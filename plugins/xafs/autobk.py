import numpy as np
import sys, os
import larch

ETOK = 0.26246851088

sys.path.insert(0, os.path.join(larch.site_config.plugins_path[1], 'xafs'))

from xafsft import ftwindow, xafsft_fast
from pre_edge import find_e0
from scipy.interpolate import splrep, splev, UnivariateSpline

from lmfit import Parameters, Minimizer

def nearest_index(array, value):
    "return index of array nearest value"
    return np.abs(array-value).argmin()

def _autobk_resid(pars, eknots=None, order=3,
                  energy=None, mu=None, ie0=0,
                  nrbkg=1, kraw=None, kout=None,
                  ftwin=1, nfft=2048, **kws):

    coefs = [p.value for p in pars.values()]
    chie  = mu - splev(kraw, [eknots, coefs, order])
    chik  = UnivariateSpline(kraw, chie, s=0)(kout)
    chir  = xafsft_fast(chik*ftwin, nfft=nfft)
    return np.array((chir[:nrbkg].real, chir[:nrbkg].imag)).flatten()


def autobk(energy, mu, rbkg=1, nknots=None, group=None, e0=None,
           kmin=0, kmax=None, kw=1, dk=0, win=None, vary_e0=True,
           chi_std=None, nfft=2048, kstep=0.05, larch=None):
    if larch is None:
        raise Warning("cannot calculate autobk spline -- larch broken?")

    if rbkg < 0.1: rbkg = 1.0
    rgrid = np.pi/(kstep*nfft)
    nrbkg = int(1.01 + rbkg/rgrid)
    if e0 is None:
        e0 = find_e0(energy, mu, group=group, larch=larch)

    ie0 = nearest_index(energy, e0)
    kraw = np.sqrt(ETOK*(energy[ie0:] - e0))
    if kmax is None:
        kmax = max(kraw)
    emin = kmin**2 / ETOK
    emax = kmax**2 / ETOK

    kout = kstep * np.arange(int(1.01+kmax/kstep))
    if win is None:
        win = 'han'
    ftwin = kout**kw * ftwindow(kout, xmin=kmin, xmax=kmax,
                                window=win, dx=dk)

    nspline = 2*int(rbkg*(kmax-kmin)/np.pi) + 1
    if nspline < 5: nspline = 5
    spl_y  = np.zeros(nspline)
    spl_k  = np.zeros(nspline)
    for i in range(nspline):
        q = kmin + i*(kmax-kmin)/(nspline - 1)
        ik = nearest_index(kraw, q)
        i1 = min(len(kraw)-1, ik + 5)
        i2 = max(0, ik - 5)
        spl_k[i] = kraw[ik]
        spl_y[i] = (2*mu[ik] + mu[ik] + mu[ik] ) / 4.0

    spl_pars = splrep(spl_k, spl_y)  # , s=nspline/1000.)

    eknots = spl_pars[0]
    order  = spl_pars[2]

    bkg0  = splev(kraw, spl_pars)
    bkg0[:ie0] = mu[:ie0]
    fparams = Parameters()
    for i, v in enumerate(spl_pars[1]):
        fparams.add("coef%i" % i, value=v)

    kws = dict(eknots=eknots, order=order, kraw=kraw, mu=mu[ie0:],
               nrbkg=nrbkg, kout=kout, ftwin=ftwin, nfft=nfft,
               kstep=kstep, larch=larch)

    fit = Minimizer(_autobk_resid, fparams, fcn_kws=kws)
    fit.leastsq()

    coefs = [p.value for p in fparams.values()]
    bkg   = splev(kraw, [eknots, coefs, order])
    chi   = UnivariateSpline(kraw, (mu[ie0:] - bkg), s=0)(kout)
    bkgf  = mu[:]
    bkgf[ie0:] = bkg
    chie  = mu - bkgf
    if larch.symtable.isgroup(group):
        setattr(group, 'bkg',  bkgf)
        setattr(group, 'k',   kout)
        setattr(group, 'chi',  chi)
        setattr(group, 'chie',  chie)

def registerLarchPlugin():
    return ('_xafs', {'autobk': autobk})
