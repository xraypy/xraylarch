#!/usr/bin/python
# functions to calculate extended condifence intervals
# adapted from lmfit.confidence, originally authored
# by Till Stensitzki from Freie Universitat Berlin,
# adopted by M Newville for xraylarch
"""
Contains functions to calculate confidence intervals.
"""

import copy
import numpy as np
from scipy.stats import f
from scipy.optimize import brentq
from scipy.special import erf

from .parameter import isParameter

def f_compare(ndata, nparams, new_chi, best_chi, nfix=1):
    """
    Returns the probalitiy for two given parameter sets.
    nfix is the number of fixed parameters.
    """
    nparams = nparams + nfix
    nfree = 1.0*(ndata - nparams)
    return f.cdf((new_chi / best_chi - 1) * nfree/nfix, nfix, nfree)

def restore_vals(paramgroup, saved_vals):
    '''restores values and stderrs from params saved in saved_vals'''
    for name, val, stderr in saved_vals:
        par = getattr(paramgroup, name)
        par.value, par.stderr = val, stderr

def p_trace_to_dict(p_tr, params):
    """
    p_tr has following form:

        ([[p1, p2,...],[p1, p2,...]],[res_prob1,res_prob2..])

    Returns a dict with p-names and prob as keys and lists as their values.
    """
    out = {'prob': np.array(p_tr[1])}
    for par in params:
        out[par.name] = np.array([l.pop(0) for l in p_tr[0]])
    return out


def conf_report(conf_vals):
    out = ['# Confidence Interval Report']
    names = list(conf_vals.keys())
    nvals = len(conf_vals[names[0]])
    maxlen = max([len(i) for i in names])
    if maxlen < 10: maxlen  = 10

    sig = [' % 7i ' % i[0] for i in conf_vals[names[0]]]
    prob= [' %7.3f ' % (100*erf(i[0]/np.sqrt(2))) for i in conf_vals[names[0]]]
    nbest = int(nvals/2.0)
    out.append('# Sigmas:    %s' % ('  '.join(sig)))
    out.append('# Percentiles: %s' % ('  '.join(prob)))
    out.append('#'  + '='*90)
    for nam in names:
        t1 = (' ' + nam + ' '*maxlen)[:maxlen+2]
        t2 = ('    -best ' + ' '*len(t1))[:len(t1)]
        line = [t1]
        line.extend(['%9.5g' % i[1] for i in conf_vals[nam]])
        out.append('  '.join(line))
        best = conf_vals[nam][nbest][1]
        line = [t2]
        line.extend(['%9.5g' % (i[1]-best) for i in conf_vals[nam]])
        out.append('  '.join(line))
    return '\n'.join(out)

def conf_intervals(minimizer, sigmas=(1, 2, 3), maxiter=200,
                  verbose=False, prob_func=None, with_trace=False, **kws):
    r"""Calculates the confidence interval for parameters
    from the given minimizer.

    The parameter for which the ci is calculated will be varied, while
    the remaining parameters are reoptimized for minimizing chi-square.
    The resulting chi-square is used  to calculate the probability with
    a given statistic e.g. F-statistic. This function uses a 1d-rootfinder
    from scipy to find the values resulting in the searched confidence
    region.

    Parameters
    ----------
    minimizer : Minimizer
        The minimizer to use, should be already fitted via leastsq.

    sigmas : list, optional
          The sigmas to find. Default is 1, 2 and 3.
    maxiter : int
        Maximum of iteration to find an upper limit.
    prob_func : ``None`` or callable
        Function to calculate the probality from the opimized chi-square.
        Default (``None``) uses built-in f_compare (F test).


    Returns
    -------
    output : dict
        A dict, which contains a list of (sigma, vals)-tuples for each name.
    trace_dict : dict
        A dict, the key is the parameter which was fixed. The values are again
        a dict with the names as keys, but with an additional key 'prob'.
        Each contains an array of the corresponding values.

    See also
    --------
    conf_interval2d


    Examples
    --------

    >>> from lmfit.printfuncs import *
    >>> mini=minimize(some_func, params)
    >>> mini.leastsq()
    True
    >>> report_errors(params)
    ... #report
    >>> ci=conf_interval(mini)
    >>> report_ci(ci)
    ... #report

    Now with quantils for the sigmas and using the trace.

    >>> ci, trace=conf_interval(mini, sigmas=(1, 2, 3, 4), trace=True)
    >>> fixed=trace['para1']['para1']
    >>> free=trace['para1']['not_para1']
    >>> prob=trace['para1']['prob']

    This makes it possible to plot the dependence between free and fixed.
    """
    paramgroup = minimizer.paramgroup
    if prob_func is None or not hasattr(prob_func, '__call__'):
        prob_func = f_compare

    # calculate fractions from sigma-levels, make sure the
    # list is sorted
    sigmas = list(sigmas)
    sigmas.sort()
    probs = [erf(s/np.sqrt(2)) for s in sigmas]

    # copy the best fit values.
    params, params_savevals = [], []
    for name in minimizer.var_names:
        par = getattr(paramgroup, name)
        if isParameter(par):
            params.append(par)
            params_savevals.append((name, par.value, par.stderr))

    best_chi = paramgroup.chi_square

    output, trace_dict = {}, {}
    p_trace = ([], [])

    ndata  = len(paramgroup.residual)

    def calc_prob(val, offset, par, p_trace):
        '''Returns the probability for given Value.'''
        par.value = val
        minimizer.prepare_fit(force=True)
        minimizer.leastsq()
        chi2   = paramgroup.chi_square
        nvarys = paramgroup.nvarys
        prob = prob_func(ndata, nvarys, chi2, best_chi)

        p_trace[0].append([i.value for i in params])
        p_trace[1].append(prob)
        return prob - offset

    def search_limits(par, direction, p_trace):
        """
        Searchs for the limits. First it looks for a upper limit and
        then finds the sigma-limits with help of scipy root finder.
        """
        change, i, old_prob = 1, 0, 0
        limit = start_val
        # Find a upper limit
        while change > 1.e-4 and old_prob <= max(probs):
            i += 1
            limit += step * direction
            new_prob = calc_prob(limit, 0, par, p_trace)
            change = new_prob - old_prob
            old_prob = new_prob
            if i > maxiter:
                break
        ret = []
        val_limit = start_val
        for sig, p in zip(sigmas, probs):
            if p < old_prob:
                try:

                    val = brentq(calc_prob, val_limit, limit,
                                 args=(p, par, p_trace), xtol=0.001)
                    # print ' lim at ', val, sig, p
                except ValueError:
                    val = np.nan
                val_limit =val - 0.001*direction
                ret.append((direction*sig, val))
            else:
                # print ' lim nan', sig, p, old_prob
                ret.append((direction*sig, np.nan))

        restore_vals(paramgroup, params_savevals)
        return ret

    for par in params:
        p_trace = ([], [])
        # print('== Calculating confidence interval for %s' % par.name)

        restore_vals(paramgroup, params_savevals)

        if par.stderr > 0:
            step = par.stderr
        else:
            step = max(par.value * 0.05, 0.01)

        par.vary = False

        start_val = par.value
        lower = search_limits(par, -1, p_trace)
        upper = search_limits(par, 1, p_trace)
        out = lower[::-1] + [(0, start_val)] + upper

        if with_trace:
            trace_dict[par.name] = p_trace_to_dict(p_trace, params)
        output[par.name]= out
        par.vary = True

    restore_vals(paramgroup, params_savevals)
    if with_trace:
        return output, trace_dict
    else:
        return output

def chisquare_map(minimizer, xname, yname, nx=11, ny=11, xrange=None,
             yrange=None, sigmas=5, prob_func=None, **kws):
    r"""Calculates chi-square map for two fixed parameters.

    The method is explained roughly as in *conf_interval*:
    here we are fixing  two parameters.

    Parameters
    ----------
    minimizer : minimizer
        The minimizer to use, should be already fitted via leastsq.
    x_name : string
        The name of the parameter which will be the x direction.
    y_name : string
        The name of the parameter which will be the y direction.
    nx, ny : ints, optional
        Number of points.
    xrange, yrange: tuples optional
        Should have the form (x_lower, x_upper) and (y_lower, y_upper), respectively.
        Default is 5 stderrs in each direction.

    Returns
    -------
    x : (nx)-array
        x-coordinates
    y : (ny)-array
        y-coordinates
    grid : (nx,ny)-array
        grid contains the calculated probabilities.

    Examples
    --------

    >>> from lmfit.printfuncs import *
    >>> mini=minimize(some_func, params)
    >>> mini.leastsq()
    True
    >>> x,y,gr=conf_interval2d('para1','para2')
    >>> plt.contour(x,y,gr)

    Other Parameters
    ----------------
    prob_func : ``None`` or callable
        Function to calculate the probality from the opimized chi-square.
        Default (``None``) uses built-in f_compare (F test).
    """
    paramgroup = minimizer.paramgroup
    best_chi = paramgroup.chi_square

    if prob_func is None or not hasattr(prob_func, '__call__'):
        prob_func = f_compare

    x = getattr(paramgroup, xname)
    y = getattr(paramgroup, yname)
    if sigmas is None:
        sigmas = 5

    x_upper, x_lower = (x.value + sigmas*x.stderr, x.value - sigmas*x.stderr)
    y_upper, y_lower = (y.value + sigmas*y.stderr, y.value - sigmas*y.stderr)

    if xrange is not None: x_lower, x_upper = xrange
    if yrange is not None: y_lower, y_upper = yrange

    x_points = np.linspace(x_lower, x_upper, nx)
    y_points = np.linspace(y_lower, y_upper, ny)
    grid = np.dstack(np.meshgrid(x_points, y_points))

    x.vary, y.vary = False, False

    # copy the best fit values.
    params_savevals = []
    for name in minimizer.var_names:
        par = getattr(paramgroup, name)
        if isParameter(par):
            params_savevals.append((name, par.value, par.stderr))

    def calc_chi2(vals):
        x.value = vals[0]
        y.value = vals[1]
        minimizer.leastsq()
        return paramgroup.chi_square

    out = np.apply_along_axis(calc_chi2, -1, grid)
    x.vary, y.vary = True, True
    restore_vals(paramgroup, params_savevals)
    minimizer.leastsq()

    return x_points, y_points, out
