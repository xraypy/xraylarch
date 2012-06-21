#!/usr/bin/env python

import sys, os

import numpy as np
from scipy.interpolate import splrep, splev, UnivariateSpline

import larch
from larch import Group, Parameter
from larch.larchlib import plugin_path

# put the 'std' and 'xafs' (this!) plugin directories into sys.path
sys.path.insert(0, plugin_path('std'))
sys.path.insert(0, plugin_path('xafs'))
sys.path.insert(0, plugin_path('fitter'))

# now we can reliably import other std and xafs modules...
from mathutils import index_nearest, realimag

from xafsutils import ETOK
from xafsft import ftwindow, xafsft_fast
from pre_edge import find_e0, pre_edge

from minimizer import Minimizer

FMT_COEF = 'c%2.2i'

def spline_eval(kraw, mu, knots, coefs, order, kout):
    """eval bkg(kraw) and chi(k) for knots, coefs, order"""
    bkg = splev(kraw, [knots, coefs, order])
    chi = UnivariateSpline(kraw, mu-bkg, s=0)(kout)
    return bkg, chi

def __resid(pars, ncoefs=1, knots=None, order=3, irbkg=1, nfft=2048,
            kraw=None, mu=None, kout=None, ftwin=1, **kws):

    coefs = [getattr(pars, FMT_COEF % i) for i in range(ncoefs)]
    bkg, chi = spline_eval(kraw, mu, knots, coefs, order, kout)
    return realimag(xafsft_fast(chi*ftwin, nfft=nfft)[:irbkg])

def autobk(energy, mu, group=None, rbkg=1, nknots=None,
           e0=None, edge_step=None, kmin=0, kmax=None, kweight=1,
           dk=0, win=None, vary_e0=True, chi_std=None,
           nfft=2048, kstep=0.05, pre_edge_kws=None,
           debug=False, _larch=None, **kws):

    """Use Autobk algorithm to remove XAFS background
    Options are:
      rbkg -- distance out to which the chi(R) is minimized
    """
    if _larch is None:
        raise Warning("cannot calculate autobk spline -- larch broken?")

    if 'kw' in kws:
        kweight = kws['kw']

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

    ftwin = kout**kweight * ftwindow(kout, xmin=kmin, xmax=kmax,
                                     window=win, dx=dk)

    # calc k-value and initial guess for y-values of spline params
    nspline = max(4, min(60, 2*int(rbkg*(kmax-kmin)/np.pi) + 1))
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

    fitkws = dict(ncoefs=len(coefs),
                  knots=knots, order=order, kraw=kraw, mu=mu[ie0:],
                  irbkg=irbkg, kout=kout, ftwin=ftwin, nfft=nfft)
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
        if debug:
            group.spline_params = params
            ix_bkg = np.zeros(len(mu))
            ix_bkg[:ie0] = mu[:ie0]
            ix_bkg[ie0:] = initbkg
            group.init_bkg = ix_bkg
            group.init_chi = initchi/edge_step
            group.spline_e = spl_e
            group.spline_y = np.array([coefs[i] for i in range(nspline)])
            group.spline_yinit = spl_y


def registerLarchPlugin():
    return ('_xafs', {'autobk': autobk})

