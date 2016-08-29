#!/usr/bin/env python
"""
  XAFS pre-edge subtraction, normalization algorithms
"""

import numpy as np
from scipy import polyfit
from larch import (Group, Parameter, ValidateLarchPlugin,
                   Make_CallArgs, Minimizer, isgroup,
                   parse_group_args)

# now we can reliably import other std and xafs modules...

from larch_plugins.math import (index_of, index_nearest,
                                remove_dups, remove_nans2)
from larch_plugins.xafs import set_xafsGroup

MODNAME = '_xafs'
MAX_NNORM = 5

@ValidateLarchPlugin
def find_e0(energy, mu=None, group=None, _larch=None):
    """calculate E0 given mu(energy)

    This finds the point with maximum derivative with some
    checks to avoid spurious glitches.

    Arguments
    ----------
    energy:  array of x-ray energies, in eV or group
    mu:      array of mu(E)
    group:   output group

    Returns
    -------
    Value of e0.  If provided, group.e0 will be set to this value.

    Notes
    -----
       Supports First Argument Group convention, requiring group
       members 'energy' and 'mu'
    """
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='find_e0')

    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    energy = remove_dups(energy)
    dmu = np.gradient(mu)/np.gradient(energy)
    # find points of high derivative
    high_deriv_pts = np.where(dmu >  max(dmu)*0.05)[0]
    idmu_max, dmu_max = 0, 0
    for i in high_deriv_pts:
        if (dmu[i] > dmu_max and
            (i+1 in high_deriv_pts) and
            (i-1 in high_deriv_pts)):
            idmu_max, dmu_max = i, dmu[i]

    e0 = energy[idmu_max]
    if group is not None:
        group = set_xafsGroup(group, _larch=_larch)
        group.e0 = e0
    return e0

def flat_resid(pars):
    c0, c1, c2 =  pars.c0.value,  pars.c1.value,  pars.c2.value
    return  (pars.mu - (c0 + pars.en * (c1 + pars.en * c2)))


def preedge(energy, mu, e0=None, step=None,
            nnorm=3, nvict=0, pre1=None, pre2=-50,
            norm1=100, norm2=None):
    """pre edge subtraction, normalization for XAFS (straight python)

    This performs a number of steps:
       1. determine E0 (if not supplied) from max of deriv(mu)
       2. fit a line of polymonial to the region below the edge
       3. fit a polymonial to the region above the edge
       4. extrapolae the two curves to E0 to determine the edge jump

    Arguments
    ----------
    energy:  array of x-ray energies, in eV
    mu:      array of mu(E)
    e0:      edge energy, in eV.  If None, it will be determined here.
    step:    edge jump.  If None, it will be determined here.
    pre1:    low E range (relative to E0) for pre-edge fit
    pre2:    high E range (relative to E0) for pre-edge fit
    nvict:   energy exponent to use for pre-edg fit.  See Note
    norm1:   low E range (relative to E0) for post-edge fit
    norm2:   high E range (relative to E0) for post-edge fit
    nnorm:   degree of polynomial (ie, nnorm+1 coefficients will be found) for
             post-edge normalization curve. Default=3 (quadratic), max=5
    Returns
    -------
      dictionary with elements (among others)
          e0          energy origin in eV
          edge_step   edge step
          norm        normalized mu(E)
          pre_edge    determined pre-edge curve
          post_edge   determined post-edge, normalization curve

    Notes
    -----
     1 nvict gives an exponent to the energy term for the fits to the pre-edge
       and the post-edge region.  For the pre-edge, a line (m * energy + b) is
       fit to mu(energy)*energy**nvict over the pre-edge region,
       energy=[e0+pre1, e0+pre2].  For the post-edge, a polynomial of order
       nnorm will be fit to mu(energy)*energy**nvict of the post-edge region
       energy=[e0+norm1, e0+norm2].

    """
    energy = remove_dups(energy)

    if e0 is None or e0 < energy[0] or e0 > energy[-1]:
        energy = remove_dups(energy)
        dmu = np.gradient(mu)/np.gradient(energy)
        # find points of high derivative
        high_deriv_pts = np.where(dmu >  max(dmu)*0.05)[0]
        idmu_max, dmu_max = 0, 0
        for i in high_deriv_pts:
            if (dmu[i] > dmu_max and
                (i+1 in high_deriv_pts) and
                (i-1 in high_deriv_pts)):
                idmu_max, dmu_max = i, dmu[i]

        e0 = energy[idmu_max]
    nnorm = max(min(nnorm, MAX_NNORM), 0)
    ie0 = index_nearest(energy, e0)
    e0 = energy[ie0]

    if pre1 is None:  pre1  = min(energy) - e0
    if norm2 is None: norm2 = max(energy) - e0
    if norm2 < 0:     norm2 = max(energy) - e0 - norm2
    pre1  = max(pre1,  (min(energy) - e0))
    norm2 = min(norm2, (max(energy) - e0))

    if pre1 > pre2:
        pre1, pre2 = pre2, pre1
    if norm1 > norm2:
        norm1, norm2 = norm2, norm1

    p1 = index_of(energy, pre1+e0)
    p2 = index_nearest(energy, pre2+e0)
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    omu  = mu*energy**nvict
    ex, mx = remove_nans2(energy[p1:p2], omu[p1:p2])
    precoefs = polyfit(ex, mx, 1)
    pre_edge = (precoefs[0] * energy + precoefs[1]) * energy**(-nvict)
    # normalization
    p1 = index_of(energy, norm1+e0)
    p2 = index_nearest(energy, norm2+e0)
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    coefs = polyfit(energy[p1:p2], omu[p1:p2], nnorm)
    post_edge = 0
    norm_coefs = []
    for n, c in enumerate(reversed(list(coefs))):
        post_edge += c * energy**(n-nvict)
        norm_coefs.append(c)
    edge_step = step
    if edge_step is None:
        edge_step = post_edge[ie0] - pre_edge[ie0]

    norm = (mu - pre_edge)/edge_step
    out = {'e0': e0, 'edge_step': edge_step, 'norm': norm,
           'pre_edge': pre_edge, 'post_edge': post_edge,
           'norm_coefs': norm_coefs, 'nvict': nvict,
           'nnorm': nnorm, 'norm1': norm1, 'norm2': norm2,
           'pre1': pre1, 'pre2': pre2, 'precoefs': precoefs}

    return out

@ValidateLarchPlugin
@Make_CallArgs(["energy","mu"])
def pre_edge(energy, mu=None, group=None, e0=None, step=None,
             nnorm=3, nvict=0, pre1=None, pre2=-50,
             norm1=100, norm2=None, make_flat=True, _larch=None):
    """pre edge subtraction, normalization for XAFS

    This performs a number of steps:
       1. determine E0 (if not supplied) from max of deriv(mu)
       2. fit a line of polymonial to the region below the edge
       3. fit a polymonial to the region above the edge
       4. extrapolae the two curves to E0 to determine the edge jump

    Arguments
    ----------
    energy:  array of x-ray energies, in eV, or group (see note)
    mu:      array of mu(E)
    group:   output group
    e0:      edge energy, in eV.  If None, it will be determined here.
    step:    edge jump.  If None, it will be determined here.
    pre1:    low E range (relative to E0) for pre-edge fit
    pre2:    high E range (relative to E0) for pre-edge fit
    nvict:   energy exponent to use for pre-edg fit.  See Note
    norm1:   low E range (relative to E0) for post-edge fit
    norm2:   high E range (relative to E0) for post-edge fit
    nnorm:   degree of polynomial (ie, nnorm+1 coefficients will be found) for
             post-edge normalization curve. Default=3 (quadratic), max=5
    make_flat: boolean (Default True) to calculate flattened output.


    Returns
    -------
      None

    The following attributes will be written to the output group:
        e0          energy origin
        edge_step   edge step
        norm        normalized mu(E)
        flat        flattened, normalized mu(E)
        pre_edge    determined pre-edge curve
        post_edge   determined post-edge, normalization curve
        dmude       derivative of mu(E)

    (if the output group is None, _sys.xafsGroup will be written to)

    Notes
    -----
     1 nvict gives an exponent to the energy term for the fits to the pre-edge
       and the post-edge region.  For the pre-edge, a line (m * energy + b) is
       fit to mu(energy)*energy**nvict over the pre-edge region,
       energy=[e0+pre1, e0+pre2].  For the post-edge, a polynomial of order
       nnorm will be fit to mu(energy)*energy**nvict of the post-edge region
       energy=[e0+norm1, e0+norm2].

     2 If the first argument is a Group, it must contain 'energy' and 'mu'.
       If it exists, group.e0 will be used as e0.
       See First Argrument Group in Documentation
    """


    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='pre_edge')
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    pre_dat = preedge(energy, mu, e0=e0, step=step, nnorm=nnorm,
                      nvict=nvict, pre1=pre1, pre2=pre2, norm1=norm1,
                      norm2=norm2)


    group = set_xafsGroup(group, _larch=_larch)

    e0    = pre_dat['e0']
    norm  = pre_dat['norm']
    norm1 = pre_dat['norm1']
    norm2 = pre_dat['norm2']
    # generate flattened spectra, by fitting a quadratic to .norm
    # and removing that.
    flat = norm
    ie0 = index_nearest(energy, e0)
    p1 = index_of(energy, norm1+e0)
    p2 = index_nearest(energy, norm2+e0)
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    if make_flat and p2-p1 > 4:
        enx, mux = remove_nans2(energy[p1:p2], norm[p1:p2])
        # enx, mux = (energy[p1:p2], norm[p1:p2])
        fpars = Group(c0 = Parameter(0, vary=True),
                      c1 = Parameter(0, vary=True),
                      c2 = Parameter(0, vary=True),
                      en=enx, mu=mux)
        fit = Minimizer(flat_resid, fpars, _larch=_larch, toler=1.e-5)
        try:
            fit.leastsq()
        except (TypeError, ValueError):
            pass
        fc0, fc1, fc2  = fpars.c0.value, fpars.c1.value, fpars.c2.value
        flat_diff   = fc0 + energy * (fc1 + energy * fc2)
        flat        = norm - flat_diff  + flat_diff[ie0]
        flat[:ie0]  = norm[:ie0]


    group.e0 = e0
    group.norm = norm
    group.flat = flat
    group.dmude = np.gradient(mu)/np.gradient(energy)
    group.edge_step  = pre_dat['edge_step']
    group.pre_edge   = pre_dat['pre_edge']
    group.post_edge  = pre_dat['post_edge']

    group.pre_edge_details = Group()
    group.pre_edge_details.pre1   = pre_dat['pre1']
    group.pre_edge_details.pre2   = pre_dat['pre2']
    group.pre_edge_details.nnorm  = pre_dat['nnorm']
    group.pre_edge_details.norm1  = pre_dat['norm1']
    group.pre_edge_details.norm2  = pre_dat['norm2']
    group.pre_edge_details.pre_slope  = pre_dat['precoefs'][0]
    group.pre_edge_details.pre_offset = pre_dat['precoefs'][1]

    for i in range(MAX_NNORM):
        if hasattr(group, 'norm_c%i' % i):
            delattr(group, 'norm_c%i' % i)
    for i, c in enumerate(pre_dat['norm_coefs']):
        setattr(group.pre_edge_details, 'norm_c%i' % i, c)
    return

def registerLarchPlugin():
    return (MODNAME, {'find_e0': find_e0,
                      'pre_edge': pre_edge})
