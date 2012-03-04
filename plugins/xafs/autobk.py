import numpy as np
import sys, os
import larch

ETOK = 0.26246851088

# put the 'std' and 'xafs' (this!) plugin directories into
# sys.path to make sure module from these directories can be imported
stddir = os.path.join(larch.site_config.sys_larchdir, 'plugins', 'std')
sys.path.insert(0, stddir)

thisdir = os.path.join(larch.site_config.sys_larchdir, 'plugins', 'xafs')
sys.path.insert(0, thisdir)

# now we can reliably import other std and xafs modules...
from mathutils import _index_nearest, realimag

from xafsft import ftwindow, xafsft_fast
from pre_edge import find_e0

from scipy.interpolate import splrep, splev, UnivariateSpline

from lmfit import Parameters, Minimizer

def spline_eval(kraw, mu, knots, coefs, order, kout):
    """eval bkg(kraw) and chi(k) for knots, coefs, order"""
    bkg = splev(kraw, [knots, coefs, order])
    chi = UnivariateSpline(kraw, mu-bkg, s=0)(kout)
    return bkg, chi

def __resid(pars, knots=None, order=3, irbkg=1, nfft=2048,
            kraw=None, mu=None, kout=None, ftwin=1, **kws):
    coefs = [p.value for p in pars.values()]
    bkg, chi = spline_eval(kraw, mu, knots, coefs, order, kout)
    return realimag(xafsft_fast(chi*ftwin, nfft=nfft)[:irbkg])

def autobk(energy, mu, rbkg=1, nknots=None, group=None, e0=None,
           kmin=0, kmax=None, kw=1, dk=0, win=None, vary_e0=True,
           chi_std=None, nfft=2048, kstep=0.05, larch=None):
    if larch is None:
        raise Warning("cannot calculate autobk spline -- larch broken?")

    # get array indices for rkbg and e0: irbkg, ie0
    rgrid = np.pi/(kstep*nfft)
    if rbkg < 2*rgrid: rbkg = 2*rgrid
    irbkg = int(1.01 + rbkg/rgrid)
    if e0 is None:
        e0 = find_e0(energy, mu, group=group, larch=larch)
    ie0 = _index_nearest(energy, e0)

    # save ungridded k (kraw) and grided k (kout)
    # and ftwin (*k-weighting) for FT in residual
    kraw = np.sqrt(ETOK*(energy[ie0:] - e0))
    if kmax is None:
        kmax = max(kraw)
    kout  = kstep * np.arange(int(1.01+kmax/kstep))
    ftwin = kout**kw * ftwindow(kout, xmin=kmin, xmax=kmax,
                                window=win, dx=dk)

    # calc k-value and initial guess for y-values of spline params
    nspline = max(4, min(60, 2*int(rbkg*(kmax-kmin)/np.pi) + 1))
    spl_y  = np.zeros(nspline)
    spl_k  = np.zeros(nspline)
    for i in range(nspline):
        q = kmin + i*(kmax-kmin)/(nspline - 1)
        ik = _index_nearest(kraw, q)
        i1 = min(len(kraw)-1, ik + 5)
        i2 = max(0, ik - 5)
        spl_k[i] = kraw[ik]
        spl_y[i] = (2*mu[ik] + mu[i1] + mu[i2] ) / 4.0
    # get spline represention: knots, coefs, order=3
    # coefs will be varied in fit.
    knots, coefs, order = splrep(spl_k, spl_y)

    # set fit parameters from initial coefficients
    fparams = Parameters()
    for i, v in enumerate(coefs):
        fparams.add("c%i" % i, value=v, vary=i<len(spl_y))

    fitkws = dict(knots=knots, order=order, kraw=kraw, mu=mu[ie0:],
                  irbkg=irbkg, kout=kout, ftwin=ftwin, nfft=nfft)
    # do fit
    fit = Minimizer(__resid, fparams, fcn_kws=fitkws)
    fit.leastsq()

    # write final results
    coefs = [p.value for p in fparams.values()]
    bkg, chi = spline_eval(kraw, mu[ie0:], knots, coefs, order, kout)
    obkg  = np.zeros(len(mu))
    obkg[:ie0] = mu[:ie0]
    obkg[ie0:] = bkg
    if larch.symtable.isgroup(group):
        setattr(group, 'bkg',  obkg)
        setattr(group, 'chie', mu-obkg)
        setattr(group, 'k',    kout)
        setattr(group, 'chi',  chi)

def registerLarchPlugin():
    return ('_xafs', {'autobk': autobk})

