#!/usr/bin/env python
# models for debye-waller factors for xafs

import sys
import ctypes
import numpy as np
from larch.larchlib import plugin_path, get_dll

sys.path.insert(0, plugin_path('xray'))

from xraydb_plugin import atomic_mass

# EINS_FACTOR  = hbarc*hbarc/(2 * k_boltz * amu)
#    k_boltz = 8.6173324e-5  # [eV / K]
#    amu     = 931.494061e6  # [eV / (c*c)]
#    hbarc   = 1973.26938    # [eV * A]
EINS_FACTOR = 24.254360157751783

FEFF6LIB = None

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
            path = _larch.symtable._sys.paramGroup._feffdat
        except:
            pass
    if path is None:
        return 0.0
    if theta < 1.e-5: theta = 1.e-5
    if t < 1.e-5: t = 1.e-5
    tx = 2.0*t/theta
    return EINS_FACTOR/(theta * path.rmass * np.tanh(tx))

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
    if path is None:
        try:
            path = _larch.symtable._sys.paramGroup._feffdat
        except:
            pass
    if path is None:
        return 0.0

    if FEFF6LIB is None:
        FEFF6LIB = get_dll('feff6')

    fdat = path._feffdat
    npts  = len(path.geom)
    nat   = ctypes.pointer(ctypes.c_int(npts))
    t     = ctypes.pointer(ctypes.c_double(t))
    theta = ctypes.pointer(ctypes.c_double(theta))
    rnorm = ctypes.pointer(ctypes.c_double(fdat.rnorman))
    x     = (npts*ctypes.c_double)()
    y     = (npts*ctypes.c_double)()
    z     = (npts*ctypes.c_double)()
    mass  = (npts*ctypes.c_double)()
    for i in range(len(path.geom)):
        sym, iz, ipot, ax, ay, az =  path.geom[i]
        x[i], y[i], z[i], mass[i] = ax, ay, az, atomic_mass(iz, _larch=_larch)

    FEFF6LIB.sigma2_debye.restype = ctypes.c_double
    return FEFF6LIB.sigma2_debye(nat, t, theta, rnorm, x, y, z, mass)

def registerLarchPlugin():
    return ('_xafs', {'eins': sigma2_eins,
                      'debye': sigma2_debye})
