#!/usr/bin/env python
"""
Some common lineshapes and distribution functions
"""
from numpy import pi, log, exp, sqrt

from scipy.special import gamma, beta

log2 = log(2)

def gaussian(x, cen=0, sigma=1, _larch=None):
    """1 dimensional gaussian:
    gaussian(x, cen, sigma)
    """
    return (sqrt(log2/pi)/sigma) * exp(-log2 * (1.0*x-cen) **2 / sigma**2)

def lorentzian(x, cen=0, sigma=1, _larch=None):
    """1 dimensional lorentzian
    lorenztian(x, cen, sigma)
    """
    return (1.  / (1 + ((1.0*x-cen)/sigma)**2) ) / (pi*sigma)

def pvoigt(x, cen=0, sigma=1, frac=0.5, _larch=None):
    """1 dimensional pseudo-voight:
    pvoigt(x, cen, sigma, frac)
       = (1-frac)*gaussion(x,cen,sigma) + frac*lorentzian(x,cen, sigma)
    """
    return ((1-frac)*gaussian(x, cen=cen, sigma=sigma) +
                frac*lorentzian(x, cen=cen, sigma=sigma))

def pearson7(x, cen=0, sigma=1, expon=0.5, _larch=None):
    """pearson7 lineshape, according to NIST StRD
    though it seems wikpedia gives a different formula...
    pearson7(x, cen, sigma, expon)
    """
    scale = gamma(expon) * sqrt((2**(1/expon) -1)) / (gamma(expon-0.5)) / (sigma*sqrt(pi))
    return scale / (1 + ( ((1.0*x-cen)/sigma)**2) * (2**(1/expon) -1) )**expon

def registerLarchPlugin():
    return ('_math', {'gaussian': gaussian,
                      'lorentzian': lorentzian,
                      'pvoigt': pvoigt,
                      'pearson7': pearson7})
