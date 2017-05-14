"""
Some common lineshapes and distribution functions
"""
from larch.utils import (gaussian, lorentzian, voigt, pvoigt, hypermet,
                         pearson7, lognormal, gammaln,
                         breit_wigner, damped_oscillator,
                         expgaussian, donaich, skewed_voigt,
                         students_t, logistic, erf, erfc, wofz)

def registerLarchPlugin():
    return ('_math', dict(gaussian=gaussian, lorentzian=lorentzian,
                          voigt=voigt, pvoigt=pvoigt, hypermet=hypermet,
                          pearson7=pearson7, lognormal=lognormal,
                          gammaln=gammaln, breit_wigner=breit_wigner,
                          damped_oscillator=damped_oscillator,
                          expgaussian=expgaussian, donaich=donaich,
                          skewed_voigt=skewed_voigt, students_t=students_t,
                          logistic=logistic, erf=erf, erfc=erfc, wofz=wofz))
