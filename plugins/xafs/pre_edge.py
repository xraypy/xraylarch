#!/usr/bin/env python
"""
  XAFS pre-edge subtraction, normalization algorithms
"""

import numpy as np
from scipy import polyfit
from scipy.signal import find_peaks_cwt

from lmfit import Parameters, Minimizer
from lmfit.models import (LorentzianModel, GaussianModel,
                          VoigtModel, LinearModel)

try:
    import peakutils
    HAS_PEAKUTILS = True
except ImportError:
    HAS_PEAKUTILS = False

from larch import (Group, ValidateLarchPlugin,
                   Make_CallArgs, isgroup,
                   parse_group_args)

# now we can reliably import other std and xafs modules...

from larch.utils import (index_of, index_nearest,
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

def flat_resid(pars, en, mu):
    return (pars['c0'] + en * (pars['c1'] + en * pars['c2']) - mu)


def preedge(energy, mu, e0=None, step=None,
            nnorm=2, nvict=0, pre1=None, pre2=-50,
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
             post-edge normalization curve. Default=2 (quadratic), max=5
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

    pre1_input = pre1
    norm2_input = norm2

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

    # reduce dimension to linear if less than 75 eV given
    if abs(norm2-norm1) < 75.0:
        nnorm = min(nnorm, 1)

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
    return {'e0': e0, 'edge_step': edge_step, 'norm': norm,
            'pre_edge': pre_edge, 'post_edge': post_edge,
            'norm_coefs': norm_coefs, 'nvict': nvict,
            'nnorm': nnorm, 'norm1': norm1, 'norm2': norm2,
            'pre1': pre1, 'pre2': pre2, 'precoefs': precoefs,
            'norm2_input': norm2_input,  'pre1_input': pre1_input}

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
        fpars = Parameters()
        fpars.add('c0', value=0, vary=True)
        fpars.add('c1', value=0, vary=True)
        fpars.add('c2', value=0, vary=True)
        fit = Minimizer(flat_resid, fpars, fcn_args=(enx, mux))
        result = fit.leastsq(xtol=1.e-6, ftol=1.e-6)

        fc0 = result.params['c0'].value
        fc1 = result.params['c1'].value
        fc2 = result.params['c2'].value

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
    group.pre_edge_details.pre1_input  = pre_dat['pre1_input']
    group.pre_edge_details.norm2_input  = pre_dat['norm2_input']
    group.pre_edge_details.pre_slope  = pre_dat['precoefs'][0]
    group.pre_edge_details.pre_offset = pre_dat['precoefs'][1]

    for i in range(MAX_NNORM):
        if hasattr(group, 'norm_c%i' % i):
            delattr(group, 'norm_c%i' % i)
    for i, c in enumerate(pre_dat['norm_coefs']):
        setattr(group.pre_edge_details, 'norm_c%i' % i, c)
    return


@ValidateLarchPlugin
@Make_CallArgs(["energy", "norm"])
def pre_edge_baseline(energy, norm=None, group=None, form='lorentzian',
                      emin=None, emax=None, elo=None, ehi=None,
                      with_line=True, _larch=None):
    """remove baseline from main edge over pre edge peak region

    This assumes that pre_edge() has been run successfully on the spectra
    and that the spectra has decent pre-edge subtraction and normalization.

    Arguments
    ----------
    energy:    array of x-ray energies, in eV, or group (see note 1)
    norm:      array of normalized mu(E)
    group:     output group
    elo:       low energy of pre-edge peak region to not fit baseline [e0-20]
    ehi:       high energy of pre-edge peak region ot not fit baseline [e0-10]
    emax       max energy (eV) to use for baesline fit [e0-5]
    emin:      min energy (eV) to use for baesline fit [e0-40]
    form:      form used for baseline (see note 2)  ['lorentzian']
    with_line: whether to include linear component in baseline ['True']


    Returns
    -------
      None

    A group named 'prepeaks' will be created in the output group, with the following
    attributes:
        energy        energy array for pre-edge peaks = energy[emin-eneg:emax+epos]
        baseline      fitted baseline array over pre-edge peak energies
        mu            baseline-subtraced spectrum over pre-edge peak energies
        dmu           estimated uncertainty in mu from fit
        centroid      estimated centroid of pre-edge peaks (see note 3)
        peak_energies list of predicted peak energies (see note 4)
        fit_details   details of fit to extract pre-edge peaks.

    (if the output group is None, _sys.xafsGroup will be written to)

    Notes
    -----
     1 If the first argument is a Group, it must contain 'energy' and 'norm'.
       See First Argrument Group in Documentation

     2 A function will be fit to the input mu(E) data over the range between
       [emin:elo] and [ehi:emax], ignorng the pre-edge peaks in the
       region [elo:ehi].  The baseline function is specified with the `form`
       keyword argument, which can be one of
           'lorentzian', 'gaussian', or 'voigt',
       with 'lorentzian' the default.  In addition, the `with_line` keyword
       argument can be used to add a line to this baseline function.

     3 The value calculated for `prepeaks.centroid`  will be found as
         (prepeaks.energy*prepeaks.mu).sum() / prepeaks.mu.sum()
     4 The values in the `peak_energies` list will be predicted energies
       of the peaks in `prepeaks.mu` as found by peakutils.

    """
    energy, norm, group = parse_group_args(energy, members=('energy', 'norm'),
                                           defaults=(norm,), group=group,
                                           fcn_name='pre_edge_baseline')
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(norm.shape) > 1:
        norm = norm.squeeze()

    dat_emin, dat_emax = min(energy), max(energy)

    dat_e0 = getattr(group, 'e0', -1)

    if dat_e0 > 0:
        if emin is None:
            emin = dat_e0 - 30.0
        if emax is None:
            emax = dat_e0 - 1.0
        if elo is None:
            elo = dat_e0 - 15.0
        if ehi is None:
            ehi = dat_e0 - 5.0
        if emin < 0:
            emin += dat_e0
        if elo < 0:
            elo += dat_e0
        if emax < dat_emin:
            emax += dat_e0
        if ehi < dat_emin:
            ehi += dat_e0

    if emax is None or emin is None or elo is None or ehi is None:
        raise ValueError("must provide emin and emax to pre_edge_baseline")


    # get indices for input energies
    if emin > emax:
        emin, emax = emax, emin
    if emin > elo:
        elo, emin = emin, elo
    if ehi > emax:
        ehi, emax = emax, ehi

    imin = index_of(energy, emin)
    ilo  = index_of(energy, elo)
    ihi  = index_of(energy, ehi)
    imax = index_of(energy, emax)

    # build xdat, ydat: dat to fit (skipping pre-edge peaks)
    xdat = np.concatenate((energy[imin:ilo+1], energy[ihi:imax+1]))
    ydat = np.concatenate((norm[imin:ilo+1], norm[ihi:imax+1]))

    # build fitting model: note that we always include
    # a LinearModel but may fix slope and intercept
    form = form.lower()
    if form.startswith('voig'):
        model = VoigtModel()
    elif form.startswith('gaus'):
        model = GaussianModel()
    else:
        model = LorentzianModel()

    model += LinearModel()
    params = model.make_params(amplitude=1.0, sigma=2.0,
                               center=emax,
                               intercept=0, slope=0)
    params['amplitude'].min =  0.0
    params['sigma'].min     =  0.25
    params['sigma'].max     = 50.0
    params['center'].max    = emax + 25.0
    params['center'].min    = emax - 25.0

    if not with_line:
        params['slope'].vary = False
        params['intercept'].vary = False

    # run fit
    result = model.fit(ydat, params, x=xdat)

    # energy including pre-edge peaks, for output
    edat = energy[imin: imax+1]

    # get baseline and resulting mu over edat range
    bline = result.eval(result.params, x=edat)
    mu  = norm[imin:imax+1]-bline

    # uncertainty in mu includes only uncertainties in baseline fit
    dmu = result.eval_uncertainty(result.params, x=edat)

    # estimate centroid and its uncertainty
    cen = (edat*mu).sum() / mu.sum()
    cen_plus = (edat*(mu+dmu)).sum()/ (mu+dmu).sum()
    cen_minus = (edat*(mu-dmu)).sum()/ (mu-dmu).sum()
    dcen = abs(cen_minus - cen_plus) / 2.0

    # locate peak positions
    peak_energies = []
    if HAS_PEAKUTILS:
        peak_ids = peakutils.peak.indexes(mu, thres=0.05, min_dist=2)
        peak_energies = [edat[pid] for pid in peak_ids]

    group = set_xafsGroup(group, _larch=_larch)
    group.prepeaks = Group(energy=edat, mu=mu, delta_mu=dmu,
                           baseline=bline,
                           centroid=cen, delta_centroid=dcen,
                           peak_energies=peak_energies,
                           fit_details=result,
                           emin=emin, emax=emax, elo=elo, ehi=ehi,
                           form=form, with_line=with_line)
    return

def registerLarchPlugin():
    return (MODNAME, {'find_e0': find_e0,
                      'pre_edge': pre_edge,
                      'pre_edge_baseline': pre_edge_baseline})
