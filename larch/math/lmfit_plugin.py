from lmfit import Parameters, Parameter, minimize, models

from lmfit.model import (save_model, load_model, save_modelresult,
                         load_modelresult)

lmobjs = {'Parameters': Parameters,
          'Parameter': Parameter,
          'lm_minimize': minimize,
          'lm_save_model': save_model,
          'lm_load_model': load_model,
          'lm_save_modelresult': save_modelresult,
          'lm_load_modelresult': load_modelresult,
          }

for name in ('BreitWignerModel', 'ComplexConstantModel',
             'ConstantModel', 'DampedHarmonicOscillatorModel',
             'DampedOscillatorModel', 'DonaichModel',
             'ExponentialGaussianModel', 'ExponentialModel',
             'ExpressionModel', 'GaussianModel', 'Interpreter',
             'LinearModel', 'LognormalModel', 'LorentzianModel',
             'MoffatModel', 'ParabolicModel', 'Pearson7Model',
             'PolynomialModel', 'PowerLawModel',
             'PseudoVoigtModel', 'QuadraticModel',
             'RectangleModel', 'SkewedGaussianModel',
             'StepModel', 'StudentsTModel', 'VoigtModel'):
    val = getattr(models, name, None)
    if val is not None:
        lmobjs[name] = val

def registerLarchPlugin():
    return ('_math',  lmobjs)
