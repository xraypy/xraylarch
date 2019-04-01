#!/usr/bin/env python
"""
linear combination fitting
"""
import os
import sys
import time
import json
import copy

from itertools import combinations
from collections import OrderedDict
from glob import glob

import numpy as np
from numpy.random import randint

import lmfit

from .. import Group
from .utils import interp, index_of

def get_arrays(group, arrayname, xname='energy'):
    y = None
    if arrayname == 'chik':
        x = getattr(group, 'k', None)
        y = getattr(group, 'chi', None)
    else:
        x = getattr(group, xname, None)
        y = getattr(group, arrayname, None)
    return x, y

def get_label(group):
    label = None
    for attr in ('filename', 'label', 'groupname', '__name__'):
        _lab = getattr(group, attr, None)
        if _lab is not None:
            label = _lab
            break
    if label is None:
        label = hex(id(group))
    return label


def groups2matrix(groups, yname='norm', xname='energy', xmin=-np.inf, xmax=np.inf,
                  interp_kind='cubic'):
    """extract an array from a list of groups and construct a uniform 2d matrix
    ready for linear analysis

    Argumments
    ----------
    groups       list of groups, assumed to have similar naming conventions
    yname        name of y-arrays to convert to matrix ['norm']
    xname        name of x-array to use ['energy']
    xmin         min x value [-inf]
    xmax         max x value [+inf]
    interp_kind  kind argument for interpolation ['cubic']

    Returns
    -------
    xdat, ydat  where xdat has shape (nx,) and ydat has shape (nx, ngroups)
    """
    # get arrays from first group
    xdat, ydat = get_arrays(groups[0], yname, xname=xname)
    if xdat is None or ydat is None:
        raise ValueError("cannot get arrays for arrayname='%s'" % yname)

    imin, imax = None, None
    if xmin is not None:
        imin = index_of(xdat, xmin)
    if xmax is not None:
        imax = index_of(xdat, xmax) + 1

    xsel = slice(imin, imax)
    xdat = xdat[xsel]
    ydat = ydat[xsel]

    ydat = [ydat]
    for g in groups[1:]:
        x, y = get_arrays(g, yname, xname=xname)
        ydat.append(interp(x, y, xdat, kind=interp_kind))
    return xdat, np.array(ydat)


def lincombo_fit(group, components, weights=None, minvals=None,
                 maxvals=None, arrayname='norm', xmin=-np.inf, xmax=np.inf,
                 sum_to_one=True):

    """perform linear combination fitting for a group

    Arguments
    ---------
      group       Group to be fitted
      components  List of groups to use as components (see Note 1)
      weights     array of starting  weights (see Note 2)
      minvals     array of min weights (or None to mean -inf)
      maxvals     array of max weights (or None to mean +inf)
      arrayname   string of array name to be fit (see Note 3) ['norm']
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]
      sum_to_one  bool, whether to force weights to sum to 1.0 [True]

    Returns
    -------
      group with resulting weights and fit statistics

    Notes
    -----
     1.  The names of Group members for the components must match those of the
         group to be fitted.
     2.  use `None` to use basic linear algebra solution.
     3.  arrayname is expected to be one of `norm`, `mu`, `dmude`, or `chi`.
         It can be some other name but such named arrays should exist for all
         components and groups.
    """

    # first, gather components
    ncomps = len(components)
    allgroups = [group]
    allgroups.extend(components)
    xdat, yall = groups2matrix(allgroups, yname=arrayname,
                               xname='energy', xmin=xmin, xmax=xmax)
    ydat   = yall[0, :]
    ycomps = yall[1:, :].transpose()

    # second use unconstrained linear algebra to estimate weights
    ls_out = np.linalg.lstsq(ycomps, ydat, rcond=-1)
    ls_vals = ls_out[0]
    # third use lmfit, imposing bounds and sum_to_one constraint
    if weights in (None, [None]*ncomps):
        weights = ls_vals
    if minvals in (None, [None]*ncomps):
        minvals = -np.inf * np.ones(ncomps)
    if maxvals in (None, [None]*ncomps):
        maxvals = np.inf * np.ones(ncomps)

    def lincombo_resid(params, data, ycomps):
        npts, ncomps = ycomps.shape
        sum = np.zeros(npts)
        for i in range(ncomps):
            sum += ycomps[:, i] * params['c%i' % i].value
        return sum-data

    params = lmfit.Parameters()
    for i in range(ncomps):
        params.add('c%i' % i, value=weights[i], min=minvals[i], max=maxvals[i])

    if sum_to_one:
        expr = ['1'] + ['c%i' % i for i in range(ncomps-1)]
        params['c%i' % (ncomps-1)].expr = '-'.join(expr)

    expr = ['c%i' % i for i in range(ncomps)]
    params.add('total', expr='+'.join(expr))

    result = lmfit.minimize(lincombo_resid, params, args=(ydat, ycomps))

    # gather results
    weights, weights_lstsq = OrderedDict(), OrderedDict()
    params, fcomps = OrderedDict(), OrderedDict()
    for i in range(ncomps):
        label = get_label(components[i])
        weights[label] = result.params['c%i' % i].value
        params[label] = copy.deepcopy(result.params['c%i' % i])
        weights_lstsq[label] = ls_vals[i]
        fcomps[label] = ycomps[:, i] * result.params['c%i' % i].value


    if 'total' in result.params:
        params['total'] = copy.deepcopy(result.params['total'])

    yfit = ydat + lincombo_resid(result.params, ydat, ycomps)
    return Group(result=result, chisqr=result.chisqr, redchi=result.redchi,
                 params=params, weights=weights, weights_lstsq=weights_lstsq,
                 xdata=xdat, ydata=ydat, yfit=yfit, ycomps=fcomps)

def lincombo_fitall(group, components, weights=None, minvals=None, maxvals=None,
                     arrayname='norm', xmin=-np.inf, xmax=np.inf,
                    sum_to_one=True):
    """perform linear combination fittings for a group with all combinations
    of 2 or more of the components given

    Arguments
    ---------
      group       Group to be fitted
      components  List of groups to use as components (see Note 1)
      weights     array of starting  weights (or None to use basic linear alg solution)
      minvals     array of min weights (or None to mean -inf)
      maxvals     array of max weights (or None to mean +inf)
      arrayname   string of array name to be fit (see Note 2)
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]
      sum_to_one  bool, whether to force weights to sum to 1.0 [True]

    Returns
    -------
     list of groups with resulting weights and fit statistics,
     ordered by reduced chi-square (best first)

    Notes
    -----
     1.  The names of Group members for the components must match those of the
         group to be fitted.
     2.  arrayname can be one of `norm` or `dmude`
    """

    ncomps = len(components)

    # here we save the inputs weights and bounds for each component by name
    # so they can be imposed for the individual fits
    _save = {}
    if weights in (None, [None]*ncomps):
        weights = [None]*ncomps
    if minvals in (None, [None]*ncomps):
        minvals = -np.inf * np.ones(ncomps)
    if maxvals in (None, [None]*ncomps):
        maxvals = np.inf * np.ones(ncomps)

    for i in range(ncomps):
        _save[get_label(components[i])] = (weights[i], minvals[i], maxvals[i])

    all = []
    for nx in range(ncomps, 1, -1):
        for comps in combinations(components, nx):
            labs = [get_label(c) for c in comps]
            _wts = [1.0/nx for lab in labs]
            _min = [_save[lab][1] for lab in labs]
            _max = [_save[lab][2] for lab in labs]

            o = lincombo_fit(group, comps, weights=_wts, arrayname=arrayname,
                             minvals=_min, maxvals=_max, xmin=xmin, xmax=xmax,
                             sum_to_one=sum_to_one)
            all.append(o)
    # sort outputs by reduced chi-square
    return sorted(all, key=lambda x: x.redchi)
