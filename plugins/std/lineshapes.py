#!/usr/bin/env python
"""
Some common lineshapes and distribution functions
"""
from numpy import pi, log, exp, sqrt

from scipy.special import gamma, beta

log2 = log(2)

def gaussian(x, amp, cen, sigma, larch=None):
    "1 dimensional gaussian"
    return (sqrt(log2/pi) / sigma) * amp * exp(-log2 * (1.0*x-cen) **2 / sigma**2)

def lorentzian(x, amp, cen, sigma, larch=None):
    "1 dimensional lorentzian"
    return (amp  / (1 + ((1.0*x-cen)/sigma)**2) ) / (pi*sigma)

def pvoigt(x, amp, cen, sigma, frac, larch=None):
    "1 dimensional pseudo-voight: amp*(1-frac)*gaussion + amp*frac*lorentzian"
    return amp * (gaussiann(x, (1-frac), cen, sigma) +
                  lorentzian(x, frac,    cen, sigma))

def pearson7(x, amp, cen, sigma, expon, larch=None):
    """"pearson7 lineshape, according to NIST StRD
    though it seems wikpedia gives a different formula... """
    scale = amp * gamma(expon) * sqrt((2**(1/expon) -1)) / (gamma(expon-0.5)) / (sigma*sqrt(pi))
    return scale / (1 + ( ((1.0*x-cen)/sigma)**2) * (2**(1/expon) -1) )**expon


def registerLarchPlugin():
    return ('_math', {'gaussian': gaussian,
                      'lorentzian': lorentzian,
                      'pvoigt': pvoigt,
                      'pearson7': pearson7})
