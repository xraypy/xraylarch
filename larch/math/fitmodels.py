"""
Fitting Models, some inherited from lmfit, some defined here.
"""

import numpy as np
from scipy.special import gamma, gammaln, beta, betaln, erf, erfc, wofz
from lmfit import Parameter, Minimizer
from lmfit.model import Model

from lmfit.models import (update_param_vals, ConstantModel,
                          ComplexConstantModel, LinearModel,
                          QuadraticModel, PolynomialModel,
                          SplineModel, SineModel, GaussianModel,
                          Gaussian2dModel, LorentzianModel,
                          SplitLorentzianModel, VoigtModel,
                          PseudoVoigtModel, MoffatModel,
                          Pearson4Model, Pearson7Model,
                          StudentsTModel, BreitWignerModel,
                          LognormalModel, DampedOscillatorModel,
                          DampedHarmonicOscillatorModel,
                          ExponentialGaussianModel,
                          SkewedGaussianModel, SkewedVoigtModel,
                          ThermalDistributionModel, DoniachModel,
                          PowerLawModel, ExponentialModel,
                          ExpressionModel, StepModel, RectangleModel)

from lmfit.lineshapes import step, rectangle

from .utils import index_nearest, index_of, savitzky_golay

VALID_BKGS = ('Constant', 'Linear', 'Quadratic')

STEPFUNC_DOC = """{form} step function
    Starts at 0.0, ends at `amplitude*sign(sigma)`, has a half-max at
    `center`, rising or falling linearly:
          amplitude * {equation}
    where ``arg = (x - center)/sigma``.
    Note that ``sigma > 0`` gives a rising step, while ``sigma < 0`` gives
    a falling step.
"""

STEPMODEL_DOC =  r"""A model for a {form} Step function.

    The model has three Parameters: `amplitude` `center`, and `sigma`.

    The step function starts with a value 0 and ends with a value of
    `amplitude*sign(sigma)`` rising or falling to `amplitudee/2` at
    `x = center`, with `x=sigma` setting the characteristic width of
    the step.

    Note that `sigma > 0` gives a rising step, while `sigma < 0` gives a
    falling step.
"""

def step_guess(self, data, x, **kwargs):
    """Estimate initial model parameter values from data."""
    ymin, ymax = min(data), max(data)
    xmin, xmax = min(x), max(x)
    pars = self.make_params(amplitude=(ymax-ymin),
                            center=(xmax+xmin)/2.0)
    n = len(data)
    sigma = 0.1*(xmax - xmin)
    if data[:n//5].mean() > data[-n//5:].mean():
        sigma = -sigma
    pars[f'{self.prefix}sigma'].set(value=sigma)
    return update_param_vals(pars, self.prefix, **kwargs)


def erf_step(x, amplitude=1.0, center=0.0, sigma=1.0):
    return step(x, amplitude=amplitude, center=center, sigma=sigma, form='erf')

def logi_step(x, amplitude=1.0, center=0.0, sigma=1.0):
    return step(x, amplitude=amplitude, center=center, sigma=sigma, form='logistic')

def atan_step(x, amplitude=1.0, center=0.0, sigma=1.0):
    return step(x, amplitude=amplitude, center=center, sigma=sigma, form='atan')

def linear_step(x, amplitude=1.0, center=0.0, sigma=1.0):
    return step(x, amplitude=amplitude, center=center, sigma=sigma, form='linear')


class LinearStepModel(Model):
    def __init__(self, prefix='', **kwargs):
        super().__init__(linear_step, prefix=prefix, **kwargs)

class AtanStepModel(Model):
    def __init__(self, prefix='', **kwargs):
        super().__init__(atan_step, prefix=prefix, **kwargs)

class LogiStepModel(Model):
    def __init__(self, prefix='', **kwargs):
        super().__init__(logi_step, prefix=prefix, **kwargs)

class ErfStepModel(Model):
    def __init__(self, prefix='', **kwargs):
        super().__init__(erf_step, prefix=prefix, **kwargs)

linear_step.__doc__ = STEPFUNC_DOC.format(form='linear', equation='min(1, max(0, arg + 0.5))')
atan_step.__doc__ = STEPFUNC_DOC.format(form='arctangent', equation='(0.5 + atan(arg)/pi)')
logi_step.__doc__ = STEPFUNC_DOC.format(form='logistic', equation='[1 - 1/(1 + exp(arg))]')
erf_step.__doc__ = STEPFUNC_DOC.format(form='error function', equation='(1 + erf(arg))/2.0')

LinearStepModel.__doc__ = STEPMODEL_DOC.format(form='linear')
AtanStepModel.__doc__ = STEPMODEL_DOC.format(form='arctangent')
LogiStepModel.__doc__ = STEPMODEL_DOC.format(form='logistic')
ErfStepModel.__doc__ = STEPMODEL_DOC.format(form='error function')

LinearStepModel.guess = step_guess
AtanStepModel.guess = step_guess
LogiStepModel.guess = step_guess
ErfStepModel.guess = step_guess


RECTFUNC_DOC = """{form} rectangle function: step up, step down.
    Starts at 0.0, rises to `amplitude` (at `center1` with width `sigma1`),
    then drops to 0.0 (at `center2` with width `sigma2`) with form
       {equation}

    where ``arg1 = (x - center1)/sigma1`` and ``arg2 = -(x - center2)/sigma2``.

    Note: unlike `step`, ``sigma1 > 0`` and ``sigma2 > 0``, so that a
    rectangle only supports a step up followed by a step down.  Use a constant
    offset and adjust amplitude to be negative if you need a rectangle that
    falls and then rises.
    """

def rectangle_guess(self, data, x, **kwargs):
    """Estimate initial model parameter values from data."""
    ymin, ymax = min(data), max(data)
    xmin, xmax = min(x), max(x)
    pars = self.make_params(amplitude=(ymax-ymin),
                            center1=(xmax+xmin)/4.0,
                            center2=3*(xmax+xmin)/4.0,
                            sigma1={'value': (xmax-xmin)/10.0, 'min': 0},
                            sigma2={'value': (xmax-xmin)/10.0, 'min': 0})

    return update_param_vals(pars, self.prefix, **kwargs)


def linear_rectangle(x, amplitude=1.0, center1=0.0, sigma1=1.0,
                       center2=1.0, sigma2=1.0):
    return rectangle(x, amplitude=amplitude, center1=center1, sigma1=sigma1,
                         center2=center2, sigma2=sigma2, form='linear')

def atan_rectangle(x, amplitude=1.0, center1=0.0, sigma1=1.0,
                       center2=1.0, sigma2=1.0):
    return rectangle(x, amplitude=amplitude, center1=center1, sigma1=sigma1,
                         center2=center2, sigma2=sigma2, form='atan')

def logi_rectangle(x, amplitude=1.0, center1=0.0, sigma1=1.0,
                       center2=1.0, sigma2=1.0):
    return rectangle(x, amplitude=amplitude, center1=center1, sigma1=sigma1,
                         center2=center2, sigma2=sigma2, form='logistic')

def erf_rectangle(x, amplitude=1.0, center1=0.0, sigma1=1.0,
                       center2=1.0, sigma2=1.0):
    return rectangle(x, amplitude=amplitude, center1=center1, sigma1=sigma1,
                         center2=center2, sigma2=sigma2, form='erf')

linear_rectangle.__doc__ = RECTFUNC_DOC.format(form='linear', equation='min(1, max(0, arg + 0.5))')
atan_rectangle.__doc__ = RECTFUNC_DOC.format(form='arctangent', equation='(0.5 + atan(arg)/pi)')
logi_rectangle.__doc__ = RECTFUNC_DOC.format(form='logistic', equation='[1 - 1/(1 + exp(arg))]')
erf_rectangle.__doc__ = RECTFUNC_DOC.format(form='error function', equation='(1 + erf(arg))/2.0')


class LinearRectangleModel(Model):
    def __init__(self, prefix='', **kwargs):
        super().__init__(linear_rectangle, prefix=prefix, **kwargs)

class AtanRectangleModel(Model):
    def __init__(self, prefix='', **kwargs):
        super().__init__(atan_rectangle, prefix=prefix, **kwargs)

class LogiRectangleModel(Model):
    def __init__(self, prefix='', **kwargs):
        super().__init__(logi_rectangle, prefix=prefix, **kwargs)

class ErfRectangleModel(Model):
    def __init__(self, prefix='', **kwargs):
        super().__init__(erf_rectangle, prefix=prefix, **kwargs)

RECTMODEL_DOC = r"""A model based on a Step-up and Step-down function.

    The model has five Parameters: `amplitude` (:math:`A`), `center1`
    (:math:`\mu_1`), `center2` (:math:`\mu_2`), `sigma1`
    (:math:`\sigma_1`), and `sigma2` (:math:`\sigma_2`).

    There same form is used for the step up and down
    and the Step down.
"""

LinearRectangleModel.__doc__ = RECTMODEL_DOC.format(form='linear')
AtanRectangleModel.__doc__ = RECTMODEL_DOC.format(form='arctangent')
LogiRectangleModel.__doc__ = RECTMODEL_DOC.format(form='logistic')
ErfRectangleModel.__doc__ = RECTMODEL_DOC.format(form='error function')

LinearRectangleModel.guess = rectangle_guess
AtanRectangleModel.guess = rectangle_guess
LogiRectangleModel.guess = rectangle_guess
ErfRectangleModel.guess = rectangle_guess
