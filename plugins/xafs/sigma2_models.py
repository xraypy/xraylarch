#!/usr/bin/env python
# models for debye-waller factors for xafs

from numpy import coth

# EINS_FACTOR  = hbarc*hbarc/(2 * k_boltz * amu)
#    k_boltz = 8.6173324e-5  # [eV / K]
#    amu     = 931.494061e6  # [eV / (c*c)]
#    hbarc   = 1973.26938    # [eV * A]
EINS_FACTOR = 24.254360157751783

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
    return EINS_FACTOR*coth(tx)/(theta * path.rmass)

def registerLarchPlugin():
    return ('_xafs', {'eins': sigma2_eins})

