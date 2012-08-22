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

def restore_vals(params, saveparams):
    '''restores values and stderrs from params saved in saveparams'''
    for par, spar in zip(params, saveparams):
        par.value, par.stderr = spar.value, spar.stderr
        

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
    names = conf_vals.keys()
    nvals = len(conf_vals[names[0]])
    maxlen = max([len(i) for i in names])
    if maxlen < 10: maxlen  = 10
    
    sig = [' % 7i ' % i[0] for i in conf_vals[names[0]]]
    prob= [' %7.3f ' % (100*erf(i[0]/np.sqrt(2))) for i in conf_vals[names[0]]]

    out.append('# Sigmas:      %s' % ('  '.join(sig)))
    out.append('# Percentiles:   %s' % ('  '.join(prob)))
    out.append('#'  + '='*90)
    for nam in names:
        line = [' ', (nam + ' '*maxlen)[:maxlen+1]]
        line.extend(['%9.5g' % i[1] for i in conf_vals[nam]])
        out.append('  '.join(line))
    return '\n'.join(out)

def conf_intervals(minimizer, sigmas=(1, 2, 3), maxiter=200,
                  verbose=False, prob_func=None, **kws):
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
    if prob_func is None or not hasattr(prob_func, '__call__'):
        prob_func = f_compare

    pgroup_save = copy.deepcopy(minimizer.paramgroup)
    
    # calculate fractions from sigma-levels, make sure the
    # list is sorted
    sigmas = list(sigmas)
    sigmas.sort()
    probs = [erf(s/np.sqrt(2)) for s in sigmas]

    # copy the best fit values.
    params, params_save = [], []
    for i in minimizer.var_names:
        par = getattr(minimizer.paramgroup, i)
        if isParameter(par):
            params.append(par)
            params_save.append(copy.deepcopy(par))
        
    best_chi = minimizer.paramgroup.chi_square

    output, trace_dict = {}, {}
    p_trace = ([], [])

    ndata  = len(minimizer.paramgroup.residual)
    
    def calc_prob(val, offset, par, p_trace):
        '''Returns the probability for given Value.'''
        par.value = val
        minimizer.prepare_fit(force=True)
        minimizer.leastsq()
        chi2   = minimizer.paramgroup.chi_square
        nvarys = minimizer.paramgroup.nvarys
        prob = prob_func(ndata, nvarys, chi2, best_chi)

        p_trace[0].append([i.value for i in params])
        p_trace[1].append(prob)
        return prob - offset
    
    def search_limits(par, direction, p_trace):
        """
        Searchs for the limits. First it looks for a upper limit and
        then finds the sigma-limits with help of scipy root finder.
        """

        change = 1
        old_prob = 0
        i = 0
        limit = start_val

        # Find a upper limit,
        while change > 0.001 and old_prob < max(probs):
            i += 1
            limit += step * direction
            new_prob = calc_prob(limit, 0, par, p_trace)
            change = new_prob - old_prob
            old_prob = new_prob
            if i > maxiter:
                break

        ret=[]
        val_limit = start_val

        for sig, p in zip(sigmas, probs):
            if p < old_prob:
                try:
                    val = brentq(calc_prob, val_limit, limit,
                                 args=(p, par, p_trace), xtol=0.001)
                except ValueError:
                    val = brentq(calc_prob, start_val, limit,
                                 args=(p, par, p_trace), xtol=0.001)
                               #we don't know which side of zero we are                    
                val_limit=val-0.001*direction                    
                ret.append((direction*sig, val))
            else: 
                ret.append((direction*sig, np.nan))

        restore_vals(params, params_save)
        return ret

    for par in params:
        p_trace = ([], [])
        # print('== Calculating confidence interval for %s' % par.name)

        restore_vals(params, params_save)

        if par.stderr > 0:
            step = par.stderr
        else:
            step = max(par.value * 0.05, 0.01)

        par.vary = False

        start_val = par.value
        upper = search_limits(par, 1, p_trace)
        out = upper[::-1] + [(0, start_val)]
        out.extend(search_limits(par, -1, p_trace))
        
        trace_dict[par.name] = p_trace_to_dict(p_trace, params)
        output[par.name]= out
        par.vary = True
        
    restore_vals(params, params_save)
    minimizer.paramgroup = pgroup_save
    return output, trace_dict

def chisquare_map(minimizer, xname, yname, nx=16, ny=16, xrange=None,
             yrange=None, prob_func=None, **kws):
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

    best_chi = minimizer.paramgroup.chi_square
    pgroup_save = copy.deepcopy(minimizer.paramgroup)

    if prob_func is None or not hasattr(prob_func, '__call__'):
        prob_func = f_compare


    x = getattr(minimizer.paramgroup, xname)
    y = getattr(minimizer.paramgroup, yname)

    x_upper, x_lower = (x.value + 5*x.stderr, x.value - 5*x.stderr)
    y_upper, y_lower = (y.value + 5*y.stderr, y.value - 5*y.stderr)

    if xrange is not None:
        x_lower, x_upper = xrange
    if yrange is not None:
        y_lower, y_upper = yrange

    x_points = np.linspace(x_lower, x_upper, nx)
    y_points = np.linspace(y_lower, y_upper, ny)
    grid = np.dstack(np.meshgrid(x_points, y_points))

    x.vary, y.vary = False, False
    
    # copy the best fit values.
    params, params_save = [], []
    for i in minimizer.var_names:
        par = getattr(minimizer.paramgroup, i)
        if isParameter(par):
            params.append(par)
            params_save.append(copy.deepcopy(par))

    ndata  = len(minimizer.paramgroup.residual)

    # def calc_prob(vals):
    def calc_chi2(vals):
        x.value = vals[0]
        y.value = vals[1]

        minimizer.prepare_fit(force=True)
        minimizer.leastsq()
        return minimizer.paramgroup.chi_square
        # chi2   = minimizer.paramgroup.chi_square
        # nvarys = minimizer.paramgroup.nvarys
        # return prob_func(ndata, nvarys, chi2, best_chi, nfix=2.0)

    out = np.apply_along_axis(calc_chi2, -1, grid)

    x.vary, y.vary = True, True
    restore_vals(params, params_save)
    minimizer.paramgroup = pgroup_save

    return x_points, y_points, out

    
