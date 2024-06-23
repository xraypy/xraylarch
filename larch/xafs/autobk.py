#!/usr/bin/env python
import sys
import time
import numpy as np
from scipy.interpolate import splrep, splev, UnivariateSpline
from scipy.stats import t
from scipy.special import erf
from scipy.optimize import leastsq
from lmfit import Parameter, Parameters, minimize, fit_report

import uncertainties

from larch import (Group, Make_CallArgs, parse_group_args, isgroup)
from larch.math import index_of, index_nearest, realimag, remove_dups

from .xafsutils import ETOK, TINY_ENERGY, set_xafsGroup
from .xafsft import ftwindow, xftf_fast
from .pre_edge import find_e0, pre_edge

FMT_COEF = 'coef_%2.2i'
NFEV = 0
def spline_eval(kraw, mu, knots, coefs, order, kout):
    """eval bkg(kraw) and chi(k) for knots, coefs, order"""
    bkg = splev(kraw, [knots, coefs, order])
    chi = UnivariateSpline(kraw, (mu-bkg), s=0)(kout)
    return bkg, chi

def _resid(vcoefs, ncoef, kraw, mu, chi_std, knots, order, kout,
            ftwin, nfft, irbkg, nclamp, clamp_lo, clamp_hi):
    global NFEV
    NFEV += 1
    nspl = len(vcoefs)
    coefs = np.ones(ncoef)*vcoefs[-1]
    coefs[:nspl] = vcoefs
    bkg, chi = spline_eval(kraw, mu, knots, coefs, order, kout)
    if chi_std is not None:
        chi = chi - chi_std
    out =  realimag(xftf_fast(chi*ftwin, nfft=nfft)[:irbkg])
    if nclamp == 0:
        return out
    scale = 1.0 + 100*(out*out).mean()
    return  np.concatenate((out,
                            abs(clamp_lo)*scale*chi[:nclamp],
                            abs(clamp_hi)*scale*chi[-nclamp:]))


@Make_CallArgs(["energy" ,"mu"])
def autobk(energy, mu=None, group=None, rbkg=1, nknots=None, e0=None, ek0=None,
           edge_step=None, kmin=0, kmax=None, kweight=1, dk=0.1,
           win='hanning', k_std=None, chi_std=None, nfft=2048, kstep=0.05,
           pre_edge_kws=None, nclamp=3, clamp_lo=0, clamp_hi=1,
           calc_uncertainties=False, err_sigma=1, _larch=None, **kws):
    """Use Autobk algorithm to remove XAFS background

    Parameters:
    -----------
      energy:    1-d array of x-ray energies, in eV, or group
      mu:        1-d array of mu(E)
      group:     output group (and input group for e0 and edge_step).
      rbkg:      distance (in Ang) for chi(R) above
                 which the signal is ignored. Default = 1.
      e0:        edge energy, in eV.  (deprecated: use ek0)
      ek0:       edge energy, in eV.  If None, it will be determined.
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
    msg = sys.stdout.write
    if _larch is not None:
        msg = _larch.writer.write
    if 'kw' in kws:
        kweight = kws.pop('kw')
    if len(kws) > 0:
        msg('Unrecognized arguments for autobk():\n')
        msg('    %s\n' % (', '.join(kws.keys())))
        return
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='autobk')
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()
    energy = remove_dups(energy, tiny=TINY_ENERGY)
    # if e0 or edge_step are not specified, get them, either from the
    # passed-in group or from running pre_edge()
    group = set_xafsGroup(group, _larch=_larch)

    if edge_step is None and isgroup(group, 'edge_step'):
        edge_step = group.edge_step
    if e0 is not None and ek0 is None:  # command-line e0 still valid
        ek0 = e0
    if ek0 is None and isgroup(group, 'ek0'):
        ek0 = group.ek0
    if ek0 is None and isgroup(group, 'e0'):
        ek0 = group.e0

    if ek0 is not None and (ek0 < energy.min() or ek0 > energy.max()):
        ek0 = None
    if ek0 is None or edge_step is None:
        # need to run pre_edge:
        pre_kws = dict(nnorm=None, nvict=0, pre1=None,
                       pre2=None, norm1=None, norm2=None)
        if pre_edge_kws is not None:
            pre_kws.update(pre_edge_kws)
        pre_edge(energy, mu, group=group, _larch=_larch, **pre_kws)
        if ek0 is None:
            ek0 = group.e0
        if edge_step is None:
            edge_step = group.edge_step
    if ek0 is None or edge_step is None:
        msg('autobk() could not determine ek0 or edge_step!: trying running pre_edge first\n')
        return

    # get array indices for rkbg and ek0: irbkg, iek0
    iek0 = index_of(energy, ek0)
    rgrid = np.pi/(kstep*nfft)
    rbkg = max(rbkg, 2*rgrid)

    # save ungridded k (kraw) and grided k (kout)
    # and ftwin (*k-weighting) for FT in residual
    enpe = energy[iek0:] - ek0
    kraw = np.sign(enpe)*np.sqrt(ETOK*abs(enpe))
    if kmax is None:
        kmax = max(kraw)
    else:
        kmax = max(0, min(max(kraw), kmax))
    kout  = kstep * np.arange(int(1.01+kmax/kstep), dtype='float64')
    iemax = min(len(energy), 2+index_of(energy, ek0+kmax*kmax/ETOK)) - 1

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
        spl_y[i] = (2*mu[ik+iek0] + mu[i1+iek0] + mu[i2+iek0] ) / 4.0

    order = 3
    qmin, qmax  = spl_k[0], spl_k[nspl-1]
    knots = [spl_k[0] - 1.e-4*(order-i) for i in range(order)]

    for i in range(order, nspl):
        knots.append((i-order)*(qmax - qmin)/(nspl-order+1))
    qlast = knots[-1]
    for i in range(order+1):
        knots.append(qlast + 1.e-4*(i+1))

    # coefs = [mu[index_nearest(energy, ek0 + q**2/ETOK)] for q in knots]
    knots, coefs, order = splrep(spl_k, spl_y, k=order)
    coefs[nspl:] = coefs[nspl-1]
    ncoefs = len(coefs)
    kraw_ = kraw[:iemax-iek0+1]
    mu_  = mu[iek0:iemax+1]
    initbkg, initchi = spline_eval(kraw_, mu_, knots, coefs, order, kout)
    global NFEV
    NFEV = 0

    vcoefs = 1.0*coefs[:nspl]
    userargs = (len(coefs), kraw_, mu_, chi_std, knots, order, kout,
               ftwin, nfft, irbkg, nclamp, clamp_lo, clamp_hi)

    lsout = leastsq(_resid, vcoefs, userargs, maxfev=2000*(ncoefs+1),
                    gtol=0.0, ftol=1.e-6, xtol=1.e-6, epsfcn=1.e-6,
                    full_output=1, col_deriv=0, factor=100, diag=None)

    best, covar, _infodict, errmsg, ier = lsout
    final_coefs        = coefs[:]
    final_coefs[:nspl] = best[:]
    final_coefs[nspl:] = best[-1]

    chisqr = ((_resid(best, *userargs))**2).sum()
    redchi = chisqr / (2*irbkg+2*nclamp - nspl)

    coefs_std = np.array([np.sqrt(redchi*covar[i, i]) for i in range(nspl)])
    bkg, chi = spline_eval(kraw[:iemax-iek0+1], mu[iek0:iemax+1],
                           knots, final_coefs, order, kout)
    obkg = mu[:]*1.0
    obkg[iek0:iek0+len(bkg)] = bkg

    # outputs to group
    group = set_xafsGroup(group, _larch=_larch)
    group.bkg  = obkg
    group.chie = (mu-obkg)/edge_step
    group.k    = kout
    group.chi  = chi/edge_step
    group.ek0  = ek0
    group.rbkg = rbkg

    knots_y  = np.array([coefs[i] for i in range(nspl)])
    init_bkg = mu[:]*1.0
    init_bkg[iek0:iek0+len(bkg)] = initbkg
    # now fill in 'autobk_details' group

    group.autobk_details = Group(kmin=kmin, kmax=kmax, irbkg=irbkg,
                                 nknots=len(spl_k), knots=knots, order=order,
                                 init_knots_y=spl_y, nspl=nspl,
                                 init_chi=initchi/edge_step, coefs=final_coefs,
                                 coefs_std=coefs_std, iek0=iek0, iemax=iemax,
                                 ek0=ek0, covar=covar, chisqr=chisqr,
                                 redchi=redchi, init_bkg=init_bkg,
                                 knots_y=knots_y, kraw=kraw, mu=mu)

    if  calc_uncertainties and covar is not None:
        autobk_delta_chi(group, err_sigma=err_sigma)


def autobk_delta_chi(group, err_sigma=1):
    """calculate uncertainties in chi(k) and bkg(E)
    after running autobk
    """
    d = getattr(group, 'autobk_details', None)
    if d is None or getattr(d, 'covar', None) is None:
        return

    nchi = len(group.chi)
    nmue = d.iemax-d.iek0 + 1
    nspl = d.nspl
    jac_chi = np.zeros(nchi*nspl).reshape((nspl, nchi))
    jac_bkg = np.zeros(nmue*nspl).reshape((nspl, nmue))
    tcoefs = np.ones(len(d.coefs)) * d.coefs[-1]

    step = 0.5
    # find derivatives by hand
    for i in range(nspl):
        b = [0, 0]
        c = [0, 0]
        for k in (0, 1):
            tcoefs = [1.0*d.coefs[j] for j in range(nspl)]
            tcoefs[i] = d.coefs[i] + (2*k-1)*step*d.coefs_std[i]
            b[k], c[k] = spline_eval(d.kraw[:d.iemax-d.iek0+1],
                                     d.mu[d.iek0:d.iemax+1],
                                     d.knots, tcoefs, d.order, group.k)
        jac_chi[i] = (c[1]- c[0])/(2*step*d.coefs_std[i])
        jac_bkg[i] = (b[1]- b[0])/(2*step*d.coefs_std[i])

    dfchi = np.zeros(nchi)
    dfbkg = np.zeros(nmue)
    for i in range(nspl):
        for j in range(nspl):
            dfchi += jac_chi[i]*jac_chi[j]*d.covar[i,j]
            dfbkg += jac_bkg[i]*jac_bkg[j]*d.covar[i,j]

    prob = 0.5*(1.0 + erf(err_sigma/np.sqrt(2.0)))
    dchi = t.ppf(prob, nchi-nspl) * np.sqrt(dfchi*d.redchi)
    dbkg = t.ppf(prob, nmue-nspl) * np.sqrt(dfbkg*d.redchi)

    if not any(np.isnan(dchi)):
        group.delta_chi = dchi
        group.delta_bkg = 0.0*d.mu
        group.delta_bkg[d.iek0:d.iek0+len(dbkg)] = dbkg


## version of autobk using lmfit

def _lmfit_resid(pars, ncoefs=1, knots=None, order=3, irbkg=1, nfft=2048,
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
def autobk_lmfit(energy, mu=None, group=None, rbkg=1, nknots=None, e0=None, ek0=None,
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
      e0:        edge energy, in eV.  (deprecated: use ek0)
      ek0:       edge energy, in eV.  If None, it will be determined.
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
    msg = sys.stdout.write
    if _larch is not None:
        msg = _larch.writer.write
    if 'kw' in kws:
        kweight = kws.pop('kw')
    if len(kws) > 0:
        msg('Unrecognized arguments for autobk_lmfit():\n')
        msg('    %s\n' % (', '.join(kws.keys())))
        return
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='autobk')
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    energy = remove_dups(energy, tiny=TINY_ENERGY)
    # if e0 or edge_step are not specified, get them, either from the
    # passed-in group or from running pre_edge()
    group = set_xafsGroup(group, _larch=_larch)

    if edge_step is None and isgroup(group, 'edge_step'):
        edge_step = group.edge_step
    if e0 is not None and ek0 is None:  # command-line e0 still valid
        ek0 = e0
    if ek0 is None and isgroup(group, 'ek0'):
        ek0 = group.ek0
    if ek0 is None and isgroup(group, 'e0'):
        ek0 = group.e0

    if ek0 is not None and (ek0 < energy.min() or ek0 > energy.max()):
        ek0 = None
    if ek0 is None or edge_step is None:
        # need to run pre_edge:
        pre_kws = dict(nnorm=None, nvict=0, pre1=None,
                       pre2=None, norm1=None, norm2=None)
        if pre_edge_kws is not None:
            pre_kws.update(pre_edge_kws)
        pre_edge(energy, mu, group=group, _larch=_larch, **pre_kws)
        if ek0 is None:
            ek0 = group.e0
        if edge_step is None:
            edge_step = group.edge_step
    if ek0 is None or edge_step is None:
        msg('autobk() could not determine ek0 or edge_step!: trying running pre_edge first\n')
        return

    # get array indices for rkbg and ek0: irbkg, iek0
    iek0 = index_of(energy, ek0)
    rgrid = np.pi/(kstep*nfft)
    if rbkg < 2*rgrid: rbkg = 2*rgrid

    # save ungridded k (kraw) and grided k (kout)
    # and ftwin (*k-weighting) for FT in residual
    enpe = energy[iek0:] - ek0
    kraw = np.sign(enpe)*np.sqrt(ETOK*abs(enpe))
    if kmax is None:
        kmax = max(kraw)
    else:
        kmax = max(0, min(max(kraw), kmax))
    kout  = kstep * np.arange(int(1.01+kmax/kstep), dtype='float64')
    iemax = min(len(energy), 2+index_of(energy, ek0+kmax*kmax/ETOK)) - 1

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
        spl_y[i] = (2*mu[ik+iek0] + mu[i1+iek0] + mu[i2+iek0] ) / 4.0

    order = 3
    qmin, qmax  = spl_k[0], spl_k[nspl-1]
    knots = [spl_k[0] - 1.e-4*(order-i) for i in range(order)]

    for i in range(order, nspl):
        knots.append((i-order)*(qmax - qmin)/(nspl-order+1))
    qlast = knots[-1]
    for i in range(order+1):
        knots.append(qlast + 1.e-4*(i+1))

    # coefs = [mu[index_nearest(energy, ek0 + q**2/ETOK)] for q in knots]
    knots, coefs, order = splrep(spl_k, spl_y, k=order)
    coefs[nspl:] = coefs[nspl-1]

    # set fit parameters from initial coefficients
    params = Parameters()
    for i in range(len(coefs)):
        params.add(name = FMT_COEF % i, value=coefs[i], vary=i<len(spl_y))

    initbkg, initchi = spline_eval(kraw[:iemax-iek0+1], mu[iek0:iemax+1],
                                   knots, coefs, order, kout)

    # do fit
    result = minimize(_lmfit_resid, params, method='leastsq',
                      gtol=1.e-6, ftol=1.e-6, xtol=1.e-6, epsfcn=1.e-6,
                      kws = dict(ncoefs=len(coefs), chi_std=chi_std,
                                 knots=knots, order=order,
                                 kraw=kraw[:iemax-iek0+1],
                                 mu=mu[iek0:iemax+1], irbkg=irbkg, kout=kout,
                                 ftwin=ftwin, kweight=kweight,
                                 nfft=nfft, nclamp=nclamp,
                                 clamp_lo=clamp_lo, clamp_hi=clamp_hi))

    # write final results
    coefs = [result.params[FMT_COEF % i].value for i in range(len(coefs))]
    bkg, chi = spline_eval(kraw[:iemax-iek0+1], mu[iek0:iemax+1],
                           knots, coefs, order, kout)
    obkg = mu[:]*1.0
    obkg[iek0:iek0+len(bkg)] = bkg

    # outputs to group
    group = set_xafsGroup(group, _larch=_larch)
    group.bkg  = obkg
    group.chie = (mu-obkg)/edge_step
    group.k    = kout
    group.chi  = chi/edge_step
    group.ek0  = ek0
    group.rbkg = rbkg

    # now fill in 'autobk_details' group
    details = Group(kmin=kmin, kmax=kmax, irbkg=irbkg, nknots=len(spl_k),
                    knots_k=knots, init_knots_y=spl_y, nspl=nspl,
                    init_chi=initchi/edge_step, report=fit_report(result))
    details.init_bkg = mu[:]*1.0
    details.init_bkg[iek0:iek0+len(bkg)] = initbkg
    details.knots_y  = np.array([coefs[i] for i in range(nspl)])
    group.autobk_details = details
    for attr in ('nfev', 'redchi', 'chisqr', 'aic', 'bic', 'params'):
        setattr(details, attr, getattr(result, attr, None))

    # uncertainties in mu0 and chi: can be fairly slow.
    covar = getattr(result, 'covar', None)
    if calc_uncertainties and covar is not None:
        nchi = len(chi)
        nmue = iemax-iek0 + 1
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
        _m = mu[iek0:iemax+1]
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

        if not any(np.isnan(dchi)):
            group.delta_chi = dchi
            group.delta_bkg = 0.0*mu
            group.delta_bkg[iek0:iek0+len(dbkg)] = dbkg
