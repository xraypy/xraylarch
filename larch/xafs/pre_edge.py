#!/usr/bin/env python
"""
  XAFS pre-edge subtraction, normalization algorithms
"""
import numpy as np

from lmfit import Parameters, Minimizer, report_fit
from xraydb import guess_edge
from larch import Group, Make_CallArgs, parse_group_args

from larch.math import (index_of, index_nearest, interp, smooth,
                        polyfit, remove_dups, remove_nans, remove_nans2)
from .xafsutils import set_xafsGroup, TINY_ENERGY

MODNAME = '_xafs'
MAX_NNORM = 5

@Make_CallArgs(["energy","mu"])
def find_e0(energy, mu=None, group=None, _larch=None):
    """calculate E0, the energy threshold of absorption, or 'edge energy', given mu(E).

    E0 is found as the point with maximum derivative with some checks to avoid spurious glitches.

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
    # first find e0 without smoothing, then refine with smoothing
    e1, ie0, estep1 = _finde0(energy, mu, estep=None, use_smooth=False)
    istart = max(3, ie0-75)
    istop  = min(ie0+75, len(energy)-3)
    # sanity check: e0 should not be in first 5% of energy point: avoids common glitches
    if ie0 < 0.05*len(energy):
        e1 = energy.mean()
        istart = max(3, ie0-20)
        istop = len(energy)-3

    # for the smoothing energy, we use and energy step that is an average of
    # the observed minimimum energy step (which could be ridiculously low)
    # and a scaled value of the initial e0 (0.2 eV and 5000 eV, 0.4 eV at 10000 eV)
    # print("Find E0 step 1 ", e1, ie0, len(energy), estep1, istart, istop)
    estep = 0.5*(max(0.01, min(1.0, estep1)) + max(0.01, min(1.0, e1/25000.)))
    e0, ix, ex = _finde0(energy[istart:istop], mu[istart:istop], estep=estep, use_smooth=True)
    if ix < 1 :
        e0 = energy[istart+2]
    if group is not None:
        group = set_xafsGroup(group, _larch=_larch)
        group.e0 = e0
    return e0

def find_energy_step(energy, frac_ignore=0.01, nave=10):
    """robustly find energy step in XAS energy array,
    ignoring the smallest fraction of energy steps (frac_ignore),
    and averaging over the next `nave` values
    """
    nskip = int(frac_ignore*len(energy))
    e_ordered = np.where(np.diff(np.argsort(energy))==1)[0]  # where energy step are in order
    ediff = np.diff(energy[e_ordered][nskip:-nskip])
    return ediff[np.argsort(ediff)][nskip:nskip+nave].mean()


def _finde0(energy, mu_input, estep=None, use_smooth=True):
    "internally used by find e0 "

    en = remove_dups(energy, tiny=TINY_ENERGY)
    ordered = np.where(np.diff(np.argsort(en))==1)[0]
    en = en[ordered]
    mu = mu_input[ordered]
    if len(en.shape) > 1:
        en = en.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()
    if estep is None:
        estep = find_energy_step(en)


    nmin = max(3, int(len(en)*0.02))
    if use_smooth:
        dmu = smooth(en, np.gradient(mu)/np.gradient(en), xstep=estep, sigma=estep)
    else:
        dmu = np.gradient(mu)/np.gradient(en)
    # find points of high derivative
    dmu[np.where(~np.isfinite(dmu))] = -1.0
    dm_min = dmu[nmin:-nmin].min()
    dm_ptp = max(1.e-10, np.ptp(dmu[nmin:-nmin]))
    dmu = (dmu - dm_min)/dm_ptp

    dhigh = 0.60 if len(en) > 20 else 0.30
    high_deriv_pts = np.where(dmu > dhigh)[0]
    if len(high_deriv_pts) < 3:
        for _ in range(2):
            if len(high_deriv_pts) > 3:
                break
            dhigh *= 0.5
            high_deriv_pts = np.where(dmu > dhigh)[0]

    if len(high_deriv_pts) < 3:
        high_deriv_pts = np.where(np.isfinite(dmu))[0]

    imax, dmax = 0, 0
    for i in high_deriv_pts:
        if i < nmin or i > len(en) - nmin:
            continue
        if (dmu[i] > dmax and
            (i+1 in high_deriv_pts) and
            (i-1 in high_deriv_pts)):
            imax, dmax = i, dmu[i]
    return en[imax], imax, estep

def flat_resid(pars, en, mu):
    return pars['c0'] + en * (pars['c1'] + en * pars['c2']) - mu

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
         nnorm = 2 in norm2-norm1>300, 1 if norm2-norm1>30, or 0 if less.
         norm2 = max energy - e0, rounded to 5 eV
         norm1 = roughly min(150, norm2/3.0), rounded to 5 eV
    """

    energy, mu = remove_nans2(energy, mu)
    energy = remove_dups(energy, tiny=TINY_ENERGY)
    if energy.size <= 1:
        raise ValueError("energy array must have at least 2 points")
    if e0 is None or e0 < energy[1] or e0 > energy[-2]:
        e0 = find_e0(energy, mu)
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
        pre2 = 0.5*pre1
    if pre1 > pre2:
        pre1, pre2 = pre2, pre1
    ipre1 = index_of(energy-e0, pre1)
    ipre2 = index_of(energy-e0, pre2)
    if ipre2 < ipre1 + 2 + nvict:
        pre2 = (energy-e0)[int(ipre1 + 2 + nvict)]

    if norm2 is None:
        norm2 = 5.0*round((max(energy) - e0)/5.0)
    if norm2 < 0:
        norm2 = max(energy) - e0 - norm2
    norm2 = min(norm2, (max(energy) - e0))
    if norm1 is None:
        norm1 = min(25, 5.0*round(norm2/15.0))

    if norm1 > norm2:
        norm1, norm2 = norm2, norm1

    norm1 = min(norm1, norm2 - 10)
    if nnorm is None:
        nnorm = 2
        if norm2-norm1 < 300: nnorm = 1
        if norm2-norm1 <  30: nnorm = 0
    nnorm = max(min(nnorm, MAX_NNORM), 0)
    # preedge
    p1 = index_of(energy, pre1+e0)
    p2 = index_nearest(energy, pre2+e0)
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    omu  = mu*energy**nvict
    ex = remove_nans(energy[p1:p2], interp=True)
    mx = remove_nans(omu[p1:p2], interp=True)

    precoefs = polyfit(ex, mx, 1)
    pre_edge = (precoefs[0] + energy*precoefs[1]) * energy**(-nvict)
    # normalization
    p1 = index_of(energy, norm1+e0)
    p2 = index_nearest(energy, norm2+e0)
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)
    if p2-p1 < 2:
        p1 = p1-2

    presub = (mu-pre_edge)[p1:p2]
    coefs = polyfit(energy[p1:p2], presub, nnorm)
    post_edge = 1.0*pre_edge
    norm_coefs = []
    for n, c in enumerate(coefs):
        post_edge += c * energy**(n)
        norm_coefs.append(c)
    edge_step = step
    if edge_step is None:
        edge_step = post_edge[ie0] - pre_edge[ie0]
    edge_step = max(1.e-12, abs(float(edge_step)))
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
              nnorm = 2 in norm2-norm1>300, 1 if norm2-norm1>30, or 0 if less.
      5. flattening fits a quadratic curve (no matter nnorm) to the post-edge
         normalized mu(E) and subtracts that curve from it.
    """
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='pre_edge')
    energy, mu = remove_nans2(energy, mu)
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    out_of_order = np.where(np.diff(np.argsort(energy))!=1)[0]
    if len(out_of_order) > 0:
        order = np.argsort(energy)
        energy = energy[order]
        mu = mu[order]
    energy = remove_dups(energy, tiny=TINY_ENERGY)

    if group is not None and e0 is None:
        e0 = getattr(group, 'e0', None)
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

    ie0 = index_nearest(energy, e0)
    p1 = index_of(energy, norm1+e0)
    p2 = index_nearest(energy, norm2+e0)
    if p2-p1 < 2:
        p2 = min(len(energy), p1 + 2)

    group.e0 = e0
    group.norm = norm
    group.flat = 1.0*norm
    group.norm_poly = 1.0*norm

    if make_flat:
        pre_edge = pre_dat['pre_edge']
        post_edge = pre_dat['post_edge']
        edge_step = pre_dat['edge_step']
        flat_residue = (post_edge - pre_edge)/edge_step
        flat = norm - flat_residue + flat_residue[ie0]
        flat[:ie0] = norm[:ie0]
        group.flat = flat

        enx = remove_nans(energy[p1:p2], interp=True)
        mux = remove_nans(norm[p1:p2], interp=True)

        # enx, mux = (energy[p1:p2], norm[p1:p2])
        fpars = Parameters()
        ncoefs = len(pre_dat['norm_coefs'])
        fpars.add('c0', value=1.0, vary=True)
        fpars.add('c1', value=0.0, vary=False)
        fpars.add('c2', value=0.0, vary=False)
        if ncoefs > 1:
            fpars['c1'].set(value=1.e-5, vary=True)
            if ncoefs > 2:
                fpars['c2'].set(value=1.e-5, vary=True)

        try:
            fit = Minimizer(flat_resid, fpars, fcn_args=(enx, mux))
            result = fit.leastsq()
            fc0 = result.params['c0'].value
            fc1 = result.params['c1'].value
            fc2 = result.params['c2'].value

            flat_diff = fc0 + energy * (fc1 + energy * fc2)
            flat_alt  = norm - flat_diff  + flat_diff[ie0]
            flat_alt[:ie0]  = norm[:ie0]
            group.flat_coefs = (fc0, fc1, fc2)
            group.flat_alt = flat_alt
        except:
            pass

    group.dmude = np.gradient(norm)/np.gradient(energy)
    group.d2mude = np.gradient(group.dmude)/np.gradient(energy)
    group.edge_step  = pre_dat['edge_step']
    group.edge_step_poly = pre_dat['edge_step']
    group.pre_edge   = pre_dat['pre_edge']
    group.post_edge  = pre_dat['post_edge']

    group.pre_edge_details = Group()
    for attr in ('pre1', 'pre2', 'norm1', 'norm2', 'nnorm', 'nvict'):
        setattr(group.pre_edge_details, attr, pre_dat.get(attr, None))

    group.pre_edge_details.pre_slope  = pre_dat['precoefs'][1]
    group.pre_edge_details.pre_offset = pre_dat['precoefs'][0]

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

def energy_align(group, reference, array='dmude', emin=-15, emax=35):
    """
    align XAFS data group to a reference group

    Arguments
    ---------
    group      Larch group for spectrum to be aligned (see Note 1)
    reference  Larch group for reference spectrum     (see Note 1)
    array      string of 'dmude', 'norm', or 'mu'     (see Note 2) ['dmude']
    emin       float, min energy relative to e0 of reference for alignment [-15]
    emax       float, max energy relative to e0 of reference for alignment [+35]

    Returns
    -------
    eshift   energy shift to add to group.energy to match reference.
             This value will also be written to group.eshift

    Notes
    -----
      1.  Both group and reference must be XAFS data, with arrays of 'energy' and 'mu'.
          The reference group must already have an e0 value set.

      2.  The alignment can be done with 'mu' or 'dmude'.  If it does not exist, the
          dmude array will be built for group and reference.

    """
    if not (hasattr(group, 'energy') and hasattr(group, 'mu')):
        raise ValueError("group must have attributes 'energy' and 'mu'")

    if not hasattr(group, 'dmude'):
        mu = getattr(group, 'norm', getattr(group, 'mu'))
        en = getattr(group, 'energy')
        group.dmude = gradient(mu)/gradient(en)


    if not (hasattr(reference, 'energy') and hasattr(reference, 'mu')
            and hasattr(reference, 'e0') ):
        raise ValueError("reference must have attributes 'energy', 'mu', and 'e0'")

    if not hasattr(reference, 'dmude'):
        mu = getattr(reference, 'norm', getattr(reference, 'mu'))
        en = getattr(reference, 'energy')
        reference.dmude = gradient(mu)/gradient(en)

    xdat = group.energy[:]*1.0
    xref = reference.energy[:]*1.0
    ydat = group.dmude[:]*1.0
    yref = reference.dmude[:]*1.0
    if array == 'mu':
        ydat = group.mu[:]*1.0
        yref = reference.mu[:]*1.0
    elif array == 'norm':
        ydat = group.norm[:]*1.0
        yref = reference.norm[:]*1.0

    xdat = remove_nans(xdat[:], interp=True)
    ydat = remove_nans(ydat[:], interp=True)
    xref = remove_nans(xref[:], interp=True)
    yref = remove_nans(yref[:], interp=True)

    i1 = index_of(xref, reference.e0-emin)
    i2 = index_of(xref, reference.e0+emax)

    def align_resid(params, xdat, ydat, xref, yref, i1, i2):
        "fit residual"
        newx = xdat + params['eshift'].value
        scale = params['scale'].value
        ytmp = interp(newx, ydat, xref, kind='cubic')
        return (ytmp*scale - yref)[i1:i2]

    params = Parameters()
    params.add('eshift', value=0, min=-50, max=50)
    params.add('scale', value=1, min=0, max=50)

    try:
        fit = Minimizer(align_resid, params,
                        fcn_args=(xdat, ydat, xref, yref, i1, i2))
        result = fit.leastsq()
        eshift = result.params['eshift'].value
    except:
        eshift = 0

    group.eshift = eshift
    return eshift
