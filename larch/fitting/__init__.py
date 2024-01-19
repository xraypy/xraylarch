#!/usr/bin/env python

from copy import copy, deepcopy
import random
import numpy as np
from scipy.stats import f

import lmfit
from lmfit import Parameter
from lmfit import (Parameters, Minimizer, conf_interval,
                   ci_report, conf_interval2d)

from lmfit.minimizer import MinimizerResult
from lmfit.model import (ModelResult, save_model, load_model,
                         save_modelresult, load_modelresult)
from lmfit.confidence import f_compare

from lmfit.printfuncs import gformat, getfloat_attr
from uncertainties import ufloat, correlated_values
from uncertainties import wrap as un_wrap

from ..symboltable import Group, isgroup


def isParameter(x):
    return (isinstance(x, Parameter) or
            x.__class__.__name__ == 'Parameter')

def param_value(val):
    "get param value -- useful for 3rd party code"
    while isinstance(val, Parameter):
        val = val.value
    return val

def format_param(par, length=10, with_initial=True):
    value = repr(par)
    if isParameter(par):
        value = gformat(par.value, length=length)
        if not par.vary and par.expr is None:
            value = f"{value} (fixed)"
        else:
            stderr = 'unknown'
            if par.stderr is not None:
                stderr = gformat(par.stderr, length=length)
                value = f"{value} +/-{stderr}"
                if par.vary and par.expr is None and with_initial:
                    value = f"{value} (init={gformat(par.init_value, length=length)})"
            if par.expr is not None:
                value = f"{value}  = '{par.expr}'"
    return value


def stats_table(results, labels=None, csv_output=False, csv_delim=','):
    """
    create a table comparing fit statistics for multiple fit results
    """
    stats = {'number of variables': 'nvarys',
             'chi-square': 'chi_square',
             'reduced chi-square': 'chi2_reduced',
             'r-factor': 'rfactor',
             'Akaike Info Crit': 'aic',
             'Bayesian Info Crit': 'bic'}

    nfits = len(results)
    if labels is not None:
        if len(labels) != len(results):
            raise ValueError('labels must be a list that is the same length as results')

    columns = [['Statistics']]
    if labels is None:
        labels = [f"  Fit {i+1}" for i in range(nfits)]
    for lab in labels:
        columns.append([lab])

    for sname, attr in stats.items():
        columns[0].append(sname)
        for i, result in enumerate(results):
            columns[i+1].append(getfloat_attr(result, attr))

    return format_table_columns(columns, csv_output=csv_output, csv_delim=csv_delim)

def paramgroups_table(pgroups, labels=None, csv_output=False, csv_delim=','):
    """
    create a table comparing parameters from a Feffit Parameter Grooup for multiple fit results
    """
    nfits = len(pgroups)
    if labels is not None:
        if len(labels) != len(pgroups):
            raise ValueError('labels must be a list that is the same length as Parameter Groups')

    columns = [['Parameter']]
    if labels is None:
        labels = [f" Fit {i+1}" for i in range(nfits)]
    for lab in labels:
        columns.append([lab])

    parnames = []
    for pgroup in pgroups:
        for pname in dir(pgroup):
            if pname not in parnames:
                parnames.append(pname)

    for pname in parnames:
        columns[0].append(pname)
        for i, pgroup in enumerate(pgroups):
            value = 'N/A'
            par = getattr(pgroup, pname, None)
            if par is not None:
                value = format_param(par, length=10, with_initial=False)
            columns[i+1].append(value)

    return format_table_columns(columns, csv_output=csv_output, csv_delim=csv_delim)


def format_table_columns(columns, csv_output=False, csv_delim=','):
    hjoin, rjoin, edge = '+', '|', '|'
    if csv_output:
       hjoin, rjoin, edge = csv_delim, csv_delim, ''

    ncols = len(columns)
    nrows = len(columns[0])
    slen = [2]*ncols
    for i, col in enumerate(columns):
        slen[i] = max(5, max([len(row) for row in col]))

    buff = []
    if not csv_output:
        header = edge + hjoin.join(['-'*(lx+2) for lx in slen]) + edge
        buff = [header]

    while len(columns[0]) > 0:
        values = [c.pop(0) for c in columns]
        row = rjoin.join([f" {l:{slen[i]}.{slen[i]}s} " for i, l in enumerate(values)])
        buff.append(edge + row + edge)
        if not csv_output and len(buff) == 2:
            buff.append(header)
    if not csv_output:
        buff.append(header)
    return '\n'.join(buff)


def f_test(ndata, nvars, chisquare, chisquare0, nfix=1):
    """return the F-test value for the following input values:
    f = f_test(ndata, nparams, chisquare, chisquare0, nfix=1)

    nfix = the number of fixed parameters.
    """
    return f_compare(ndata, nvars, chisquare, chisquare0, nfix=1)

def confidence_report(conf_vals, **kws):
    """return a formatted report of confidence intervals calcualted
    by confidence_intervals
    """
    return ci_report(conf_vals)

def asteval_with_uncertainties(*vals, **kwargs):
    """Calculate object value, given values for variables.

    This is used by the uncertainties package to calculate the
    uncertainty in an object even with a complicated expression.

    """
    _obj = kwargs.get('_obj', None)
    _pars = kwargs.get('_pars', None)
    _names = kwargs.get('_names', None)
    _asteval = _pars._asteval
    if (_obj is None or _pars is None or _names is None or
         _asteval is None or _obj._expr_ast is None):
        return 0
    for val, name in zip(vals, _names):
        _asteval.symtable[name] = val

    # re-evaluate all constraint parameters to
    # force the propagation of uncertainties
    [p._getval() for p in _pars.values()]
    return _asteval.eval(_obj._expr_ast)


wrap_ueval = un_wrap(asteval_with_uncertainties)


def eval_stderr(obj, uvars, _names, _pars):
    """Evaluate uncertainty and set ``.stderr`` for a parameter `obj`.

    Given the uncertain values `uvars` (list of `uncertainties.ufloats`),
    a list of parameter names that matches `uvars`, and a dictionary of
    parameter objects, keyed by name.

    This uses the uncertainties package wrapped function to evaluate the
    uncertainty for an arbitrary expression (in ``obj._expr_ast``) of
    parameters.

    """
    if not isinstance(obj, Parameter) or getattr(obj, '_expr_ast', None) is None:
        return
    uval = wrap_ueval(*uvars, _obj=obj, _names=_names, _pars=_pars)
    try:
        obj.stderr = uval.std_dev
    except Exception:
        obj.stderr = 0


class ParameterGroup(Group):
    """
    Group for Fitting Parameters
    """
    def __init__(self, name=None, **kws):
        if name is not None:
            self.__name__ = name
        if '_larch' in kws:
            kws.pop('_larch')
        self.__params__ = Parameters()
        Group.__init__(self)
        self.__exprsave__ = {}
        for key, val in kws.items():
            expr = getattr(val, 'expr', None)
            if expr is not None:
                self.__exprsave__[key] =  expr
                val.expr = None
            setattr(self, key, val)

        for key, val in self.__exprsave__.items():
            self.__params__[key].expr = val


    def __repr__(self):
        return '<Param Group {:s}>'.format(self.__name__)

    def __setattr__(self, name, val):
        if isParameter(val):
            if val.name != name:
                # allow 'a=Parameter(2, ..)' to mean Parameter(name='a', value=2, ...)
                nval = None
                try:
                    nval = float(val.name)
                except (ValueError, TypeError):
                    pass
                if nval is not None:
                    val.value = nval
            skip = getattr(val, 'skip', None)
            self.__params__.add(name, value=val.value, vary=val.vary, min=val.min,
                              max=val.max, expr=val.expr, brute_step=val.brute_step)
            val = self.__params__[name]

            val.skip = skip
        elif hasattr(self, '__params__') and not name.startswith('__'):
            self.__params__._asteval.symtable[name] = val
        self.__dict__[name] = val

    def __delattr__(self, name):
        self.__dict__.pop(name)
        if name in self.__params__:
            self.__params__.pop(name)

    def __add(self, name, value=None, vary=True, min=-np.inf, max=np.inf,
              expr=None, stderr=None, correl=None, brute_step=None, skip=None):
        if expr is None and isinstance(value, str):
            expr = value
            value = None
        if self.__params__  is not None:
            self.__params__.add(name, value=value, vary=vary, min=min, max=max,
                              expr=expr, brute_step=brute_step)
            self.__params__[name].stderr = stderr
            self.__params__[name].correl = correl
            self.__params__[name].skip = skip
            self.__dict__[name] = self.__params__[name]


def param_group(**kws):
    "create a parameter group"
    return ParameterGroup(**kws)

def randstr(n):
    return ''.join([chr(random.randint(97, 122)) for i in range(n)])

class unnamedParameter(Parameter):
    """A Parameter that can be nameless"""
    def __init__(self, name=None, value=None, vary=True, min=-np.inf, max=np.inf,
                 expr=None, brute_step=None, user_data=None, skip=None):
        if name is None:
            name = randstr(8)
        self.name = name
        self.user_data = user_data
        self.init_value = value
        self.min = min
        self.max = max
        self.brute_step = brute_step
        self.vary = vary
        self.skip = skip
        self._expr = expr
        self._expr_ast = None
        self._expr_eval = None
        self._expr_deps = []
        self._delay_asteval = False
        self.stderr = None
        self.correl = None
        self.from_internal = lambda val: val
        self._val = value
        self._init_bounds()
        Parameter.__init__(self, name, value=value, vary=vary,
                           min=min, max=max, expr=expr,
                           brute_step=brute_step,
                           user_data=user_data)

def param(*args, **kws):
    "create a fitting Parameter as a Variable"
    if len(args) > 0:
        a0 = args[0]
        if isinstance(a0, str):
            kws.update({'expr': a0})
        elif isinstance(a0, (int, float)):
            kws.update({'value': a0})
        else:
            raise ValueError("first argument to param() must be string or number")
        args = args[1:]
    if '_larch' in kws:
        kws.pop('_larch')
    if 'vary' not in kws:
        kws['vary'] = False

    return unnamedParameter(*args, **kws)

def guess(value,  **kws):
    """create a fitting Parameter as a Variable.
    A minimum or maximum value for the variable value can be given:
       x = guess(10, min=0)
       y = guess(1.2, min=1, max=2)
    """
    kws.update({'vary':True})
    return param(value, **kws)

def is_param(obj):
    """return whether an object is a Parameter"""
    return isParameter(obj)

def dict2params(pars):
    """sometimes we get a plain dict of Parameters,
    with vals that are Parameter objects"""
    if isinstance(pars, Parameters):
        return pars
    out = Parameters()
    for key, val in pars.items():
        if isinstance(val, Parameter):
            out[key] = val
    return out

def group2params(paramgroup):
    """take a Group of Parameter objects (and maybe other things)
    and put them into a lmfit.Parameters, ready for use in fitting
    """
    if isinstance(paramgroup, Parameters):
        return paramgroup
    if isinstance(paramgroup, dict):
        params = Parameters()
        for key, val in paramgroup.items():
            if isinstance(val, Parameter):
                params[key] = val
        return params


    if isinstance(paramgroup, ParameterGroup):
        return paramgroup.__params__

    params = Parameters()
    if paramgroup is not None:
        for name in dir(paramgroup):
            par = getattr(paramgroup, name)
            if getattr(par, 'skip', None) not in (False, None):
                continue
            if isParameter(par):
                params.add(name, value=par.value, vary=par.vary,
                           min=par.min, max=par.max,
                           brute_step=par.brute_step)
            else:
                params._asteval.symtable[name] = par

        # now set any expression (that is, after all symbols are defined)
        for name in dir(paramgroup):
            par = getattr(paramgroup, name)
            if isParameter(par) and par.expr is not None:
                params[name].expr = par.expr

    return params

def params2group(params, paramgroup):
    """fill Parameter objects in paramgroup with
    values from lmfit.Parameters
    """
    _params = getattr(paramgroup, '__params__', None)
    for name, param in params.items():
        this = getattr(paramgroup, name, None)
        if isParameter(this):
            if _params is not None:
                _params[name] = this
            for attr in ('value', 'vary', 'stderr', 'min', 'max', 'expr',
                         'name', 'correl', 'brute_step', 'user_data'):
                setattr(this, attr, getattr(param, attr, None))
            if this.stderr is not None:
                try:
                    this.uvalue = ufloat(this.value, this.stderr)
                except:
                    pass


def minimize(fcn, paramgroup, method='leastsq', args=None, kws=None,
             scale_covar=True, iter_cb=None, reduce_fcn=None, nan_polcy='omit',
             **fit_kws):
    """
    wrapper around lmfit minimizer for Larch
    """
    if isinstance(paramgroup, ParameterGroup):
        params = paramgroup.__params__
    elif isgroup(paramgroup):
        params = group2params(paramgroup)
    elif isinstance(Parameters):
        params = paramgroup
    else:
        raise ValueError('minimize takes ParamterGroup or Group as first argument')

    if args is None:
        args = ()
    if kws is None:
        kws = {}

    def _residual(params):
        params2group(params, paramgroup)
        return fcn(paramgroup, *args,  **kws)

    fitter = Minimizer(_residual, params, iter_cb=iter_cb,
                       reduce_fcn=reduce_fcn, nan_policy='omit', **fit_kws)

    result = fitter.minimize(method=method)
    params2group(result.params, paramgroup)

    out = Group(name='minimize results', fitter=fitter, fit_details=result,
                chi_square=result.chisqr, chi_reduced=result.redchi)

    for attr in ('aic', 'bic', 'covar', 'params', 'nvarys',
                 'nfree', 'ndata', 'var_names', 'nfev', 'success',
                 'errorbars', 'message', 'lmdif_message', 'residual'):
        setattr(out, attr, getattr(result, attr, None))
    return out

def fit_report(fit_result, modelpars=None, show_correl=True, min_correl=0.1,
               sort_pars=True, **kws):
    """generate a report of fitting results
    wrapper around lmfit.fit_report

    The report contains the best-fit values for the parameters and their
    uncertainties and correlations.

    Parameters
    ----------
    fit_result : result from fit
       Fit Group output from fit, or lmfit.MinimizerResult returned from a fit.
    modelpars : Parameters, optional
       Known Model Parameters.
    show_correl : bool, optional
       Whether to show list of sorted correlations (default is True).
    min_correl : float, optional
       Smallest correlation in absolute value to show (default is 0.1).
    sort_pars : bool or callable, optional
       Whether to show parameter names sorted in alphanumerical order. If
       False, then the parameters will be listed in the order they
       were added to the Parameters dictionary. If callable, then this (one
       argument) function is used to extract a comparison key from each
       list element.

    Returns
    -------
    string
       Multi-line text of fit report.


    """
    result = getattr(fit_result, 'fit_details', fit_result)
    if isinstance(result,  MinimizerResult):
        return lmfit.fit_report(result, modelpars=modelpars,
                                show_correl=show_correl,
                                min_correl=min_correl, sort_pars=sort_pars)
    elif isinstance(result,  ModelResult):
        return result.fit_report(modelpars=modelpars,
                                 show_correl=show_correl,
                                 min_correl=min_correl, sort_pars=sort_pars)
    else:
        result = getattr(fit_result, 'params', fit_result)
        if isinstance(result,  Parameters):
            return lmfit.fit_report(result, modelpars=modelpars,
                                    show_correl=show_correl,
                                    min_correl=min_correl, sort_pars=sort_pars)
        else:
            try:
                result = group2params(fit_result)
                return lmfit.fit_report(result, modelpars=modelpars,
                                        show_correl=show_correl,
                                        min_correl=min_correl, sort_pars=sort_pars)
            except (ValueError, AttributeError):
                pass
    return "Cannot make fit report with %s" % repr(fit_result)


def confidence_intervals(fit_result, sigmas=(1, 2, 3), **kws):
    """calculate the confidence intervals from a fit
    for supplied sigma values

    wrapper around lmfit.conf_interval
    """
    fitter = getattr(fit_result, 'fitter', None)
    result = getattr(fit_result, 'fit_details', None)
    return conf_interval(fitter, result, sigmas=sigmas, **kws)

def chi2_map(fit_result, xname, yname, nx=21, ny=21, sigma=3, **kws):
    """generate a confidence map for any two parameters for a fit

    Arguments
    ==========
       minout   output of minimize() fit (must be run first)
       xname    name of variable parameter for x-axis
       yname    name of variable parameter for y-axis
       nx       number of steps in x [21]
       ny       number of steps in y [21]
       sigma    scale for uncertainty range [3]

    Returns
    =======
        xpts, ypts, map

    Notes
    =====
     1.  sigma sets the extent of values to explore:
              param.value +/- sigma * param.stderr
    """
    #
    fitter = getattr(fit_result, 'fitter', None)
    result = getattr(fit_result, 'fit_details', None)
    if fitter is None or result is None:
        raise ValueError("chi2_map needs valid fit result as first argument")

    x = result.params[xname]
    y = result.params[yname]
    xrange = (x.value + sigma * x.stderr, x.value - sigma * x.stderr)
    yrange = (y.value + sigma * y.stderr, y.value - sigma * y.stderr)

    return conf_interval2d(fitter, result, xname, yname,
                           limits=(xrange, yrange),
                           nx=nx, ny=ny, nsigma=2*sigma, **kws)

_larch_name = '_math'
exports = {'param': param,
           'guess': guess,
           'param_group': param_group,
           'confidence_intervals': confidence_intervals,
           'confidence_report': confidence_report,
           'f_test': f_test, 'chi2_map': chi2_map,
           'is_param': isParameter,
           'isparam': isParameter,
           'minimize': minimize,
           'ufloat': ufloat,
           'fit_report': fit_report,
           'Parameters': Parameters,
           'Parameter': Parameter,
           'lm_minimize': minimize,
           'lm_save_model': save_model,
           'lm_load_model': load_model,
           'lm_save_modelresult': save_modelresult,
           'lm_load_modelresult': load_modelresult,
           }

for name in ('BreitWignerModel', 'ComplexConstantModel',
             'ConstantModel', 'DampedHarmonicOscillatorModel',
             'DampedOscillatorModel', 'DoniachModel',
             'ExponentialGaussianModel', 'ExponentialModel',
             'ExpressionModel', 'GaussianModel', 'Interpreter',
             'LinearModel', 'LognormalModel', 'LorentzianModel',
             'MoffatModel', 'ParabolicModel', 'Pearson7Model',
             'PolynomialModel', 'PowerLawModel',
             'PseudoVoigtModel', 'QuadraticModel',
             'RectangleModel', 'SkewedGaussianModel',
             'StepModel', 'StudentsTModel', 'VoigtModel'):
    val = getattr(lmfit.models, name, None)
    if val is not None:
        exports[name] = val

_larch_builtins = {'_math': exports}
