#!/usr/bin/env python
"""
  XAFS pre-edge subtraction, normalization algorithms
"""

import numpy as np
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
    if group is not None and larch.symtable.isgroup(group):
        setattr(group, 'e0', energy[idmu_max+1])
    return energy[idmu_max+1]

def pre_edge(energy, mu, group=None, larch=None, e0=None,
             step=None, nnorm=2, form='linear',
             pre1=-200, pre2=-50, enorm1=100, enorm2=400):

    if larch is None:
        raise Warning("cannot remove pre_edge -- larch broken?")

    print 'preedge! ', group
    print nnorm, step, e0
    if e0 is None or e0 < energy[0] or e0 > energy[-1]:
        e0 = find_e0(energy, mu, group=group, larch=larch)

    print 'preedge e0 ', e0
    pre1 = pre1 + e0
    pre2 = pre2 + e0

    if form == 'linear':
        print 'get linear regression'

def registerLarchPlugin():
    return (MODNAME, {'find_e0': find_e0,
                      'pre_edge': pre_edge})


