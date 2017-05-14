#!/usr/bin/env python
import six
from copy import copy, deepcopy
import wx
import matplotlib
matplotlib.use("WXAgg")

from lmfit import (Parameter, Parameters, Minimizer, minimize, fit_report,
                   conf_interval, ci_report, conf_interval2d, ufloat,
                   correlated_values)

from lmfit.minimizer import eval_stderr
from lmfit.confidence import f_compare

# from .parameter import Parameter, isParameter, param_value
# from .minimizer import Minimizer, minimize, fit_report, eval_stderr
# from .confidence import conf_intervals , chisquare_map, conf_report, f_compare
# from .uncertainties import ufloat, correlated_values

def isParameter(x):
    return (isinstance(x, Parameter) or
            x.__class__.__name__ == 'Parameter')

def param_value(val):
    "get param value -- useful for 3rd party code"
    while isinstance(val, Parameter):
        val = val.value
    return val


def f_test(ndata, nvars, chisquare, chisquare0, nfix=1):
    """return the F-test value for the following input values:
    f = f_test(ndata, nparams, chisquare, chisquare0, nfix=1)

    nfix = the number of fixed parameters.
    """
    return f_compare(ndata, nvars, chisquare, chisquare0, nfix=1)

def confidence_report(conf_vals, **kws):
    """return a formatted report of confidence intervals calcualted
    by confidence_intervals"""

    return ci_report(conf_vals)

def confidence_intervals(minout, sigmas=(1, 2, 3),  **kws):
    """explicitly calculate the confidence intervals from a fit
    for supplied sigma values"""
    return conf_interval(minout, sigmas=sigmas, **kws)

def chi2_map(minout, xname, yname, nx=11, ny=11, xrange=None,
             yrange=None, sigmas=None, **kws):
    """generate a confidence map for any two parameters for a fit

    Arguments
    ==========
       minout   output of minimize() fit (must be run first)
       xname    name of variable parameter for x-axis
       yname    name of variable parameter for y-axis
       nx       number of steps in x [11]
       ny       number of steps in y [11]
       xrange   range of calculations for x [x.best +/- 5*x.stderr]
       yrange   range of calculations for y [y.best +/- 5*y.stderr]

    Returns
    =======
        xpts, ypts, map
    """
    return conf_interval2d(minout, xname, yname, nx=nx, ny=ny,
                           sigmas=sigmas, **kws)

def param(*args, **kws):
    "create a fitting Parameter as a Variable"
    if len(args) > 0:
        a0 = args[0]
        if isinstance(a0, six.string_types):
            kws.update({'expr': a0})
        elif isinstance(a0, (int, float)):
            kws.update({'value': a0})
        else:
            raise ValueError("first argument to param() must be string or number")
        args = args[1:]
    if '_larch' in kws:
        kws.pop('_larch')
    return Parameter(*args, **kws)

def guess(value,  **kws):
    """create a fitting Parameter as a Variable.
    A minimum or maximum value for the variable value can be given:
       x = guess(10, min=0)
       y = guess(1.2, min=1, max=2)
    """
    kws.update({'vary':True})
    return param(value, **kws)


def is_param(obj, _larch=None, **kws):
    """return whether an object is a Parameter"""
    return isParameter(obj)


def group2params(paramgroup, _larch=None):
    """take a Group of Parameter objects (and maybe other things)
    and put them into Larch's current fiteval namespace

    returns a lmfit Parameters set, ready for use in fitting
    """
    if _larch is None:
        return None

    fiteval  = _larch.symtable._sys.fiteval
    params = Parameters(asteval=fiteval)

    if paramgroup is not None:
        for name in dir(paramgroup):
            par = getattr(paramgroup, name)
            if isParameter(par):
                params.add(name, value=par.value, vary=par.vary,
                           min=par.min, max=par.max, expr=par.expr,
                           brute_step=par.brute_step)
            else:
                fiteval.symtable[name] = par
    return params

def params2group(params, paramgroup):
    """fill Parameter objects in paramgroup with
    values from lmfit.Parameters
    """
    for name, param in params.items():
        this = getattr(paramgroup, name, None)
        if is_param(this):
            for attr in ('value', 'vary', 'stderr', 'min', 'max', 'expr',
                         'name', 'correl', 'brute_step', 'user_data'):
                setattr(this, attr, getattr(param, attr, None))
