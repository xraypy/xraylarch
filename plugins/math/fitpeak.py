"""
Basic Fitting Models for 1-D data, simplifying fits to many standard line shapes.

  usage:
  ------
  param_group = fit_peak(x, y, model, dy=None,
                         background='linear', step='linear')

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
  step        name of step model to use for 'step' and 'rectangle' models.
              One of (case insensitive):
                 'linear', 'erf', or 'atan'
  output:
  -------
  param_group   Group with fit parameters, and
"""

import numpy as np
from scipy.special import gamma, gammaln, beta, betaln, erf, erfc, wofz

from larch import Group, Parameter, Minimizer, fitting, ValidateLarchPlugin

from larch_plugins.math import index_nearest, index_of

VALID_BKGS = ('constant', 'linear', 'quadratic')

LOG2 = np.log(2)
SQRT2   = np.sqrt(2)
SQRT2PI = np.sqrt(2*np.pi)
SQRTPI  = np.sqrt(np.pi)

class FitModel(object):
    """base class for fitting models"""
    invalid_bkg_msg = """Warning: unrecoginzed background option '%s'
expected one of the following:
   %s
"""
    def __init__(self, background=None, step=None, negative=None,
                 _larch=None, **kws):
        self.params = Group()
        self._larch = _larch
        self.initialize_background(background=background, **kws)

    def add_param(self, name, value=0, vary=True, **kws):
        if self._larch is not None:
            self._larch.symtable._sys.paramGroup = self.params
        p = Parameter(value=value, name=name, vary=vary,
                      _larch=self._larch,  **kws)
        setattr(self.params, name, p)

    def set_initval(self, param, value):
        param.value = value
        param._initval = value

    def set_init_bkg(self,val):
        if hasattr(self.params, 'bkg_offset'):
            self.set_initval(self.params.bkg_offset, val)

    def initialize_background(self, background=None,
                              offset=0, slope=0, quad=0):
        """initialize background parameters"""
        if background is None:
            return
        if background not in VALID_BKGS:
            print(self.invalid_bkg_msg % (repr(background),
                                          ', '.join(VALID_BKGS)))

        self.add_param('bkg_offset', value=offset, vary=True)
        if background.startswith('line'):
            self.add_param('bkg_slope', value=slope, vary=True)
        elif background.startswith('quad'):
            self.add_param('bkg_slope', value=slope, vary=True)
            self.add_param('bkg_quad', value=slope, vary=True)

    def calc_background(self, x):
        bkg = np.zeros_like(x)
        if hasattr(self.params, 'bkg_offset'):
            bkg += self.params.bkg_offset.value
        if hasattr(self.params, 'bkg_slope'):
            bkg += x*self.params.bkg_slope.value
        if hasattr(self.params, 'bkg_quad'):
            bkg += x*x*self.params.bkg_quad.value
        return bkg

    def __objective(self, params, y=None, x=None, dy=None, **kws):
        """fit objective function"""
        bkg = 0
        if x is not None: bkg = self.calc_background(x)
        if y is None:     y   = 0.0
        if dy is None:    dy  = 1.0
        model = self.model(self.params, x=x, dy=dy, **kws)
        return (model + bkg - y)/dy

    def model(self, params, x=None, **kws):
        raise NotImplementedError

    def guess_starting_values(self, params, y, x=None, **kws):
        raise NotImplementedError

    def fit_report(self, params=None, min_correl=0.2, **kws):
        if params is None:
            params = self.params
        return fitting.fit_report(params, min_correl=min_correl,
                                  _larch=self._larch, **kws)

    def fit(self, y, x=None, dy=None, _larch=None, **kws):
        fcn_kws={'y':y, 'x':x, 'dy':dy}
        fcn_kws.update(kws)
        if _larch is not None:
            self._larch = _larch
        f = Minimizer(self.__objective, self.params,
                      _larch=self._larch, fcn_kws=fcn_kws,
                      scale_covar=True)
        f.leastsq()
        return f

class LinearModel(FitModel):
    """Linear Model: slope, offset, no background"""
    def __init__(self, offset=0, slope=0, **kws):
        kws['background'] = None
        FitModel.__init__(self, **kws)
        self.add_param('offset', value=offset)
        self.add_param('slope',  value=slope)

    def guess_starting_values(self, y, x):
        sval, oval = np.polyfit(x, y, 1)
        self.set_initval(self.params.offset, oval)
        self.set_initval(self.params.slope, sval)

    def model(self, params=None, x=None, **kws):
        if params is None:
            params = self.params
        return params.offset.value +  x * params.slope.value

class QuadraticModel(FitModel):
    """Quadratic Model: slope, offset, quad, no background"""
    def __init__(self, offset=0, slope=0, quad=0, **kws):
        kws['background'] = None
        FitModel.__init__(self, **kws)
        self.add_param('offset', value=offset)
        self.add_param('slope',  value=slope)
        self.add_param('quad',  value=quad)

    def guess_starting_values(self, y, x):
        qval, sval, oval = np.polyfit(x, y, 2)
        self.set_initval(self.params.offset, oval)
        self.set_initval(self.params.slope, sval)
        self.set_initval(self.params.quad, qval)

    def model(self, params=None, x=None, **kws):
        if params is None:
            params = self.params
        return params.offset.value +  x * (params.slope.value +
                                              x * params.quad.value)

class ExponentialModel(FitModel):
    """Exponential Model: amplitude, decay, optional background"""
    def __init__(self, amplitude=1, decay=1, background=None, **kws):
        FitModel.__init__(self, background=background, **kws)
        self.add_param('amplitude', value=amplitude)
        self.add_param('decay',  value=decay)

    def guess_starting_values(self, y, x):
        try:
            sval, oval = np.polyfit(x, np.log(abs(y)), 1)
        except:
            sval, oval = 1., np.log(abs(max(y)+1.e-9))
        self.set_initval(self.params.amplitude, np.exp(oval))
        self.set_initval(self.params.decay, (max(x)-min(x))/10.)
        self.set_init_bkg(min(y))

    def model(self, params=None, x=None, **kws):
        if params is None:
            params = self.params
        amp   = params.amplitude.value
        decay = params.decay.value
        return amp*np.exp(-x / decay)

class PeakModel(FitModel):
    """Generalization for Gaussian/Lorentzian/Voigt Model:
       amplitude, center, sigma, optional background
       sets bounds: sigma >= 0
       """
    def __init__(self, amplitude=1, center=0, sigma=1,
                 negative=False, background=None, **kws):
        FitModel.__init__(self, background=background, **kws)
        self.add_param('amplitude', value=amplitude)
        self.add_param('center',  value=center)
        self.add_param('sigma',  value=sigma, min=1.e-10)
        self.negative = negative

    def guess_starting_values(self, y, x):
        """could probably improve this"""
        ymax, ymin = max(y), min(y)
        yex = ymax
        self.set_initval(self.params.amplitude, 5.*(ymax-ymin))
        if self.negative:
            yex = ymin
            self.params.amplitude.value = -(ymax - ymin)*5.0
        iyex = index_nearest(y, yex)
        self.set_initval(self.params.center, x[iyex])

        halfy = yex /2.0
        ihalfy = index_of(y, halfy)
        sig0 = abs(x[iyex] - x[ihalfy])
        sig1 = 0.15*(max(x) - min(x))
        if sig1 < sig0 : sig0 = sig1
        self.set_initval(self.params.sigma,  sig0)
        bkg0 = ymin
        if self.negative: bkg0 = ymax
        self.set_init_bkg(bkg0)

    def model(self, params=None, x=None, **kws):
        pass

class GaussianModel(PeakModel):
    """Gaussian Model:
    amplitude, center, sigma, optional background"""
    def __init__(self, amplitude=1, center=0, sigma=1,
                 negative=False, background=None, **kws):
        PeakModel.__init__(self, amplitude=amplitude, center=center,
                           sigma=sigma, negative=negative,
                           background=background, **kws)
        self.add_param('fwhm',  expr='2.354820*sigma', vary=False)

    def model(self, params=None, x=None, **kws):
        if params is None:
            params = self.params
        amp = params.amplitude.value
        cen = params.center.value
        sig = params.sigma.value
        amp = amp/(SQRT2PI*sig)
        return amp * np.exp(-(x-cen)**2 / (2*sig**2))

class LorentzianModel(PeakModel):
    """Lorentzian Model:
    amplitude, center, sigma, optional background"""
    def __init__(self, amplitude=1, center=0, sigma=1,
                 negative=False, background=None, **kws):
        PeakModel.__init__(self, amplitude=amplitude, center=center, sigma=sigma,
                           negative=negative, background=background, **kws)
        self.add_param('fwhm',  expr='2*sigma', vary=False)

    def model(self, params=None, x=None, **kws):
        if params is None:
            params = self.params
        amp = params.amplitude.value
        cen = params.center.value
        sig = params.sigma.value
        return (amp/(1 + ((x-cen)/sig)**2))/(np.pi*sig)

class VoigtModel(PeakModel):
    """Voigt Model:
    amplitude, center, sigma, optional background
    this version sets gamma=sigma
    """
    def __init__(self, amplitude=1, center=0, sigma=1, use_gamma=False,
                 negative=False, background=None, **kws):
        PeakModel.__init__(self, amplitude=amplitude, center=center, sigma=sigma,
                           negative=negative, background=background, **kws)
        self.add_param('fwhm',  expr='3.60131*sigma', vary=False)
        if use_gamma:
            self.add_param('gamma',  vary=True)
        else:
            self.add_param('gamma',  expr='1.0*sigma', vary=False)

    def guess_starting_values(self, y, x):
        PeakModel.guess_starting_values(self, y, x)
        self.set_initval(self.params.gamma, self.params.sigma._getval())

    def model(self, params=None, x=None, **kws):
        if params is None:
            params = self.params
        amp = params.amplitude.value
        cen = params.center.value
        sig = params.sigma.value
        gam = params.gamma.value
        if gam is None: gam = sig
        z = (x-cen + 1j*gam) / (sig*SQRT2)
        return amp*wofz(z).real / (sig*SQRT2PI)

class StepModel(FitModel):
    """Step Model: height, center, width, optional background
    a step can be one of 'linear' (default), 'atan', or 'erf'
    which will give the functional form for going from 0 to height
   """
    def __init__(self, height=1, center=0, width=1, step='linear',
                 negative=False, background=None, **kws):
        FitModel.__init__(self, background=background, **kws)
        self.add_param('height', value=height)
        self.add_param('center',  value=center)
        self.add_param('width',  value=width, min=1.e-10)
        self.step = step
        self.negative=negative

    def guess_starting_values(self, y, x, negative=False):
        ymin, ymax = min(y), max(y)
        xmin, xmax = min(x), max(x)
        self.set_initval(self.params.center, 0.5*(xmax+xmin))
        self.set_initval(self.params.width,  0.1*(xmax-xmin))

        bkg0 = ymin
        height0 = ymax - ymin
        if self.negative:
            bkg0 = ymax
            height0 = -height0
        self.set_initval(self.params.height, height0)
        self.set_init_bkg(bkg0)

    def model(self, params=None, x=None, **kws):
        if params is None:
            params = self.params
        height = params.height.value
        center = params.center.value
        width  = params.width.value
        out = (x - center)/max(width, 1.e-13)
        if self.step == 'atan':
            out = 0.5 + np.arctan(out)/np.pi
        elif self.step == 'erf':
            out = 0.5*(1 + erf(out))
        else: # linear
            out[np.where(out<0)] = 0.0
            out[np.where(out>1)] = 1.0
        return height*out

class RectangularModel(FitModel):
    """Rectangular Model:  a step up and a step down:

    height, center1, center2, width1, width2, optional background

    a step can be one of 'linear' (default), 'atan', or 'erf'
    which will give the functional form for going from 0 to height
   """
    def __init__(self, height=1, center1=0, width1=1,
                 center2=1, width2=None, step='linear',
                 negative=False, background=None, **kws):
        FitModel.__init__(self, background=background, **kws)

        self.add_param('height',   value=height)
        self.add_param('center1',  value=center1)
        self.add_param('width1',   value=width1, min=1.e-10)
        self.add_param('center2',  value=center2)
        if width2 is None:
            self.add_param('width2',   expr='width1')
        else:
            self.add_param('width2',  value=width2, min=1.e-10)
        self.add_param('midpoint',
                       expr='(center1+center2)/2.0', vary=False)
        self.step = step
        self.negative = negative

    def guess_starting_values(self, y, x):
        ymin, ymax = min(y), max(y)
        xmin, xmax = min(x), max(x)
        self.set_initval(self.params.center1, 0.25*(xmax+xmin))
        self.set_initval(self.params.width1,  0.12*(xmax-xmin))
        self.set_initval(self.params.center2, 0.75*(xmax+xmin))
        self.set_initval(self.params.width2,  0.12*(xmax-xmin))

        bkg0 = ymin
        height0 = ymax - ymin
        if self.negative:
            bkg0 = ymax
            height0 = -height0
        self.set_initval(self.params.height, height0)
        self.set_init_bkg(bkg0)

    def model(self, params=None, x=None, **kws):
        if params is None:
            params = self.params
        height  = params.height.value
        center1 = params.center1.value
        width1  = params.width1.value
        center2 = params.center2.value
        width2  = params.width2.value

        arg1 = (x - center1)/max(width1, 1.e-13)
        arg2 = (center2 - x)/max(width2, 1.e-13)
        if self.step == 'atan':
            out = (np.arctan(arg1) + np.arctan(arg2))/np.pi
        elif self.step == 'erf':
            out = 0.5*(erf(arg1) + erf(arg2))
        else: # 'linear'
            arg1[np.where(arg1<0)] =  0.0
            arg1[np.where(arg1>1)] =  1.0
            arg2[np.where(arg2<-1)] = -1.0
            arg2[np.where(arg2>0)] =  0.0
            out = arg1 + arg2

        return height*out

MODELS = {'linear': LinearModel,
          'quadratic': QuadraticModel,
          'step': StepModel,
          'rectangle': RectangularModel,
          'exponential': ExponentialModel,
          'gaussian': GaussianModel,
          'lorentzian': LorentzianModel,
          'voigt': VoigtModel,
          }

@ValidateLarchPlugin
def fit_peak(x, y, model, dy=None, background=None, step=None,
             negative=False, use_gamma=False, _larch=None):
    """fit peak to one a selection of simple 1d models

    out = fit_peak(x, y, model, dy=None,
                   background='linear', step='linear')

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
    step        name of step model to use for 'step' and 'rectangle' models.
                One of (case insensitive):
                    'linear', 'erf', or 'atan'
    negative    True/False for whether peak or steps are expected to go down.
    use_gamma   True/False for whether to use separate gamma parameter for
                voigt model.
    output:
    -------
    Group with fit parameters, and more...
    """
    out = Group(x=x*1.0, y=y*1.0, dy=1.0, model=model,
                background=background, step=step)
    if dy is not None:
        out.dy = 1.0*dy
    if model.lower() not in MODELS:
        _larch.writer.write('Unknown fit model: %s ' % model)
        return None

    kwargs = dict(negative=negative, background=background,
                  step=step, _larch=_larch)

    fitclass = MODELS[model.lower()]
    if fitclass == VoigtModel:
        kwargs['use_gamma'] = use_gamma

    mod = fitclass(**kwargs)
    mod.guess_starting_values(out.y, out.x)

    out.fit_init = mod.model(x=out.x)
    if background is not None:
        out.bkg_init = mod.calc_background(out.x)
        out.fit_init += out.bkg_init

    mod.fit(out.y, x=out.x, dy=out.dy, _larch=_larch)

    out.fit = mod.model(x=out.x)
    if background is not None:
        out.bkg = mod.calc_background(out.x)
        out.fit += out.bkg
    out.params = mod.params
    return out

def registerLarchPlugin():
    return ('_math', {'fit_peak': fit_peak})
