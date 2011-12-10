#!/usr/bin/env python
"""
  XAFS pre-edge subtraction, normalization algorithms
"""

import numpy as np
from scipy import polyfit
MODNAME = '_xafs'

def find_e0(energy, mu, group=None, larch=None):
    """calculate e0 given mu(energy)
    """
    if larch is None:
        raise Warning("cannot find e0 -- larch broken?")

    dmu = np.diff(mu)
    # find points of high derivative
    high_deriv_pts = np.where(dmu >  max(dmu)*0.05)[0]
    idmu_max, dmu_max = 0, 0
    for i in high_deriv_pts:
        if (dmu[i] > dmu_max and
            (i+1 in high_deriv_pts) and
            (i-1 in high_deriv_pts)):
            idmu_max, dmu_max = i, dmu[i]
    if larch.symtable.isgroup(group):
        setattr(group, 'e0', energy[idmu_max+1])
    return energy[idmu_max+1]

def pre_edge(energy, mu, group=None, larch=None, e0=None,
             step=None, nnorm=3, form='linear',
             pre1=-200, pre2=-50, norm1=100, norm2=400):

    if larch is None:
        raise Warning("cannot remove pre_edge -- larch broken?")

    if e0 is None or e0 < energy[0] or e0 > energy[-1]:
        e0 = find_e0(energy, mu, group=group, larch=larch)

    p1 = min(np.where(energy >= e0-10.0)[0])
    p2 = max(np.where(energy <= e0+10.0)[0])
    ie0 = np.where(energy-e0 == min(abs(energy[p1:p2] - e0)))[0][0]

    p1 = min(np.where(energy >= pre1+e0)[0])
    p2 = max(np.where(energy <= pre2+e0)[0])
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    if form == 'linear':
        coefs = polyfit(energy[p1:p2], mu[p1:p2], 1)
        pre_edge = coefs[0] * energy + coefs[1]

    # normalization
    p1 = min(np.where(energy >= norm1+e0)[0])
    p2 = max(np.where(energy <= norm2+e0)[0])
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    coefs = polyfit(energy[p1:p2], mu[p1:p2], nnorm)
    post_edge = 0
    for n, c in enumerate(reversed(list(coefs))):
        post_edge += c * energy**n

    edge_step = post_edge[ie0] - pre_edge[ie0]
    norm  = (mu - pre_edge)/edge_step

    if larch.symtable.isgroup(group):
        setattr(group, 'e0', e0)
        setattr(group, 'pre_edge', pre_edge)
        setattr(group, 'post_edge', post_edge)
        setattr(group, 'edge_step', edge_step)
        setattr(group, 'norm', norm)

    return edge_step, e0

def registerLarchPlugin():
    return (MODNAME, {'find_e0': find_e0,
                      'pre_edge': pre_edge})
