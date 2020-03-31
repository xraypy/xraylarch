#!/usr/bin/env python
import sys
import numpy as np
from scipy.interpolate import splrep, splev, UnivariateSpline
from scipy.stats import t
from scipy.special import erf
from lmfit import Parameter, Parameters, minimize, fit_report

import uncertainties

from larch import (Group, Make_CallArgs, parse_group_args, isgroup)

from larch.math import index_of, index_nearest, realimag, remove_dups

from .xafsutils import ETOK, set_xafsGroup
from .xafsft import ftwindow, xftf_fast
from .pre_edge import find_e0, pre_edge

FMT_COEF = 'coef_%2.2i'

def spline_eval(kraw, mu, knots, coefs, order, kout):
    """eval bkg(kraw) and chi(k) for knots, coefs, order"""
    bkg = splev(kraw, [knots, coefs, order])
    chi = UnivariateSpline(kraw, (mu-bkg), s=0)(kout)
    return bkg, chi

def __resid(pars, ncoefs=1, knots=None, order=3, irbkg=1, nfft=2048,
            kraw=None, mu=None, kout=None, ftwin=1, kweight=1, chi_std=None,
            nclamp=0, clamp_lo=1, clamp_hi=1, **kws):

    # coefs = [getattr(pars, FMT_COEF % i) for i in range(ncoefs)]
    coefs = [pars[FMT_COEF % i].value for i in range(ncoefs)]
    bkg, chi = spline_eval(kraw, mu, knots, coefs, order, kout)
    if chi_std is not None:
        chi = chi - chi_std
    out =  realimag(xftf_fast(chi*ftwin, nfft=nfft)[:irbkg])
    if nclamp == 0:
        return out
    # spline clamps:
    scale = 1.0 + 100*(out*out).mean()
    return  np.concatenate((out,
                            abs(clamp_lo)*scale*chi[:nclamp],
                            abs(clamp_hi)*scale*chi[-nclamp:]))


@Make_CallArgs(["energy" ,"mu"])
def autobk(energy, mu=None, group=None, rbkg=1, nknots=None, e0=None,
           edge_step=None, kmin=0, kmax=None, kweight=1, dk=0.1,
           win='hanning', k_std=None, chi_std=None, nfft=2048, kstep=0.05,
           pre_edge_kws=None, nclamp=3, clamp_lo=0, clamp_hi=1,
           calc_uncertainties=True, err_sigma=1, _larch=None, **kws):
    """Use Autobk algorithm to remove XAFS background

    Parameters:
    -----------
      energy:    1-d array of x-ray energies, in eV, or group
      mu:        1-d array of mu(E)
      group:     output group (and input group for e0 and edge_step).
      rbkg:      distance (in Ang) for chi(R) above
                 which the signal is ignored. Default = 1.
      e0:        edge energy, in eV.  If None, it will be determined.
      edge_step: edge step.  If None, it will be determined.
      pre_edge_kws:  keyword arguments to pass to pre_edge()
      nknots:    number of knots in spline.  If None, it will be determined.
      kmin:      minimum k value   [0]
      kmax:      maximum k value   [full data range].
      kweight:   k weight for FFT.  [1]
      dk:        FFT window window parameter.  [0.1]
      win:       FFT window function name.     ['hanning']
      nfft:      array size to use for FFT [2048]
      kstep:     k step size to use for FFT [0.05]
      k_std:     optional k array for standard chi(k).
      chi_std:   optional chi array for standard chi(k).
      nclamp:    number of energy end-points for clamp [3]
      clamp_lo:  weight of low-energy clamp [0]
      clamp_hi:  weight of high-energy clamp [1]
      calc_uncertaintites:  Flag to calculate uncertainties in
                            mu_0(E) and chi(k) [True]
      err_sigma: sigma level for uncertainties in mu_0(E) and chi(k) [1]

    Output arrays are written to the provided group.

    Follows the 'First Argument Group' convention.
    """
    msg = sys.stdout
    if _larch is not None:
        msg = _larch.writer.write
    if 'kw' in kws:
        kweight = kws.pop('kw')
    if len(kws) > 0:
        msg('Unrecognized a:rguments for autobk():\n')
        msg('    %s\n' % (', '.join(kws.keys())))
        return
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='autobk')
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    energy = remove_dups(energy)
    # if e0 or edge_step are not specified, get them, either from the
    # passed-in group or from running pre_edge()
    group = set_xafsGroup(group, _larch=_larch)

    if edge_step is None and isgroup(group, 'edge_step'):
        edge_step = group.edge_step
    if e0 is None and isgroup(group, 'e0'):
        e0 = group.e0
    if e0 is not None and (e0 < energy.min() or e0 > energy.max()):
        e0 = None
    if e0 is None or edge_step is None:
        # need to run pre_edge:
        pre_kws = dict(nnorm=None, nvict=0, pre1=None,
                       pre2=None, norm1=None, norm2=None)
        if pre_edge_kws is not None:
            pre_kws.update(pre_edge_kws)
        pre_edge(energy, mu, group=group, _larch=_larch, **pre_kws)
        if e0 is None:
            e0 = group.e0
        if edge_step is None:
            edge_step = group.edge_step
    if e0 is None or edge_step is None:
        msg('autobk() could not determine e0 or edge_step!: trying running pre_edge first\n')
        return

    # get array indices for rkbg and e0: irbkg, ie0
    ie0 = index_of(energy, e0)
    rgrid = np.pi/(kstep*nfft)
    if rbkg < 2*rgrid: rbkg = 2*rgrid

    # save ungridded k (kraw) and grided k (kout)
    # and ftwin (*k-weighting) for FT in residual
    enpe = energy[ie0:] - e0
    kraw = np.sign(enpe)*np.sqrt(ETOK*abs(enpe))
    if kmax is None:
        kmax = max(kraw)
    else:
        kmax = max(0, min(max(kraw), kmax))
    kout  = kstep * np.arange(int(1.01+kmax/kstep), dtype='float64')
    iemax = min(len(energy), 2+index_of(energy, e0+kmax*kmax/ETOK)) - 1

    # interpolate provided chi(k) onto the kout grid
    if chi_std is not None and k_std is not None:
        chi_std = np.interp(kout, k_std, chi_std)
    # pre-load FT window
    ftwin = kout**kweight * ftwindow(kout, xmin=kmin, xmax=kmax,
                                     window=win, dx=dk, dx2=dk)
    # calc k-value and initial guess for y-values of spline params
    nspl = 1 + int(2*rbkg*(kmax-kmin)/np.pi)
    irbkg = int(1 + (nspl-1)*np.pi/(2*rgrid*(kmax-kmin)))
    if nknots is not None:
        nspl = nknots
    nspl = max(5, min(128, nspl))
    spl_y, spl_k  = np.ones(nspl), np.zeros(nspl)
    for i in range(nspl):
        q  = kmin + i*(kmax-kmin)/(nspl - 1)
        ik = index_nearest(kraw, q)
        i1 = min(len(kraw)-1, ik + 5)
        i2 = max(0, ik - 5)
        spl_k[i] = kraw[ik]
        spl_y[i] = (2*mu[ik+ie0] + mu[i1+ie0] + mu[i2+ie0] ) / 4.0

    order = 3
    qmin, qmax  = spl_k[0], spl_k[nspl-1]
    knots = [spl_k[0] - 1.e-4*(order-i) for i in range(order)]

    for i in range(order, nspl):
        knots.append((i-order)*(qmax - qmin)/(nspl-order+1))
    qlast = knots[-1]
    for i in range(order+1):
        knots.append(qlast + 1.e-4*(i+1))

    coefs = [mu[index_nearest(energy, e0 + q**2/ETOK)] for q in knots]
    knots, coefs, order = splrep(spl_k, spl_y, k=order)
    coefs[nspl:] = coefs[nspl-1]

    # set fit parameters from initial coefficients
    params = Parameters()
    for i in range(len(coefs)):
        params.add(name = FMT_COEF % i, value=coefs[i], vary=i<len(spl_y))

    initbkg, initchi = spline_eval(kraw[:iemax-ie0+1], mu[ie0:iemax+1],
                                   knots, coefs, order, kout)

    # do fit
    result = minimize(__resid, params, method='leastsq',
                      gtol=1.e-6, ftol=1.e-6, xtol=1.e-6, epsfcn=1.e-6,
                      kws = dict(ncoefs=len(coefs), chi_std=chi_std,
                                 knots=knots, order=order,
                                 kraw=kraw[:iemax-ie0+1],
                                 mu=mu[ie0:iemax+1], irbkg=irbkg, kout=kout,
                                 ftwin=ftwin, kweight=kweight,
                                 nfft=nfft, nclamp=nclamp,
                                 clamp_lo=clamp_lo, clamp_hi=clamp_hi))

    # write final results
    coefs = [result.params[FMT_COEF % i].value for i in range(len(coefs))]
    bkg, chi = spline_eval(kraw[:iemax-ie0+1], mu[ie0:iemax+1],
                           knots, coefs, order, kout)
    obkg = np.copy(mu)
    obkg[ie0:ie0+len(bkg)] = bkg

    # outputs to group
    group = set_xafsGroup(group, _larch=_larch)
    group.bkg  = obkg
    group.chie = (mu-obkg)/edge_step
    group.k    = kout
    group.chi  = chi/edge_step
    group.e0   = e0

    # now fill in 'autobk_details' group
    details = Group(kmin=kmin, kmax=kmax, irbkg=irbkg, nknots=len(spl_k),
                    knots_k=knots, init_knots_y=spl_y, nspl=nspl,
                    init_chi=initchi/edge_step, report=fit_report(result))
    details.init_bkg = np.copy(mu)
    details.init_bkg[ie0:ie0+len(bkg)] = initbkg
    details.knots_y  = np.array([coefs[i] for i in range(nspl)])
    group.autobk_details = details
    for attr in ('nfev', 'redchi', 'chisqr', 'aic', 'bic', 'params'):
        setattr(details, attr, getattr(result, attr, None))

    # uncertainties in mu0 and chi: can be fairly slow.
    if calc_uncertainties:
        nchi = len(chi)
        nmue = iemax-ie0 + 1
        redchi = result.redchi
        covar  = result.covar / redchi
        jac_chi = np.zeros(nchi*nspl).reshape((nspl, nchi))
        jac_bkg = np.zeros(nmue*nspl).reshape((nspl, nmue))

        cvals, cerrs = [], []
        for i in range(len(coefs)):
             par = result.params[FMT_COEF % i]
             cvals.append(getattr(par, 'value', 0.0))
             cdel = getattr(par, 'stderr', 0.0)
             if cdel is None:
                 cdel = 0.0
             cerrs.append(cdel/2.0)
        cvals = np.array(cvals)
        cerrs = np.array(cerrs)

        # find derivatives by hand!
        _k = kraw[:nmue]
        _m = mu[ie0:iemax+1]
        for i in range(nspl):
            cval0 = cvals[i]
            cvals[i] = cval0 + cerrs[i]
            bkg1, chi1 = spline_eval(_k, _m, knots, cvals, order, kout)

            cvals[i] = cval0 - cerrs[i]
            bkg2, chi2 = spline_eval(_k, _m, knots, cvals, order, kout)

            cvals[i] = cval0
            jac_chi[i] = (chi1 - chi2) / (2*cerrs[i])
            jac_bkg[i] = (bkg1 - bkg2) / (2*cerrs[i])

        dfchi = np.zeros(nchi)
        dfbkg = np.zeros(nmue)
        for i in range(nspl):
            for j in range(nspl):
                dfchi += jac_chi[i]*jac_chi[j]*covar[i,j]
                dfbkg += jac_bkg[i]*jac_bkg[j]*covar[i,j]

        prob = 0.5*(1.0 + erf(err_sigma/np.sqrt(2.0)))
        dchi = t.ppf(prob, nchi-nspl) * np.sqrt(dfchi*redchi)
        dbkg = t.ppf(prob, nmue-nspl) * np.sqrt(dfbkg*redchi)

        group.delta_chi = dchi
        group.delta_bkg = 0.0*mu
        group.delta_bkg[ie0:ie0+len(dbkg)] = dbkg
