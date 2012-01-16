import numpy as np
import sys, os
import larch

ETOK = 0.26246851088

sys.path.insert(0, os.path.join(larch.site_config.plugins_path[1], 'xafs'))
from xafsft import ftwindow, xafsft_fast
from pre_edge import find_e0
from scipy.signal import cspline1d, cspline1d_eval
from scipy.interpolate import splrep, splev

def nearest_index(array, value):
    "return index of array nearest value"
    return np.abs(array-value).argmin()


def splfun(params, larch=None, **kws):
    print ftwindow

def spline(energy, mu, rbkg=1, nknots=None, group=None,
           kmin=0, kmax=None, kw=1, dk=0, win=None, e0=None,
           vary_e0=True, chi_std=None, nfft=2048, kstep=0.05,
           larch=None):
    if rbkg < 0.1: rbkg = 1.0
    rgrid = np.pi/(kstep*nfft)
    nrbkg = 2*(1 + int(0.001 + rbkg/rgrid))
    if e0 is None:
        e0 = find_e0(energy, mu, group=group, larch=larch)
    if kmax is None:
        kmax = np.sqrt(ETOK*(max(energy)-e0))
    emin = kmin**2 / ETOK
    emax = kmax**2 / ETOK

    nspline = 2*int(rbkg*(kmax-kmin)/np.pi) + 1
    if nspline < 5: nspline = 5

    spl_y  = np.zeros(nspline)
    spl_q  = np.zeros(nspline)
    spl_e  = np.zeros(nspline)
    for i in range(nspline):
        q = kmin + i*(kmax-kmin)/(nspline - 1)
        ie = nearest_index(energy, e0+q*q/ETOK)
        i1 = min(len(energy)-1, ie + 5)
        i2 = max(0, ie - 5)
        spl_e[i] = energy[ie]
        spl_y[i] = (2*mu[ie] + mu[i1] + mu[i2] ) / 4.0
    print nspline, spl_e
    spl_pars = splrep(spl_e, spl_y)  # , s=nspline/1000.)

    #     knots = list(spl_pars[0])
    #     coefs = list(spl_pars[1])
    #
    #     for e, y in zip(spl_e, spl_y):
    #         if e not in knots:
    #             for ik, k in enumerate(knots):
    #                 if e < k:
    #                     break
    #             knots.insert(ik, e)
    #             coefs.insert(ik, y)
    #     spl_pars = (np.array(knots), np.array(coefs), 3)
    print 'SPL PARAMS: ', len(spl_pars[0])
    bkg   = splev(energy, spl_pars)
    ie = nearest_index(energy, e0)
    bkg[:ie] = mu[:ie]
    if larch.symtable.isgroup(group):
        setattr(group, 'bkg',  bkg)
        setattr(group, 'sple', spl_e)
        setattr(group, 'sply', spl_y)
        setattr(group, 'splk', spl_pars[0])
        setattr(group, 'splc', spl_pars[1])

def registerLarchPlugin():
    return ('_xafs', {'splfun': splfun,
                      'autobk': spline})

