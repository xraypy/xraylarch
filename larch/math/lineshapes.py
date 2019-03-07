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

def hypermet(x, amplitude=1.0, center=0., sigma=1.0, step=0, tail=0, gamma=0.1):
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
        gauss = (1.0/(s2pi*sigma)) * exp(-arg**2 /2)
        sfunc = step * max(gauss) * erfc(arg/2.0) / 2.0
        tfunc = tail * exp((x-center)/(gamma*sigma)) * erfc(arg/s2 + 1.0/gamma))
        hypermet = amplitude * (gauss + sfunc + tfunc) / 2.0

    This follows the definitions given in
        ED-XRF SPECTRUM EVALUATION AND QUANTITATIVE ANALYSIS
        USING MULTIVARIATE AND NONLINEAR TECHNIQUES
        P. Van Espen, P. Lemberge
        JCPDS-International Centre for Diffraction Data 2000,
        Advances in X-ray Analysis,Vol.43 560

    But is modified slightly to better preserve area with changing tail and gamma

    """
    sigma = max(1.e-8, sigma)
    gamma = max(1.e-8, gamma)
    arg   = (x - center)/sigma
    arg[where(arg>100)] = 100.0
    arg[where(arg<-100)] = -100.0
    gscale = s2pi*sigma
    gauss = (1.0/gscale) * exp(-arg**2 / 2.0)
    sfunc = step * special.erfc(arg/2.0) / (2.0*gscale)

    targ = (x-center)/(gamma*sigma)
    targ[where(targ>100)] = 100.0
    targ[where(targ<-100)] = -100.0

    tfunc = exp(targ) * special.erfc(arg/2.0 + 1.0/gamma)
    tfunc = tail*tfunc / (max(tfunc)*gscale)
    return amplitude * (gauss + sfunc + tfunc) /2.0



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
