#!/usr/bin/env python
"""
  XAFS pre-edge subtraction, normalization algorithms
"""
import numpy as np

from lmfit import Parameters, Minimizer
from xraydb import guess_edge
from larch import Group, Make_CallArgs, parse_group_args

from larch.math import index_of, index_nearest, remove_dups, remove_nans2
from .xafsutils import set_xafsGroup

MODNAME = '_xafs'
MAX_NNORM = 5

@Make_CallArgs(["energy","mu"])
def find_e0(energy, mu=None, group=None, _larch=None):
    """calculate :math:`E_0`, the energy threshold of absorption, or
    'edge energy', given :math:`\mu(E)`.

    :math:`E_0` is found as the point with maximum derivative with
    some checks to avoid spurious glitches.

    Arguments:
        energy (ndarray or group): array of x-ray energies, in eV, or group
        mu     (ndaarray or None): array of mu(E) values
        group  (group or None):    output group
        _larch (larch instance or None):  current larch session.

    Returns:
        float: Value of e0. If a group is provided, group.e0 will also be set.

    Notes:
        1. Supports :ref:`First Argument Group` convention, requiring group members `energy` and `mu`
        2. Supports :ref:`Set XAFS Group` convention within Larch or if `_larch` is set.
    """
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='find_e0')
    e0 = _finde0(energy, mu)
    if group is not None:
        group = set_xafsGroup(group, _larch=_larch)
        group.e0 = e0
    return e0

def _finde0(energy, mu):
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    dmu = np.gradient(mu)/np.gradient(energy)
    # find points of high derivative
    dmu[np.where(~np.isfinite(dmu))] = -1.0
    nmin = max(3, int(len(dmu)*0.05))
    maxdmu = max(dmu[nmin:-nmin])

    high_deriv_pts = np.where(dmu >  maxdmu*0.1)[0]
    idmu_max, dmu_max = 0, 0

    for i in high_deriv_pts:
        if i < nmin or i > len(energy) - nmin:
            continue
        if (dmu[i] > dmu_max and
            (i+1 in high_deriv_pts) and
            (i-1 in high_deriv_pts)):
            idmu_max, dmu_max = i, dmu[i]

    return energy[idmu_max]

def flat_resid(pars, en, mu):
    return (pars['c0'] + en * (pars['c1'] + en * pars['c2']) - mu)


def preedge(energy, mu, e0=None, step=None, nnorm=None, nvict=0, pre1=None,
            pre2=None, norm1=None, norm2=None):
    """pre edge subtraction, normalization for XAFS (straight python)

    This performs a number of steps:
       1. determine E0 (if not supplied) from max of deriv(mu)
       2. fit a line to the region below the edge
       3. fit a polymonial to the region above the edge
       4. extrapolate the two curves to E0 and take their difference
          to determine the edge jump

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
             post-edge normalization curve. Default=None -- see note.
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
    1  pre_edge: a line is fit to mu(energy)*energy**nvict over the region,
       energy=[e0+pre1, e0+pre2]. pre1 and pre2 default to None, which will set
           pre1 = e0 - 2nd energy point, rounded to 5 eV
           pre2 = roughly pre1/3.0, rounded to 5 eV

    2  post-edge: a polynomial of order nnorm is fit to mu(energy)*energy**nvict
       between energy=[e0+norm1, e0+norm2]. nnorm, norm1, norm2 default to None,
       which will set:
         nnorm = 2 in norm2-norm1>350, 1 if norm2-norm1>50, or 0 if less.
         norm2 = max energy - e0, rounded to 5 eV
         norm1 = roughly min(150, norm2/3.0), rounded to 5 eV
    """
    energy = remove_dups(energy)
    if e0 is None or e0 < energy[1] or e0 > energy[-2]:
        e0 = _finde0(energy, mu)

    ie0 = index_nearest(energy, e0)
    e0 = energy[ie0]

    if pre1 is None:
        # skip first energy point, often bad
        if ie0 > 20:
            pre1  = 5.0*round((energy[1] - e0)/5.0)
        else:
            pre1  = 2.0*round((energy[1] - e0)/2.0)

    pre1 = max(pre1,  (min(energy) - e0))
    if pre2 is None:
        pre2 = 5.0*round(pre1/15.0)
    if pre1 > pre2:
        pre1, pre2 = pre2, pre1

    if norm2 is None:
        norm2 = 5.0*round((max(energy) - e0)/5.0)
    if norm2 < 0:
        norm2 = max(energy) - e0 - norm2
    norm2 = min(norm2, (max(energy) - e0))
    if norm1 is None:
        norm1 = min(150, 5.0*round(norm2/15.0))
    if norm1 > norm2:
        norm1, norm2 = norm2, norm1
    if nnorm is None:
        nnorm = 2
        if norm2-norm1 < 350: nnorm = 1
        if norm2-norm1 <  50: nnorm = 0
    nnorm = max(min(nnorm, MAX_NNORM), 0)

    # preedge
    p1 = index_of(energy, pre1+e0)
    p2 = index_nearest(energy, pre2+e0)
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    omu  = mu*energy**nvict
    ex, mx = remove_nans2(energy[p1:p2], omu[p1:p2])
    precoefs = np.polyfit(ex, mx, 1)
    pre_edge = (precoefs[0] * energy + precoefs[1]) * energy**(-nvict)

    # normalization
    p1 = index_of(energy, norm1+e0)
    p2 = index_nearest(energy, norm2+e0)
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    presub = (mu-pre_edge)[p1:p2]
    coefs = np.polyfit(energy[p1:p2], presub, nnorm)
    post_edge = 1.0*pre_edge
    norm_coefs = []
    for n, c in enumerate(reversed(list(coefs))):
        post_edge += c * energy**(n)
        norm_coefs.append(c)
    edge_step = step
    if edge_step is None:
        edge_step = post_edge[ie0] - pre_edge[ie0]
    edge_step = abs(float(edge_step))

    norm = (mu - pre_edge)/edge_step
    return {'e0': e0, 'edge_step': edge_step, 'norm': norm,
            'pre_edge': pre_edge, 'post_edge': post_edge,
            'norm_coefs': norm_coefs, 'nvict': nvict,
            'nnorm': nnorm, 'norm1': norm1, 'norm2': norm2,
            'pre1': pre1, 'pre2': pre2, 'precoefs': precoefs}

@Make_CallArgs(["energy","mu"])

def pre_edge(energy, mu=None, group=None, e0=None, step=None, nnorm=None,
             nvict=0, pre1=None, pre2=None, norm1=None, norm2=None,
             make_flat=True, _larch=None):
    """pre edge subtraction, normalization for XAFS

    This performs a number of steps:
       1. determine E0 (if not supplied) from max of deriv(mu)
       2. fit a line of polymonial to the region below the edge
       3. fit a polymonial to the region above the edge
       4. extrapolate the two curves to E0 and take their difference
          to determine the edge jump

    Arguments
    ----------
    energy:  array of x-ray energies, in eV, or group (see note 1)
    mu:      array of mu(E)
    group:   output group
    e0:      edge energy, in eV. If None, it will be determined here.
    step:    edge jump.  If None, it will be determined here.
    pre1:    low E range (relative to E0) for pre-edge fit
    pre2:    high E range (relative to E0) for pre-edge fit
    nvict:   energy exponent to use for pre-edg fit.  See Notes.
    norm1:   low E range (relative to E0) for post-edge fit
    norm2:   high E range (relative to E0) for post-edge fit
    nnorm:   degree of polynomial (ie, nnorm+1 coefficients will be found) for
             post-edge normalization curve. See Notes.
    make_flat: boolean (Default True) to calculate flattened output.

    Returns
    -------
      None: The following attributes will be written to the output group:
        e0          energy origin
        edge_step   edge step
        norm        normalized mu(E), using polynomial
        norm_area   normalized mu(E), using integrated area
        flat        flattened, normalized mu(E)
        pre_edge    determined pre-edge curve
        post_edge   determined post-edge, normalization curve
        dmude       derivative of normalized mu(E)
        d2mude      second derivative of normalized mu(E)

    (if the output group is None, _sys.xafsGroup will be written to)

    Notes
    -----
      1. Supports `First Argument Group` convention, requiring group members `energy` and `mu`.
      2. Support `Set XAFS Group` convention within Larch or if `_larch` is set.
      3. pre_edge: a line is fit to mu(energy)*energy**nvict over the region,
         energy=[e0+pre1, e0+pre2]. pre1 and pre2 default to None, which will set
             pre1 = e0 - 2nd energy point, rounded to 5 eV
             pre2 = roughly pre1/3.0, rounded to 5 eV
      4. post-edge: a polynomial of order nnorm is fit to mu(energy)*energy**nvict
         between energy=[e0+norm1, e0+norm2]. nnorm, norm1, norm2 default to None,
         which will set:
              norm2 = max energy - e0, rounded to 5 eV
              norm1 = roughly min(150, norm2/3.0), rounded to 5 eV
              nnorm = 2 in norm2-norm1>350, 1 if norm2-norm1>50, or 0 if less.
      5. flattening fits a quadratic curve (no matter nnorm) to the post-edge
         normalized mu(E) and subtracts that curve from it.
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
        fpars = Parameters()
        ncoefs = len(pre_dat['norm_coefs'])
        fpars.add('c0', value=0, vary=True)
        fpars.add('c1', value=0, vary=(ncoefs>1))
        fpars.add('c2', value=0, vary=(ncoefs>2))
        fit = Minimizer(flat_resid, fpars, fcn_args=(enx, mux))
        result = fit.leastsq(xtol=1.e-6, ftol=1.e-6)

        fc0 = result.params['c0'].value
        fc1 = result.params['c1'].value
        fc2 = result.params['c2'].value

        flat_diff   = fc0 + energy * (fc1 + energy * fc2)
        flat        = norm - (flat_diff  - flat_diff[ie0])
        flat[:ie0]  = norm[:ie0]


    group.e0 = e0
    group.norm = norm
    group.norm_poly = 1.0*norm
    group.flat = flat
    group.dmude = np.gradient(norm)/np.gradient(energy)
    group.d2mude = np.gradient(group.dmude)/np.gradient(energy)
    group.edge_step  = pre_dat['edge_step']
    group.edge_step_poly = pre_dat['edge_step']
    group.pre_edge   = pre_dat['pre_edge']
    group.post_edge  = pre_dat['post_edge']

    group.pre_edge_details = Group()
    for attr in ('pre1', 'pre2', 'norm1', 'norm2', 'nnorm', 'nvict'):
        setattr(group.pre_edge_details, attr, pre_dat.get(attr, None))

    group.pre_edge_details.pre_slope  = pre_dat['precoefs'][0]
    group.pre_edge_details.pre_offset = pre_dat['precoefs'][1]

    for i in range(MAX_NNORM):
        if hasattr(group, 'norm_c%i' % i):
            delattr(group, 'norm_c%i' % i)
    for i, c in enumerate(pre_dat['norm_coefs']):
        setattr(group.pre_edge_details, 'norm_c%i' % i, c)

    # guess element and edge
    group.atsym = getattr(group, 'atsym', None)
    group.edge = getattr(group, 'edge', None)

    if group.atsym is None or group.edge is None:
        _atsym, _edge = guess_edge(group.e0)
        if group.atsym is None: group.atsym = _atsym
        if group.edge is None:  group.edge = _edge
    return
