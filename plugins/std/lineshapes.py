#!/usr/bin/env python
"""
Some common lineshapes and distribution functions
"""
from numpy import pi, log, exp, sqrt

from scipy.special import gamma, gammaln, beta, betaln, erf, erfc, wofz
from larch import param_value

log2 = log(2)
s2pi = sqrt(2*pi)
spi  = sqrt(pi)

def gaussian(x, cen=0, sigma=1):
    """1 dimensional gaussian:
    gaussian(x, cen, sigma)
    """
    cen = param_value(cen)
    sigma = param_value(sigma)
    return (1./(2*spi*sigma)) * exp(-(1.0*x-cen) **2 / (2*sigma)**2)

def lorentzian(x, cen=0, sigma=1):
    """1 dimensional lorentzian
    lorenztian(x, cen, sigma)
    """
    cen = param_value(cen)
    sigma = param_value(sigma)
    return (1.  / (1 + ((1.0*x-cen)/sigma)**2) ) / (pi*sigma)

def voigt(x, cen=0, sigma=1, gamma=None):
    """1 dimensional voigt function.

    see http://en.wikipedia.org/wiki/Voigt_profile
    """
    if gamma is None:
        gamma = sigma
    z = (x-cen + 1j*gamma)/ (sigma*sqrt(2))
    return wofz(z).real / (sigma*s2pi)

def pvoigt(x, cen=0, sigma=1, frac=0.5):
    """1 dimensional pseudo-voigt:
    pvoigt(x, cen, sigma, frac)
       = (1-frac)*gaussion(x,cen,sigma) + frac*lorentzian(x,cen, sigma)
    """
    cen = param_value(cen)
    sigma = param_value(sigma)
    frac = param_value(frac)
    return ((1-frac)*gaussian(x, cen=cen, sigma=sigma) +
                frac*lorentzian(x, cen=cen, sigma=sigma))

def pearson7(x, cen=0, sigma=1, expon=0.5):
    """pearson7 lineshape, according to NIST StRD
    though it seems wikpedia gives a different formula...
    pearson7(x, cen, sigma, expon)
    """
    cen = param_value(cen)
    sigma = param_value(sigma)
    expon = param_value(expon)
    scale = gamma(expon) * sqrt((2**(1/expon) -1)) / (gamma(expon-0.5)) / (sigma*sqrt(pi))
    return scale / (1 + ( ((1.0*x-cen)/sigma)**2) * (2**(1/expon) -1) )**expon

def _erf(x):
    """error function.  = 2/sqrt(pi)*integral(exp(-t**2), t=[0, z])"""
    return erf(x)

def _erfc(x):
    """complented error function.  = 1 - erf(x)"""
    return erfc(x)

def _wofz(x):
    """fadeeva function for complex argument. = exp(-x**2)*erfc(-i*x)"""
    return wofz(x)

def _gamma(x):
    """gamma function"""
    return gamma(x)

def _gammaln(x):
    """log of absolute value of gamma function"""
    return gammaln(x)

def registerLarchPlugin():
    return ('_math', {'gaussian': gaussian,
                      'lorentzian': lorentzian,
                      'voigt': voigt,
                      'pvoigt': pvoigt,
                      'pearson7': pearson7,
                      'gammaln': _gammaln,
                      'erf': _erf,
                      'erfc': _erfc,
                      'wofz': _wofz})
