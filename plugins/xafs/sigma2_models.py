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
    (_sys.paramGroup._feffdat) is used.

    Notes:
       sigma2 = FACTOR*coth(2*t/theta)/(theta * mass_red)

    mass_red = reduced mass of Path (in amu)
    FACTOR  = hbarc*hbarc/(2*k_boltz*amu) ~= 24.25 Ang^2 * K * amu
    """
    if path is None:
        try:
            path = _larch.symtable._sys.paramGroup
        except:
            pass
    try:
        fdat = path._feffdat
    except:
        return 0.00

    if theta < 1.e-5: theta = 1.e-5
    if t < 1.e-5: t = 1.e-5
    tx = theta/(2.0*t)
    return EINS_FACTOR/(theta * fdat.rmass * np.tanh(tx))

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
    (_sys.paramGroup._feffdat) is used.
    """
    global FEFF6LIB
    if FEFF6LIB is None:
        FEFF6LIB = get_dll('feff6')
        FEFF6LIB.sigma2_debye.restype = ctypes.c_double

    if path is None:
        try:
            path = _larch.symtable._sys.paramGroup
        except:
            pass
    try:
        fdat = path._feffdat
    except:
        return 0.00
    if theta < 1.e-5: theta = 1.e-5
    if t < 1.e-5: t = 1.e-5

    npts = len(fdat.geom)
    nat  = ctypes.pointer(ctypes.c_int(npts))
    t    = ctypes.pointer(ctypes.c_double(t))
    th   = ctypes.pointer(ctypes.c_double(theta))
    rs   = ctypes.pointer(ctypes.c_double(fdat.rnorman))
    ax   = (npts*ctypes.c_double)()
    ay   = (npts*ctypes.c_double)()
    az   = (npts*ctypes.c_double)()
    am   = (npts*ctypes.c_double)()
    for i, dat in enumerate(fdat.geom):
        s, iz, ip, x, y, z =  dat
        ax[i], ay[i], az[i], am[i] = x, y, z, atomic_mass(iz, _larch=_larch)

    return FEFF6LIB.sigma2_debye(nat, t, th, rs, ax, ay, az, am)

def registerLarchPlugin():
    return ('_xafs', {'sigma2_eins': sigma2_eins,
                      'sigma2_debye': sigma2_debye})
