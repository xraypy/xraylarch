#!/usr/bin/env python
"""
Some common lineshapes and distribution functions
"""
from numpy import pi, log, exp, sqrt, arange, concatenate, convolve

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
    lorentzian(x, cen, sigma)
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
    cen   = param_value(cen)
    sigma = param_value(sigma)
    gamma = param_value(gamma)

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

def lognormal(x, cen=0, sigma=1):
    """log-normal function
    lognormal(x, cen, sigma)
          = (1/x) * exp(-(ln(x) - cen)/ (2* sigma**2))
    """
    cen = param_value(cen)
    sigma = param_value(sigma)
    return (1./x) * exp(-(ln(x) - cen)/ (2* sigma**2))

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

def smooth(x, sigma=1, gamma=None, form='lorentzian', npad=15):
    """smooth an array with a lorentzian, gaussian, or voigt
    lineshape:

    smooth(x, sigma=1, gamma=None, form='lorentzian', npad=15)

    arguments:
    ----------
      x      input array for convoution
      sigma  primary width parameter for convolving function
      gamma  secondary width parameter for convolving function
      form   form for convolving function:
                'lorentzian' or 'gaussian' or 'voigt'
      npad   number of padding pixels to use [15]
    """

    wx = arange(2*npad)
    if form.lower().startswith('gauss'):
        win = gaussian(wx, cen=npad, sigma=sigma)
    elif form.lower().startswith('voig'):
        win = voigt(wx, cen=npad, sigma=sigma, gamma=gamma)
    else:
        win = lorentzian(wx, cen=npad, sigma=sigma)
    xax = concatenate((x[2*npad:0:-1], x, x[-1:-2*npad-1:-1]))
    out = convolve(win/win.sum(), xax, mode='valid')
    nextra = int((len(out) - len(x))/2)
    return out[nextra+1:len(out)-nextra]

def registerLarchPlugin():
    return ('_math', {'gaussian': gaussian,
                      'lorentzian': lorentzian,
                      'voigt': voigt,
                      'pvoigt': pvoigt,
                      'pearson7': pearson7,
                      'lognormal': lognormal,
                      'gammaln': _gammaln,
                      'erf': _erf,
                      'erfc': _erfc,
                      'wofz': _wofz,
                      'smooth': smooth})
