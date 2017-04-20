#!/usr/bin/env python
# models for debye-waller factors for xafs

import ctypes
import numpy as np
from larch import ValidateLarchPlugin
from larch.larchlib import get_dll

from larch_plugins.xray import atomic_mass
import scipy.constants as consts
# EINS_FACTOR  = hbarc*hbarc/(2 * k_boltz * amu) = 24.254360157751783
#    k_boltz = 8.6173324e-5  # [eV / K]
#    amu     = 931.494061e6  # [eV / (c*c)]
#    hbarc   = 1973.26938    # [eV * A]
EINS_FACTOR = 1.e20*consts.hbar**2/(2*consts.k*consts.atomic_mass)

FEFF6LIB = None

def _sigma2_clean_args(t, theta, path, _larch):
    "clean arguments for sigma2_eins, sigma2_debye"

    if path is None:
        try:
            path = _larch.symtable._sys.fiteval.symtable
        except:
            pass
    try:
        geom, rmass, rnorman = path['_feffdat']
    except:
        geom, rmass, rnorman = None, 0, 0

    if theta < 1.e-5: theta = 1.e-5
    if t < 1.e-5: t = 1.e-5
    return (t, theta, geom, rmass, rnorman)

@ValidateLarchPlugin
def sigma2_eins(t, theta, path=None, _larch=None):
    """calculate sigma2 for a Feff Path wih the einstein model

    sigma2 = sigma2_eins(t, theta, path=None)

    Parameters:
    -----------
      t        sample temperature (in K)
      theta    Einstein temperature (in K)
      path     FeffPath to cacluate sigma2 for [None]

    if path is None, the 'current path'
    (_sys.fiteval.symtable._feffdat) is used.

    Notes:
       sigma2 = FACTOR*coth(2*t/theta)/(theta * mass_red)

    mass_red = reduced mass of Path (in amu)
    FACTOR  = hbarc*hbarc/(2*k_boltz*amu) ~= 24.25 Ang^2 * K * amu
    """
    t, theta, geom, rmass, _r = _sigma2_clean_args(t, theta, path, _larch)
    if geom is None:
        return 0.0
    tx = theta/(2.0*t)
    return EINS_FACTOR/(theta * rmass * np.tanh(tx))

@ValidateLarchPlugin
def sigma2_debye(t, theta, path=None, _larch=None):
    """calculate sigma2 for a Feff Path wih the correlated Debye model

    sigma2 = sigma2_debye(t, theta, path=None)

    Parameters:
    -----------
      t        sample temperature (in K)
      theta    Debye temperature (in K)
      path     FeffPath to cacluate sigma2 for [None]

    if path is None, the 'current path'
    (_sys.fiteval.symtable._feffdat) is used.
    """
    global FEFF6LIB
    if FEFF6LIB is None:
        FEFF6LIB = get_dll('feff6')
        FEFF6LIB.sigma2_debye.restype = ctypes.c_double

    t, theta, geom, rmass, rnorman = _sigma2_clean_args(t, theta, path, _larch)
    if geom is None:
        return 0.0

    npts = len(geom)
    nat  = ctypes.pointer(ctypes.c_int(npts))
    t    = ctypes.pointer(ctypes.c_double(t))
    th   = ctypes.pointer(ctypes.c_double(theta))
    rs   = ctypes.pointer(ctypes.c_double(rnormman))
    ax   = (npts*ctypes.c_double)()
    ay   = (npts*ctypes.c_double)()
    az   = (npts*ctypes.c_double)()
    am   = (npts*ctypes.c_double)()
    for i, dat in enumerate(geom):
        s, iz, ip, x, y, z =  dat
        ax[i], ay[i], az[i], am[i] = x, y, z, atomic_mass(iz, _larch=_larch)

    return FEFF6LIB.sigma2_debye(nat, t, th, rs, ax, ay, az, am)

def registerLarchPlugin():
    return ('_xafs', {'sigma2_eins': sigma2_eins,
                      'sigma2_debye': sigma2_debye})
