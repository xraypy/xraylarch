from lmfit import Parameters, Parameter, minimize, models

lmobjs = {'Parameters': Parameters,
          'Parameter': Parameter,
          'minimize': minimize}

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
