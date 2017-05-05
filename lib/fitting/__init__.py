#!/usr/bin/env python
import six
from copy import copy, deepcopy
import wx
import numpy as np
import matplotlib
matplotlib.use("WXAgg")

from ..symboltable import Group, isgroup

import lmfit
from lmfit import (Parameter, Parameters, Minimizer,
                   conf_interval, ci_report, conf_interval2d, ufloat,
                   correlated_values)

from lmfit.minimizer import eval_stderr
from lmfit.confidence import f_compare

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


class ParameterGroup(Group):
    """
    Group for Fitting Parameters
    """
    def __init__(self, name=None, _larch=None, **kws):
        if name is not None:
            self.__name__ = name

        self._larch = _larch
        self._params = None
        if _larch is not None:
            self._params = Parameters(asteval=_larch.symtable._sys.fiteval)
        Group.__init__(self)
        for key, val in kws.items():
            self.__add(key, val)

    def __repr__(self):
        return '<Param Group {:s}>'.format(self.__name__)

    def __setattr__(self, name, val):
        if isinstance(val, Parameter):
            self._params.add(name, value=val.value, vary=val.vary, min=val.min,
                              max=val.max, expr=val.expr, brute_step=val.brute_step)
            val = self._params[name]
        self.__dict__[name] = val

    def __add(self, name, value=None, vary=True, min=-np.inf, max=np.inf,
              expr=None, stderr=None, correl=None, brute_step=None):
        if expr is None and isinstance(value, six.string_types):
            expr = value
            value = None
        if self._params  is not None:
            self._params.add(name, value=value, vary=vary, min=min, max=max,
                              expr=expr, brute_step=brute_step)
            self._params[name].stderr = stderr
            self._params[name].correl = correl
            self.__dict__[name] = self._params[name]


def param_group(_larch=None, **kws):
    "create a parameter group"
    return ParameterGroup(_larch=_larch, **kws)

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
    if 'vary' not in kws:
        kws['vary'] = False
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

    if isinstance(paramgroup, ParameterGroup):
        return paramgroup._params

    fiteval  = _larch.symtable._sys.fiteval
    params = Parameters(asteval=fiteval)

    if paramgroup is not None:
        for name in dir(paramgroup):
            par = getattr(paramgroup, name)
            if isParameter(par):
                params.add(name, value=par.value, vary=par.vary,
                           min=par.min, max=par.max,
                           brute_step=par.brute_step)

            else:
                fiteval.symtable[name] = par

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
    for name, param in params.items():
        this = getattr(paramgroup, name, None)
        if is_param(this):
            for attr in ('value', 'vary', 'stderr', 'min', 'max', 'expr',
                         'name', 'correl', 'brute_step', 'user_data'):
                setattr(this, attr, getattr(param, attr, None))
            if this.stderr is not None:
                this.uvalue = ufloat((this.value, this.stderr))


def minimize(fcn, paramgroup, method='leastsq', args=None, kws=None,
             scale_covar=True, iter_cb=None, reduce_fcn=None, nan_polcy='omit',
             _larch=None, **fit_kws):
    """
    wrapper around lmfit minimizer for Larch
    """
    fiteval  = _larch.symtable._sys.fiteval
    if isinstance(paramgroup, ParameterGroup):
        params = paramgroup._params
    elif isgroup(paramgroup):
        params = group2params(paramgroup, _larch=_larch)
    elif isinstance(Parameters):
        params = paramgroup
    else:
        raise ValueError('minimize takes ParamterGroup or Group as first argument')

    if args is None: args = ()
    if kws is None: kws = {}

    def _residual(params):
        params2group(params, paramgroup)
        return fcn(paramgroup, *args,  **kws)

    fitter = Minimizer(_residual, params, iter_cb=iter_cb,
                       reduce_fcn=reduce_fcn, nan_policy='omit', **fit_kws)

    result = fitter.minimize(method=method)
    params2group(result.params, paramgroup)

    out = Group(name='minimize results', fitter=fitter, fit_details=result,
                chi_square=result.chisqr, chi_reduced=result.redchi)


    for attr in ('aic', 'bic', 'covar', 'rfactor', 'params', 'nvarys',
                 'nfree', 'ndata', 'var_names', 'nfev', 'success',
                 'errorbars', 'message', 'lmdif_message', 'residual'):
        setattr(out, attr, getattr(result, attr, None))
    return out

def fit_report(fit_result, modelpars=None, show_correl=True, min_correl=0.1,
               sort_pars=False, _larch=None, **kws):
    """generate a report of fitting results
    wrapper around lmfit.fit_report

    The report contains the best-fit values for the parameters and their
    uncertainties and correlations.

    Parameters
    ----------
    fit_result : result from fit
       Input Parameters from fit or MinimizerResult returned from a fit.
    modelpars : Parameters, optional
       Known Model Parameters.
    show_correl : bool, optional
       Whether to show list of sorted correlations (default is True).
    min_correl : float, optional
       Smallest correlation in absolute value to show (default is 0.1).
    sort_pars : bool or callable, optional
       Whether to show parameter names sorted in alphanumerical order. If
       False (default), then the parameters will be listed in the order they
       were added to the Parameters dictionary. If callable, then this (one
       argument) function is used to extract a comparison key from each
       list element.

    Returns
    -------
    string
       Multi-line text of fit report.


    """
    params = getattr(fit_result, 'fit_details', input)
    return lmfit.fit_report(params, modelpars=modelpars, show_correl=show_correl,
                            min_correl=min_correl, sort_pars=sort_pars)


def confidence_intervals(fit_result, sigmas=(1, 2, 3), _larch=None,  **kws):
    """calculate the confidence intervals from a fit
    for supplied sigma values

    wrapper around lmfit.conf_interval
    """
    fitter = getattr(fit_result, 'fitter', None)
    result = getattr(fit_result, 'fit_details', None)
    return conf_interval(fitter, result, sigmas=sigmas, **kws)

def chi2_map(fit_result, xname, yname, nx=11, ny=11, _larch=None, **kws):
    """generate a confidence map for any two parameters for a fit

    Arguments
    ==========
       minout   output of minimize() fit (must be run first)
       xname    name of variable parameter for x-axis
       yname    name of variable parameter for y-axis
       nx       number of steps in x [11]
       ny       number of steps in y [11]

    Returns
    =======
        xpts, ypts, map
    """
    fitter = getattr(fit_result, 'fitter', None)
    result = getattr(fit_result, 'fit_details', None)
    return conf_interval2d(fitter, result, xname, yname,
                           nx=nx, ny=ny, **kws)
