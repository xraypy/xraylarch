"""
Basic Fitting Models for 1-D data, simplifying fits to many standard line shapes.

  usage:
  ------
  param_group = fit_peak(x, y, model, dy=None,
                         background='linear', form='linear')

  arguments:
  ---------
  x           array of values at which to calculate model
  y           array of values for model to try to match
  dy          array of values for uncertainty in y data to be matched.
  model       name of model to use.  One of (case insensitive)
                 'linear', 'quadratic', 'step', 'rectangle',
                 'exponential', 'gaussian', 'lorentzian', 'voigt'

  background  name of background model to use. One of (case insensitive)
                 None, 'constant', 'linear', or 'quadratic'
              this is ignored when model is 'linear' or 'quadratic'
  form        name of form to use for 'step' and 'rectangle' models.
              One of (case insensitive):
                 'linear', 'erf', or 'atan'
  output:
  -------
  param_group   Group with fit parameters, and
"""

import numpy as np
from scipy.special import gamma, gammaln, beta, betaln, erf, erfc, wofz
from lmfit import Parameter, Minimizer
from lmfit.model import Model

from lmfit.models import (update_param_vals, LinearModel, ConstantModel,
                          QuadraticModel, PolynomialModel, GaussianModel,
                          LorentzianModel, VoigtModel, PseudoVoigtModel,
                          MoffatModel, Pearson7Model, StudentsTModel,
                          BreitWignerModel, LognormalModel,
                          DampedOscillatorModel,
                          DampedHarmonicOscillatorModel,
                          ExponentialGaussianModel, SkewedGaussianModel,
                          DonaichModel, PowerLawModel, ExponentialModel,
                          StepModel, RectangleModel, ExpressionModel,
                          update_param_vals)


from .. import Group
from .utils import index_nearest, index_of, savitzky_golay

VALID_BKGS = ('constant', 'linear', 'quadratic')


MODELS = {'constant': ConstantModel,
          'linear': LinearModel,
          'quadratic': QuadraticModel,
          'step': StepModel,
          'rectangle': RectangleModel,
          'exponential': ExponentialModel,
          'gaussian': GaussianModel,
          'lorentzian': LorentzianModel,
          'voigt': VoigtModel,
          'pseudovoigt': PseudoVoigtModel,
          'pearson7': Pearson7Model,
          'dho': DampedHarmonicOscillatorModel,
          'expgaussian': ExponentialGaussianModel,
          'skewedgaussian': SkewedGaussianModel,
          'exponential': ExponentialModel,
          }

# a better guess for step and rectangle models
def step_guess(self, data, x=None, **kwargs):
    if x is None:
        return
    ymin, ymax = min(data), max(data)
    xmin, xmax = min(x), max(x)
    ntest = min(2, len(data)/5)
    step_up =  (data[:ntest].mean() > data[-ntest:].mean())

    dydx = savitzky_golay(np.gradient(data)/np.gradient(x), 5, 2)
    if step_up:
        cen = x[np.where(dydx==dydx.max())][0]
    else:
        cen = x[np.where(dydx==dydx.min())][0]

    pars = self.make_params(amplitude=(ymax-ymin), center=cen)
    pars['%ssigma' % self.prefix].set(value=(xmax-xmin)/5.0, min=0.0)
    return update_param_vals(pars, self.prefix, **kwargs)

def rect_guess(self, data, x=None, **kwargs):
    if x is None:
        return
    ymin, ymax = min(data), max(data)
    xmin, xmax = min(x), max(x)

    ntest = min(2, len(data)/5)
    step_up =  (data[:ntest].mean() > data[-ntest:].mean())


    dydx = savitzky_golay(np.gradient(data)/np.gradient(x), 5, 2)
    cen1 = x[np.where(dydx==dydx.max())][0]
    cen2 = x[np.where(dydx==dydx.min())][0]
    if step_up:
        center1 = cen1 # + (xmax+xmin)/4.0)/2.
        center2 = cen2 # + 3*(xmax+xmin)/4.0)/2.
    else:
        center1 = cen2 # + (xmax+xmin)/4.0)/2.0
        center2 = cen1 # + 3*(xmax+xmin)/4.0)/2.0

    pars = self.make_params(amplitude=(ymax-ymin),
                            center1=center1, center2=center2)

    pars['%ssigma1' % self.prefix].set(value=(xmax-xmin)/5.0, min=0.0)
    pars['%ssigma2' % self.prefix].set(value=(xmax-xmin)/5.0, min=0.0)
    return update_param_vals(pars, self.prefix, **kwargs)

StepModel.guess = step_guess
RectangleModel.guess = rect_guess

def fit_peak(x, y, model, dy=None, background=None, form=None, step=None,
             negative=False, use_gamma=False):
    """fit peak to one a selection of simple 1d models

    out = fit_peak(x, y, model, dy=None,
                   background='linear', form='linear')

    arguments:
    ---------
    x           array of values at which to calculate model
    y           array of values for model to try to match
    dy          array of values for uncertainty in y data to be matched.
    model       name of model to use.  One of (case insensitive)
                     'linear', 'quadratic', 'step', 'rectangle',
                      'gaussian', 'lorentzian', 'voigt', 'exponential'
    background  name of background model to use. One of (case insensitive)
                     None, 'constant', 'linear', or 'quadratic'
                this is ignored when model is 'linear' or 'quadratic'
    form        name of form to use for 'step' and 'rectangle' models.
                One of (case insensitive):
                    'linear', 'erf', or 'atan'
    negative    True/False for whether peak or steps are expected to go down.
    use_gamma   True/False for whether to use separate gamma parameter for
                voigt model.
    output:
    -------
    Group with fit parameters, and more...
    """
    if form is None and step is not None:
        form = step
    out = Group(name='fit_peak result', x=x*1.0, y=y*1.0, dy=1.0,
                model=model, background=background, form=form)

    weight = None
    if dy is not None:
        out.dy = 1.0*dy
        weight = 1.0/max(1.e-16, abs(dy))

    if model.lower() not in MODELS:
        raise ValueError('Unknown fit model: %s ' % model)

    kwargs = dict(negative=negative, background=background,
                  form=form, weight=weight)

    fitclass = MODELS[model.lower()]
    if fitclass == VoigtModel:
        kwargs['use_gamma'] = use_gamma

    mod = fitclass(**kwargs)
    pars = mod.guess(out.y, out.x)

    if background is not None:
        bkg = MODELS[background.lower()](prefix='bkg_')
        bpars = bkg.guess(out.y, x=out.x)
        for p, par  in bpars.items():
            par.value = 0.
            par.vary = True
        pars += bpars
        mod += bkg

    out.init_params = pars

    result = mod.fit(out.y, params=pars, x=out.x) # , dy=out.dy)
    out.fit = mod.eval(result.params, x=out.x)
    out.fit_init = mod.eval(pars, x=out.x)

    out.fit_details = result
    out.chi_square  = result.chisqr
    out.chi_reduced = result.redchi

    for attr in ('aic', 'bic', 'covar', 'rfactor', 'params', 'nvarys',
                 'nfree', 'ndata', 'var_names', 'nfev', 'success',
                 'errorbars', 'message', 'lmdif_message', 'residual'):
        setattr(out, attr, getattr(result, attr, None))

    if background is not None:
        comps = mod.eval_components(x=out.x)
        out.bkg = comps['bkg_']
    return out
