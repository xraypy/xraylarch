#!/usr/bin/env python
"""
merge groups, interpolating if necessary
"""
import os
import numpy as np
from larch import Group
from larch.math import interp, index_of, remove_dups

def merge_groups(grouplist, master=None, xarray='energy', yarray='mu',
                 kind='cubic', trim=True, calc_yerr=True):
    """merge arrays from a list of groups.

    Arguments
    ---------
     grouplist   list of groups to merge
     master      group to use for common x arrary [None -> 1st group]
     xarray      name of x-array for merge ['energy']
     yarray      name of y-array for merge ['mu']
     kind        interpolation kind ['cubic']
     trim        whether to trim to the shortest energy range [True]
     calc_yerr   whether to use the variance in the input as yerr [True]

    Returns
    --------
     group with x-array and y-array containing merged data.

    """
    if master is None:
        master = grouplist[0]

    xout = remove_dups(getattr(master, xarray))
    xmins = [min(xout)]
    xmaxs = [max(xout)]
    yvals = []

    for g in grouplist:
        x = getattr(g, xarray)
        y = getattr(g, yarray)
        yvals.append(interp(x, y, xout, kind=kind))
        xmins.append(min(x))
        xmaxs.append(max(x))

    yvals = np.array(yvals)
    yave = yvals.mean(axis=0)
    ystd = yvals.std(axis=0)

    if trim:
        xmin = min(xmins)
        xmax = min(xmaxs)
        ixmin = index_of(xout, xmin)
        ixmax = index_of(xout, xmax)
        xout = xout[ixmin:ixmax]
        yave = yave[ixmin:ixmax]
        ystd = ystd[ixmin:ixmax]

    grp = Group()
    setattr(grp, xarray, xout)
    setattr(grp, yarray, yave)
    setattr(grp, yarray + '_std', ystd)

    if kind == 'cubic':
        y0 = getattr(master, yarray)
        # if the derivative gets much worse, use linear interpolation
        if max(np.diff(yave)) > 50*max(np.diff(y0)):
            grp = merge_groups(grouplist, master=master, xarray=xarray,
                               yarray=yarray, trim=trim,
                               calc_yerr=calc_yerr, kind='linear')
    return grp
