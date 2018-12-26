#!/usr/bin/env python
"""
Some common lineshapes and distribution functions
"""

from __future__ import division

from numpy import exp, pi, sqrt
from scipy.special import erf, erfc, wofz, gamma, gammaln

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
        gauss = exp(-arg**2/2.0) / (s2pi*sigma)
        sfunc = step * erfc(arg/s2) / (2.0*center)
        tfunc = tail * exp((x-center)/gamma) * erfc(arg/s2 + sigma/(s2*gamma))
        hypermet = amplitude * (gauss + sfunc + tfunc)

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

    gauss = exp(-arg**2/2.0) / (s2pi*sigma)
    sfunc = step * erfc(arg/s2) / (2.0*center)
    tfunc = tail * exp((x-center)/gamma) * erfc(arg/s2 + sigma/(s2*gamma))

    return amplitude * (gauss + sfunc + tfunc)


# def erf(x):
#     """Return the error function.
#
#     erf = 2/sqrt(pi)*integral(exp(-t**2), t=[0, z])
#
#     """
#     return special.erf(x)
#
#
# def erfc(x):
#     """Return the complementary error function.
#
#     erfc = 1 - erf(x)
#
#     """
#     return special.erfc(x)
#
#
# def wofz(x):
#     """Return the fadeeva function for complex argument.
#
#     wofz = exp(-x**2)*erfc(-i*x)
#
#     """
#     return special.wofz(x)
#
#
# def gamma(x):
#     """Return the gamma function."""
#     return special.gamma(x)
#
#
# def gammaln(x):
#     """Return the log of absolute value of gamma function."""
#     return special.gammaln(x)
