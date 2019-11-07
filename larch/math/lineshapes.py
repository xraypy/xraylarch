#!/usr/bin/env python
"""
Some common lineshapes and distribution functions
"""

from __future__ import division

from numpy import exp, pi, sqrt, where
from scipy import special

from lmfit.lineshapes import (gaussian, lorentzian, voigt, pvoigt, moffat,
                              pearson7, breit_wigner, damped_oscillator,
                              dho, logistic, lognormal, students_t,
                              donaich, skewed_gaussian, expgaussian,
                              skewed_voigt, step, rectangle, exponential,
                              powerlaw, linear, parabolic)

s2pi = sqrt(2*pi)
s2 = sqrt(2.0)

def hypermet(x, amplitude=1.0, center=0., sigma=1.0,
             step=0.001, tail=0, beta=0.1,
             use_voigt=True, gamma=0.25):
    """
    hypermet function to simulate XRF peaks and/or Compton Scatter Peak,
    slightly modified.

    Arguments
    ---------
      x          array of ordinate (energy) values
      amplitude  overall scale factor
      center     peak centroid
      sigma      peak width parameter sigma
      step       step parameter for low-x erfc step [0.001]
      tail       amplitude of tail function         [0]
      beta       slope of tail function             [0.1]
      use_voigt  use Voigt lineshape instead of Gaussian [True]
      gamma      gamma value for Voigt lineshape [0.25


    Notes
    -----
    The function is given by (with some error checking for
    small values of sigma, beta, and gamma, and with
    s2 = sqrt(2) and s2pi = sqrt(2*pi)):

        arg  = (x - center)/sigma
        if use_voigt:
            peak = wofz(arg+1j*gamma).real
        else:
            peak = exp(-arg**2 /2)

        stepfunc = step * erfc(arg/2.0) / 200.0
        tailfunc = tail * exp(arg/beta) * erfc(arg/s2 + 1.0/beta))
        hypermet = amplitude * (peak + stepfunc + tailfunc) / (2.0*s2pi*sigma)

    This follows (for Gaussian lineshape) the definitions given in
        ED-XRF SPECTRUM EVALUATION AND QUANTITATIVE ANALYSIS
        USING MULTIVARIATE AND NONLINEAR TECHNIQUES
        P. Van Espen, P. Lemberge
        JCPDS-International Centre for Diffraction Data 2000,
        Advances in X-ray Analysis,Vol.43 560

    But is modified to prefer Voigt of Gaussian (as Lorentzian-like tails on the
    positive energy side of a peak are common), and to better preserve area with
    changing values of tail and beta.

    """
    sigma = max(1.e-8, sigma)
    beta = max(1.e-8, beta)
    gamma = max(1.e-8, gamma)
    arg   = (x - center)/sigma
    arg[where(arg>700)] = 700.0

    if use_voigt:
        peak = special.wofz(arg + 1j*gamma).real
    else:
        peak = exp(-arg**2 / 2.0)

    stepfunc = step*special.erfc((x-center)/(s2*sigma))/1000.0

    arg[where(arg>beta*700)] = beta*700.0

    tailfunc = exp(arg/beta) * special.erfc(arg/s2 + 1.0/(s2*beta))
    tailfunc *= tail / (2*beta*sigma*exp(-1/2*beta**2))
    return amplitude * (peak + stepfunc + tailfunc) / (2.0*s2pi*sigma)

def erf(x):
    """Return the error function.
    erf = 2/sqrt(pi)*integral(exp(-t**2), t=[0, z])
    """
    return special.erf(x)

def erfc(x):
    """Return the complementary error function.
    erfc = 1 - erf(x)
    """
    return special.erfc(x)

def wofz(x):
    """Return the fadeeva function for complex argument.
    wofz = exp(-x**2)*erfc(-i*x)
    """
    return special.wofz(x)

def gamma(x):
    """Return the gamma function."""
    return special.gamma(x)

def gammaln(x):
    """Return the log of absolute value of gamma function."""
    return special.gammaln(x)
