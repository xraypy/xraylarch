#!/usr/bin/env python
"""
Some common lineshapes and distribution functions
"""
from numpy import (pi, log, exp, sqrt, arctan, cos, arange,
                   concatenate, convolve)

from scipy.special import gamma, gammaln, beta, betaln, erf, erfc, wofz
from larch import param_value

log2 = log(2)
s2pi = sqrt(2*pi)
spi  = sqrt(pi)
s2   = sqrt(2.0)

def gaussian(x, cen=0, sigma=1):
    """1 dimensional gaussian:
    gaussian(x, cen, sigma)
    """
    cen = param_value(cen)
    sig = param_value(sigma)
    return (1./(s2pi*sig)) * exp(-(1.0*x-cen)**2 /(2*sig**2))

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

    z = (x-cen + 1j*gamma)/ (sigma*s2)
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



def hypermet(x, amplitude, center, sigma, step=0, tail=0, gamma=0.1):
    """
    hypermet function to simulate XRF peaks and/or Compton Scatter Peak

    Arguments
    ---------
      x          array of ordinate (energy) values
      amplitude  overall scale factor
      center     peak centroid
      sigma      Gaussian sigma
      step       step parameter for low-x erfc step [0]
      tail       amplitude of tail function         [0]
      gamma      slope of tail function             [0.1]


    Notes
    -----
    The function is given by (with error checking for
    small values of sigma, gamma and s2 = sqrt(2) and
    s2pi = sqrt(2*pi)):

        arg  = (x - center)/sigma
        gaus = exp(-arg**2/2.0) / (s2pi*sigma)
        step = step * erfc(arg/s2) / (2*center)
        tail = tail * exp(arg/gamma) * erfc(arg/s2 + 1.0/(s2*gamma))
        tail = tail / (2*sigma*gamma*exp(-1.0/(2*gamma**2)))

        hypermet = amplitude * (peak + step + tail)

    This follows the definitions given in
        ED-XRF SPECTRUM EVALUATION AND QUANTITATIVE ANALYSIS
        USING MULTIVARIATE AND NONLINEAR TECHNIQUES
        P. Van Espen, P. Lemberge
        JCPDS-International Centre for Diffraction Data 2000,
        Advances in X-ray Analysis,Vol.43 560

    """

    sigma = max(1.e-8, sigma)
    gamma = max(0.1, gamma)
    arg   = (x - center)/sigma

    gaus = exp(-arg**2/2.0) / (s2pi*sigma)

    step = step * erfc(arg/s2) / (2*center)

    tail = tail * exp(arg/gamma) * erfc(arg/s2 + 1.0/(s2*gamma))
    tail = tail / (2*sigma*gamma*exp(-1.0/(2*gamma**2)))

    return amplitude * (gaus + step + tail)

def pearson7(x, cen=0, sigma=1, expon=0.5):
    """pearson7 lineshape, according to NIST StRD
    though it seems wikpedia gives a different formula...
    pearson7(x, cen, sigma, expon)
    """
    cen = param_value(cen)
    sigma = param_value(sigma)
    expon = param_value(expon)
    scale = gamma(expon) * sqrt((2**(1/expon) -1)) / (gamma(expon-0.5)) / (sigma*spi)
    return scale / (1 + ( ((1.0*x-cen)/sigma)**2) * (2**(1/expon) -1) )**expon

def breit_wigner(x, cen=0, sigma=1, q=1):
    """Breit-Wigner-Fano lineshape:
        = (q*sigma/2 + x - cen)**2 / ( (sigma/2)**2 + (x - cen)**2 )
    """
    gam = sigma/2.0
    return  (q*gam + x - cen)**2 / (gam*gam + (x-cen)**2)

def damped_oscillator(x, cen=1., sigma=0.1):
    """amplitude for a damped harmonic oscillator
    1 /sqrt( (1.0 - (x/cen)**2)**2 + (2*sigma*x/cen)**2))
    """
    cen = max(1.e-9, abs(cen))
    return (1./sqrt( (1.0 - (x / cen)**2)**2 + (2*sigma*x/cen)**2))

def logistic(x, cen=0, sigma=1.):
    """Logistic lineshape (yet another sigmoidal curve)
        = 1.  - 1. / (1 + exp((x-cen)/sigma))
    """
    return ( 1. - 1./(1. + exp((x-cen)/sigma)))

def lognormal(x, cen=0, sigma=1):
    """log-normal function
    lognormal(x, cen, sigma)
          = (1/x) * exp(-(ln(x) - cen)/ (2* sigma**2))
    """
    cen = param_value(cen)
    sig = param_value(sigma)
    return (1./(x*sig*s2pi)) * exp(-(log(x) - cen)**2/ (2* sig**2))

def students_t(x, cen=0, sigma=1):
    """Student's t distribution:
        gamma((sigma+1)/2)   (1 + (x-cen)**2/sigma)^(-(sigma+1)/2)
     =  -------------------------
        sqrt(sigma*pi)gamma(sigma/2)

    """
    s1  = (sigma+1)/2.0
    denom = (sqrt(sigma*pi)*gamma(sigma/2))
    return (1 + (x-cen)**2/sigma)**(-s1) * gamma(s1) / denom


def exgaussian(x, cen=0, sigma=1.0, gamma=1.0):
    """exponentially modified Gaussian

    = (gamma/2) exp[cen*gamma + (gamma*sigma)**2/2 - gamma*x] *
                erfc[(cen + gamma*sigma**2 - x)/(sqrt(2)*sigma)]

    http://en.wikipedia.org/wiki/Exponentially_modified_Gaussian_distribution
    """
    gss = gamma*sigma*sigma
    arg1 = gamma*(cen +gss/2.0 - x)
    arg2 = (cen + gss - x)/s2
    return (gamma/2) * exp(arg1) * erfc(arg2)

def donaich(x, cen=0, sigma=1.0, gamma=0.0):
    """Doniach Sunjic asymmetric lineshape, used for photo-emission

    = cos(pi*gamma/2 + (1-gamma) arctan((x-cen)/sigma) /
                (sigma**2 + (x-cen)**2)**[(1-gamma)/2]

    see http://www.casaxps.com/help_manual/line_shapes.htm
    """
    arg = (x-cen)/sigma
    gm1 = (1.0 - gamma)
    scale = 1.0/(sigma**gm1)
    return scale*cos(pi*gamma/2 + gm1*arctan(arg))/(1 + arg**2)**(gm1/2)

def skewed_voigt(x, cen=0, sigma=1.0, gamma=None, skew=0.0):
    """Skewed Voigt lineshape, skewed with error function
    useful for ad-hoc Compton scatter profile

    with beta = skew/(sigma*sqrt(2))
    = voigt(x, cen, sigma, gamma)*(1+erf(beta*(x-cen)))

    skew < 0:  tail to low value of centroid
    skew > 0:  tail to high value of centroid

    see http://en.wikipedia.org/wiki/Skew_normal_distribution
    """
    beta = skew/(s2*sigma)
    return (1 + erf(beta*(x-cen)))*voigt(x, cen=cen, sigma=sigma, gamma=gamma)

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

def gammaln(x):
    """log of absolute value of gamma function"""
    return gammaln(x)

def registerLarchPlugin():
    return ('_math', {'gaussian': gaussian,
                      'lorentzian': lorentzian,
                      'voigt': voigt,
                      'pvoigt': pvoigt,
                      'hypermet': hypermet,
                      'pearson7': pearson7,
                      'lognormal': lognormal,
                      'gammaln': gammaln,
                      'breit_wigner': breit_wigner,
                      'damped_oscillator': damped_oscillator,
                      'exgaussian': exgaussian,
                      'donaich': donaich,
                      'skewed_voigt': skewed_voigt,
                      'students_t': students_t,
                      'logistic': logistic,
                      'erf': _erf,
                      'erfc': _erfc,
                      'wofz': _wofz})
