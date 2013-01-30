#!/usr/bin/env python
"""
  XAFS pre-edge subtraction, normalization algorithms
"""

import sys
import numpy as np
from scipy import polyfit

from larch.larchlib import plugin_path

# put the 'std' and 'xafs' (this!) plugin directories into sys.path
sys.path.insert(0, plugin_path('std'))

# now we can reliably import other std and xafs modules...
from mathutils import index_nearest, remove_dups

MODNAME = '_xafs'

def find_e0(energy, mu, group=None, _larch=None):
    """calculate E0 given mu(energy)

    This finds the point with maximum derivative with some
    checks to avoid spurious glitches.

    Arguments
    ----------
    energy:  array of x-ray energies, in eV
    mu:      array of mu(E)
    group:   output group

    Returns
    -------
    step, e0:    edge step, edge energy (in eV)

    If a group is supplied, group.e0 will also be set to this value.
    """
    if _larch is None:
        raise Warning("cannot find e0 -- larch broken?")

    energy = remove_dups(energy)
    dmu = np.diff(mu)/np.diff(energy)
    # find points of high derivative
    high_deriv_pts = np.where(dmu >  max(dmu)*0.05)[0]
    idmu_max, dmu_max = 0, 0
    for i in high_deriv_pts:
        if (dmu[i] > dmu_max and
            (i+1 in high_deriv_pts) and
            (i-1 in high_deriv_pts)):
            idmu_max, dmu_max = i, dmu[i]
    if _larch.symtable.isgroup(group):
        group.e0 = energy[idmu_max+1]
    return energy[idmu_max+1]

def pre_edge(energy, mu, group=None, e0=None, step=None,
             nnorm=3, nvict=0, pre1=None, pre2=-50,
             norm1=100, norm2=None, _larch=None, **kws):
    """pre edge subtraction, normalization for XAFS

    This performs a number of steps:
       1. determine E0 (if not supplied) from max of deriv(mu)
       2. fit a line of polymonial to the region below the edge
       3. fit a polymonial to the region above the edge
       4. extrapolae the two curves to E0 to determine the edge jump

    Arguments
    ----------
    energy:  array of x-ray energies, in eV
    mu:      array of mu(E)
    group:   output group
    e0:      edge energy, in eV.  If None, it will be determined here.
    step:    edge jump.  If None, it will be determined here.
    pre1:    low E range (relative to E0) for pre-edge fit
    pre2:    high E range (relative to E0) for pre-edge fit
    nvict:   energy exponent to use for pre-edg fit.  See Note
    norm1:   low E range (relative to E0) for post-edge fit
    norm2:   high E range (relative to E0) for post-edge fit
    nnorm:   number of terms in polynomial (that is, 1+degree) for
             post-edge, normalization curve. Default=3 (quadratic)

    Returns
    -------
    returns  (edge_step, e0)

    if group is not None, the following attributes of that group are set:
        e0          energy origin
        edge_step   edge step
        norm        normalized mu(E)
        pre_edge    determined pre-edge curve
        post_edge   determined post-edge, normalization curve


    Notes
    -----
       nvict gives an exponent to the energy term for the pre-edge fit.
       That is, a line (m * energy + b) is fit to mu(energy)*energy**nvict
       over the pr-edge regin, energy=[e0+pre1, e0+pre2].
    """

    if _larch is None:
        raise Warning("cannot remove pre_edge -- larch broken?")
    if e0 is None or e0 < energy[0] or e0 > energy[-1]:
        e0 = find_e0(energy, mu, group=group, _larch=_larch)

    energy = remove_dups(energy)

    p1 = min(np.where(energy >= e0-10.0)[0])
    p2 = max(np.where(energy <= e0+10.0)[0])
    ie0 = np.where(energy-e0 == min(abs(energy[p1:p2] - e0)))[0][0]

    if pre1 is None:  pre1  = min(energy) - e0
    if norm2 is None: norm2 = max(energy) - e0

    p1 = min(np.where(energy >= pre1+e0)[0])
    p2 = max(np.where(energy <= pre2+e0)[0])
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    omu  = mu*energy**nvict
    pcoefs = polyfit(energy[p1:p2], omu[p1:p2], 1)
    pre_edge = (pcoefs[0] * energy + pcoefs[1]) * energy**(-nvict)
    # normalization
    p1 = min(np.where(energy >= norm1+e0)[0])
    p2 = max(np.where(energy <= norm2+e0)[0])
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)
    coefs = polyfit(energy[p1:p2], omu[p1:p2], nnorm)
    post_edge = 0
    for n, c in enumerate(reversed(list(coefs))):
        post_edge += c * energy**(n-nvict)
    edge_step = post_edge[ie0] - pre_edge[ie0]
    norm  = (mu - pre_edge)/edge_step
    if _larch.symtable.isgroup(group):
        group.e0 = e0
        group.norm = norm
        group.edge_step  = edge_step
        group.pre_edge   = pre_edge
        group.post_edge  = post_edge
        group.pre_slope  = pcoefs[0]
        group.pre_offest = pcoefs[1]
        group.norm_coefs = reversed(list(coefs))
    return edge_step, e0

def registerLarchPlugin():
    return (MODNAME, {'find_e0': find_e0,
                      'pre_edge': pre_edge})
