#!/usr/bin/env python
"""
Some common lineshapes and distribution functions
"""

from __future__ import division

from numpy import exp, pi, sqrt, where

from scipy.special import erfc as sp_erfc
from scipy.special import wofz as sp_wofz
from scipy.special import erf as sp_erf
from scipy.special import gamma as sp_gamma
from scipy.special import gammaln as sp_gammaln

from lmfit.lineshapes import (gaussian, lorentzian, voigt, pvoigt, moffat,
                              pearson7, breit_wigner, damped_oscillator,
                              dho, logistic, lognormal, students_t,
                              doniach, skewed_gaussian, expgaussian,
                              skewed_voigt, step, rectangle, exponential,
                              powerlaw, linear, parabolic)

stau = sqrt(2*pi)
s2 = sqrt(2.0)

def hypermet(x, amplitude=1.0, center=0., sigma=1.0,
             step=0.1, tail=0.1, beta=0.5, gamma=0.01):
    """
    hypermet function to simulate XRF peaks and/or Compton Scatter Peak,
    slightly modified.

    Arguments
    ---------
      x          array of ordinate (energy) values
      amplitude  overall scale factor
      center     peak centroid
      sigma      peak width parameter sigma
      step       heigh of low-x erfc step function   [0.1]
      tail       height of tail function             [0.1]
      beta       slope of tail function              [0.5]
      gamma      gamma value for Voigt lineshape     [0.01]


    Notes
    -----
    The function is given by (with some error checking for
    small values of sigma, beta, and gamma, and with
    s2 = sqrt(2) and stau = sqrt(2*pi)):

        arg  = (x - center)/sigma
        if use_voigt:
            peak = wofz(arg+1j*gamma).real
        else:
            peak = exp(-arg**2 /2)

        stepfunc = step * erfc(arg/2.0) / 200.0
        tailfunc = tail * exp(arg/beta) * erfc(arg/s2 + 1.0/beta))
        hypermet = amplitude * (peak + stepfunc + tailfunc) / (2.0*stau*sigma)

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
    sigma = max(1.e-15, sigma)
    beta  = max(1.e-15, beta)*s2
    gamma = max(1.e-15, gamma)/s2
    step  = step/100.0

    arg   = (x - center)/(s2*sigma)
    arg[where(arg>700)] = 700.0

    peakfunc = sp_wofz((arg + 1j*gamma) ).real

    stepfunc = step*sp_erfc(arg)/(2*sp_wofz(1j*gamma).real)

    arg[where(arg>beta*350)] = beta*350.0
    tailfunc = sp_erfc(arg + 1./beta)*exp(2*arg/beta)
    tailfunc *= 2*tail/(beta*exp(-1.0/beta**2))

    return amplitude*(peakfunc + stepfunc + tailfunc)/(stau*sigma)

def erf(x):
    """Return the error function.
    erf = 2/sqrt(pi)*integral(exp(-t**2), t=[0, z])
    """
    return sp_erf(x)

def erfc(x):
    """Return the complementary error function.
    erfc = 1 - erf(x)
    """
    return sp_erfc(x)

def wofz(x):
    """Return the fadeeva function for complex argument.
    wofz = exp(-x**2)*erfc(-i*x)
    """
    return sp_wofz(x)

def gamma(x):
    """Return the gamma function."""
    return sp_gamma(x)

def gammaln(x):
    """Return the log of absolute value of gamma function."""
    return sp_gammaln(x)
