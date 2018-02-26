#!/usr/bin/env python
"""
merge groups, interpolating if necessary
"""
import os
import numpy as np
from larch import Group, ValidateLarchPlugin
from larch.utils.mathutils import interp, index_of

@ValidateLarchPlugin
def merge_groups(grouplist, master=None, xarray='energy', yarray='mu',
                 kind='cubic', trim=True, _larch=None):
    """merge arrays from a list of groups.

    Arguments
    ---------
     grouplist   list of groups to merge
     master      group to use for common x arrary [None -> 1st group]
     xarray      name of x-array for merge ['energy']
     yarray      name of y-array for merge ['mu']
     kind        interpolation kind ['cubic']
     trim        whether to trim to the shortest energy range [True]

    Returns
    --------
     group with x-array and y-array containing merged data.

    """
    if master is None:
        master = grouplist[0]

    x0 = getattr(master, xarray)
    y0 = np.zeros(len(x0))
    xmins = [min(x0)]
    xmaxs = [max(x0)]

    for g in grouplist:
        x = getattr(g, xarray)
        y = getattr(g, yarray)
        y0 += interp(x, y, x0, kind=kind)
        xmins.append(min(x))
        xmaxs.append(max(x))

    y0 = y0/len(grouplist)

    if trim:
        xmin = min(xmins)
        xmax = min(xmaxs)
        ixmin = index_of(x0, xmin)
        ixmax = index_of(x0, xmax)
        x0 = x0[ixmin:ixmax]
        y0 = y0[ixmin:ixmax]

    grp = Group()
    setattr(grp, xarray, x0)
    setattr(grp, yarray, y0)

    return grp

def registerLarchPlugin():
    return ('_io', {'merge_groups': merge_groups})
