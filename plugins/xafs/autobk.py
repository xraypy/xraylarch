#!/usr/bin/env python

import sys, os

import numpy as np
from scipy.interpolate import splrep, splev, UnivariateSpline

from larch import Group, Parameter, Minimizer, plugin_path

# put the 'std' and 'xafs' (this!) plugin directories into sys.path
sys.path.insert(0, plugin_path('std'))
sys.path.insert(0, plugin_path('xafs'))
# sys.path.insert(0, plugin_path('fitter'))

# now we can reliably import other std and xafs modules...
from mathutils import index_nearest, realimag, remove_dups

from xafsutils import ETOK
from xafsft import ftwindow, xafsft_fast
from pre_edge import find_e0, pre_edge

# check for uncertainties package
HAS_UNCERTAIN = False
try:
    import uncertainties
    from uncertainties import correlated_values
    from uncertainties.unumpy import uarray
    HAS_UNCERTAIN = True
except ImportError:
    pass


FMT_COEF = 'c%2.2i'

def spline_eval(kraw, mu, knots, coefs, order, kout):
    """eval bkg(kraw) and chi(k) for knots, coefs, order"""
    bkg = splev(kraw, [knots, coefs, order])
    chi = UnivariateSpline(kraw, mu-bkg, s=0)(kout)
    return bkg, chi

def __resid(pars, ncoefs=1, knots=None, order=3, irbkg=1, nfft=2048,
            kraw=None, mu=None, kout=None, ftwin=1, chi_std=None,
            nclamp=2, clamp_lo=1, clamp_hi=1, **kws):

    coefs = [getattr(pars, FMT_COEF % i) for i in range(ncoefs)]
    bkg, chi = spline_eval(kraw, mu, knots, coefs, order, kout)
    if chi_std is not None:
        chi = chi - chi_std
    sum2 = (chi*chi).sum() * nclamp / 10.0
    out = realimag(xafsft_fast(chi*ftwin, nfft=nfft)[:irbkg])

    if clamp_lo > 0 and nclamp > 0:
        out = np.concatenate((out, clamp_lo*chi[:nclamp]/sum2))
    if clamp_hi > 0 and nclamp > 0:
        out = np.concatenate((out, clamp_hi*chi[-nclamp:]/sum2))
    return out

def autobk(energy, mu, group=None, rbkg=1, nknots=None, e0=None,
           edge_step=None, kmin=0, kmax=None, kweight=1, dk=0,
           win='hanning', k_std=None, chi_std=None, nfft=2048, kstep=0.05,
           pre_edge_kws=None, debug=False, _larch=None, nclamp=2,
           clamp_lo=1, clamp_hi=1, **kws):

    """Use Autobk algorithm to remove XAFS background
    Options are:
      rbkg -- distance out to which the chi(R) is minimized
    """
    if _larch is None:
        raise Warning("cannot calculate autobk spline -- larch broken?")

    if 'kw' in kws:
        kweight = kws['kw']

    energy = remove_dups(energy)

    # if e0 or edge_step are not specified, get them, either from the
    # passed-in group or from running pre_edge()
    if edge_step is None:
        if _larch.symtable.isgroup(group) and hasattr(group, 'edge_step'):
            edge_step = group.edge_step
    if e0 is None:
        if _larch.symtable.isgroup(group) and hasattr(group, 'e0'):
            e0 = group.e0
    if e0 is None or edge_step is None:
        # need to run pre_edge:
        pre_kws = dict(nnorm=3, nvict=0, pre1=None,
                       pre2=-50., norm1=100., norm2=None)
        if pre_edge_kws is not None:
            pre_kws.update(pre_edge_kws)
        edge_step, e0 = pre_edge(energy, mu, group=group,
                                 _larch=_larch, **pre_kws)

    # get array indices for rkbg and e0: irbkg, ie0
    ie0 = index_nearest(energy, e0)
    rgrid = np.pi/(kstep*nfft)
    if rbkg < 2*rgrid: rbkg = 2*rgrid
    irbkg = int(1.01 + rbkg/rgrid)

    # save ungridded k (kraw) and grided k (kout)
    # and ftwin (*k-weighting) for FT in residual
    kraw = np.sqrt(ETOK*(energy[ie0:] - e0))
    if kmax is None:
        kmax = max(kraw)
    kout  = kstep * np.arange(int(1.01+kmax/kstep), dtype='float64')

    # interpolate provided chi(k) onto the kout grid
    if chi_std is not None and k_std is not None:
        chi_std = np.interp(kout, k_std, chi_std)

    ftwin = kout**kweight * ftwindow(kout, xmin=kmin, xmax=kmax,
                                     window=win, dx=dk)

    # calc k-value and initial guess for y-values of spline params
    nspline = max(4, min(128, 2*int(rbkg*(kmax-kmin)/np.pi) + 1))
    spl_y  = np.zeros(nspline)
    spl_k  = np.zeros(nspline)
    spl_e  = np.zeros(nspline)
    for i in range(nspline):
        q = kmin + i*(kmax-kmin)/(nspline - 1)
        ik = index_nearest(kraw, q)

        i1 = min(len(kraw)-1, ik + 5)
        i2 = max(0, ik - 5)
        spl_k[i] = kraw[ik]
        spl_e[i] = energy[ik+ie0]
        spl_y[i] = (2*mu[ik+ie0] + mu[i1+ie0] + mu[i2+ie0] ) / 4.0

    # get spline represention: knots, coefs, order=3
    # coefs will be varied in fit.
    knots, coefs, order = splrep(spl_k, spl_y)

    # set fit parameters from initial coefficients
    ncoefs = len(coefs)
    params = Group()
    for i in range(ncoefs):
        name = FMT_COEF % i
        p = Parameter(coefs[i], name=name, vary=i<len(spl_y))
        p._getval()
        setattr(params, name, p)

    initbkg, initchi = spline_eval(kraw, mu[ie0:], knots, coefs, order, kout)

    fitkws = dict(ncoefs=len(coefs), chi_std=chi_std,
                  knots=knots, order=order, kraw=kraw, mu=mu[ie0:],
                  irbkg=irbkg, kout=kout, ftwin=ftwin, nfft=nfft,
                  nclamp=nclamp, clamp_lo=clamp_lo, clamp_hi=clamp_hi)
    # do fit
    fit = Minimizer(__resid, params, fcn_kws=fitkws, _larch=_larch, toler=1.e-4)
    fit.leastsq()

    # write final results
    coefs = [getattr(params, FMT_COEF % i) for i in range(ncoefs)]

    bkg, chi = spline_eval(kraw, mu[ie0:], knots, coefs, order, kout)
    obkg  = np.zeros(len(mu))
    obkg[:ie0] = mu[:ie0]
    obkg[ie0:] = bkg
    if _larch.symtable.isgroup(group):
        group.bkg  = obkg
        group.chie = (mu-obkg)/edge_step
        group.k    = kout
        group.chi  = chi/edge_step
        gdet = group.autobk_details = Group()
        gdet.spline_params = params
        ix_bkg = np.zeros(len(mu))
        ix_bkg[:ie0] = mu[:ie0]
        ix_bkg[ie0:] = initbkg
        gdet.init_bkg = ix_bkg
        gdet.init_chi = initchi/edge_step
        gdet.spline_e = spl_e
        gdet.spline_y = np.array([coefs[i] for i in range(nspline)])
        gdet.spline_yinit = spl_y
        if HAS_UNCERTAIN:
            # now, calculate delta_mu0 and delta_chi
            vbest, vstd = [], []
            for n in fit.var_names:
                par = getattr(params, n)
                vbest.append(par.value)
                vstd.append(par.stderr)
            uvars = correlated_values(vbest, params.covar)
            # uncertainty in bkg (aka mu0)
            # note that much of this is working around
            # limitations in the uncertainty package that make it
            #  1. take an argument list (not array)
            #  2. work on returned scalars (but not arrays)
            #  3. not handle kw args and *args well (so use
            #     of global "index" is important here)
            def my_dsplev(*args):
                coefs = np.array(args)
                return splev(kraw, [knots, coefs, order])[index]
            fdbkg = uncertainties.wrap(my_dsplev)
            dmu0  = [fdbkg(*uvars).std_dev() for index in range(len(bkg))]
            gdet.dbkg = np.zeros(len(mu))
            gdet.dbkg[ie0:] = np.array(dmu0)

            # uncertainty in chi (see notes above)
            def my_dchi(*args):
                coefs = np.array(args)
                b, c = spline_eval(kraw, mu[ie0:], knots, coefs, order, kout)
                return c[index]
            fdchi = uncertainties.wrap(my_dchi)
            dci   = [fdchi(*uvars).std_dev() for index in range(len(kout))]
            gdet.dchi  = np.array(dci)/edge_step

def registerLarchPlugin():
    return ('_xafs', {'autobk': autobk})

