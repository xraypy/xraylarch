#!/usr/bin/env python
"""
  XAFS pre-edge subtraction, normalization algorithms
"""
from copy import deepcopy
import numpy as np
from lmfit import Parameters, Minimizer, Model
from lmfit.models import (LorentzianModel, GaussianModel, VoigtModel,
                          ConstantModel, LinearModel, QuadraticModel)
try:
    import peakutils
    HAS_PEAKUTILS = True
except ImportError:
    HAS_PEAKUTILS = False

from xraydb import guess_edge, xray_edge, core_width

from larch import Group, Make_CallArgs, isgroup, parse_group_args
# now we can reliably import other std and xafs modules...

from larch.math import (index_of, index_nearest,
                        remove_dups, remove_nans2)
from .xafsutils import set_xafsGroup

@Make_CallArgs(["energy", "norm"])
def prepeaks_setup(energy, norm=None, arrayname=None, group=None, emin=None, emax=None,
                   elo=None, ehi=None, _larch=None):
    """set up pre edge peak group.

    This assumes that pre_edge() has been run successfully on the spectra
    and that the spectra has decent pre-edge subtraction and normalization.

    Arguments:
       energy (ndarray or group): array of x-ray energies, in eV, or group (see note 1)
       norm (ndarray or None):    array of normalized mu(E) to be fit (deprecated, see note 2)
       arrayname (string or None):  name of array to use as data (see note 2)
       group (group or None):     output group
       emax (float or None):      max energy (eV) to use for baesline fit [e0-5]
       emin (float or None):      min energy (eV) to use for baesline fit [e0-40]
       elo: (float or None)       low energy of pre-edge peak region to not fit baseline [e0-20]
       ehi: (float or None)       high energy of pre-edge peak region ot not fit baseline [e0-10]
       _larch (larch instance or None):  current larch session.

    A group named `prepeaks` will be created in the output group, containing:

        ==============   ===========================================================
         attribute        meaning
        ==============   ===========================================================
         energy           energy array for pre-edge peaks = energy[emin:emax]
         norm             spectrum over pre-edge peak energies
        ==============   ===========================================================

    Note that 'norm' will be used here even if a differnt input array was used.

    Notes:
        1. Supports :ref:`First Argument Group` convention, requiring group members `energy` and `norm`
        2. You can pass is an array to fit with 'norm=', or you can name the array to use with
           `arrayname`, which can be one of ['norm', 'flat', 'deconv', 'aspassed', None] with None
           and 'aspassed' meaning that the argument of `norm` will be used, as passed in.
        3. Supports :ref:`Set XAFS Group` convention within Larch or if `_larch` is set.
    """
    ydat = None
    if norm is not None and arrayname in (None, 'aspassed'):
        arrayname = 'aspassed'
        ydat = norm[:]

    energy, norm, group = parse_group_args(energy, members=('energy', 'norm'),
                                           defaults=(norm,), group=group,
                                           fcn_name='pre_edge_baseline')
    if arrayname == 'flat' and hasattr(group, 'flat'):
        ydat = group.flat[:]
    elif arrayname == 'deconv' and hasattr(group, 'deconv'):
        ydat = group.deconv[:]
    if ydat is None:
        ydat = norm[:]

    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(ydat.shape) > 1:
        ydat = ydat.squeeze()

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
        raise ValueError("must provide emin and emax to prepeaks_setup")

    # get indices for input energies
    if emin > emax:
        emin, emax = emax, emin
    if emin > elo:
        elo, emin = emin, elo
    if ehi > emax:
        ehi, emax = emax, ehi

    dele = 1.e-13 + min(np.diff(energy))/5.0

    ilo  = index_of(energy, elo+dele)
    ihi  = index_of(energy, ehi+dele)
    imin = index_of(energy, emin+dele)
    imax = index_of(energy, emax+dele)

    edat = energy[imin: imax+1]
    ydat = ydat[imin:imax+1]

    if not hasattr(group, 'prepeaks'):
        group.prepeaks = Group(energy=edat, norm=ydat,
                               emin=emin, emax=emax,
                               elo=elo, ehi=ehi)
    else:
        group.prepeaks.energy = edat
        group.prepeaks.norm = ydat
        group.prepeaks.emin = emin
        group.prepeaks.emax = emax
        group.prepeaks.elo = elo
        group.prepeaks.ehi = ehi

    group.prepeaks.xdat = edat
    group.prepeaks.ydat = norm
    return

@Make_CallArgs(["energy", "norm"])
def pre_edge_baseline(energy, norm=None, group=None, form='linear+lorentzian',
                      emin=None, emax=None, elo=None, ehi=None, _larch=None):
    """remove baseline from main edge over pre edge peak region

    This assumes that pre_edge() has been run successfully on the spectra
    and that the spectra has decent pre-edge subtraction and normalization.

    Arguments:
       energy (ndarray or group): array of x-ray energies, in eV, or group (see note 1)
       norm (ndarray or group):   array of normalized mu(E)
       group (group or None):     output group
       elo (float or None):       low energy of pre-edge peak region to not fit baseline [e0-20]
       ehi (float or None):       high energy of pre-edge peak region ot not fit baseline [e0-10]
       emax (float or None):      max energy (eV) to use for baesline fit [e0-5]
       emin (float or None):      min energy (eV) to use for baesline fit [e0-40]
       form (string):             form used for baseline (see description)  ['linear+lorentzian']
       _larch (larch instance or None):  current larch session.


    A function will be fit to the input mu(E) data over the range between
    [emin:elo] and [ehi:emax], ignorng the pre-edge peaks in the region
    [elo:ehi].  The baseline function is specified with the `form` keyword
    argument, which can be one or a combination of 'lorentzian', 'gaussian', or 'voigt',
    plus one of 'constant', 'linear', 'quadratic', for example, 'linear+lorentzian',
    'constant+voigt', 'quadratic', 'gaussian'.

    A group named 'prepeaks' will be used or created in the output group, containing

        ==============   ===========================================================
         attribute        meaning
        ==============   ===========================================================
         energy           energy array for pre-edge peaks = energy[emin:emax]
         baseline         fitted baseline array over pre-edge peak energies
         norm             spectrum over pre-edge peak energies
         peaks            baseline-subtraced spectrum over pre-edge peak energies
         centroid         estimated centroid of pre-edge peaks (see note 3)
         peak_energies    list of predicted peak energies (see note 4)
         fit_details      details of fit to extract pre-edge peaks.
        ==============   ===========================================================

    Notes:
       1. Supports :ref:`First Argument Group` convention, requiring group members `energy` and `norm`
       2. Supports :ref:`Set XAFS Group` convention within Larch or if `_larch` is set.
       3. The value calculated for `prepeaks.centroid`  will be found as
          (prepeaks.energy*prepeaks.peaks).sum() / prepeaks.peaks.sum()
       4. The values in the `peak_energies` list will be predicted energies
          of the peaks in `prepeaks.peaks` as found by peakutils.

    """
    energy, norm, group = parse_group_args(energy, members=('energy', 'norm'),
                                           defaults=(norm,), group=group,
                                           fcn_name='pre_edge_baseline')

    prepeaks_setup(energy, norm=norm, group=group, emin=emin, emax=emax,
                   elo=elo, ehi=ehi, _larch=_larch)

    emin = group.prepeaks.emin
    emax = group.prepeaks.emax
    elo = group.prepeaks.elo
    ehi = group.prepeaks.ehi

    dele = 1.e-13 + min(np.diff(energy))/5.0

    imin = index_of(energy, emin+dele)
    ilo  = index_of(energy, elo+dele)
    ihi  = index_of(energy, ehi+dele)
    imax = index_of(energy, emax+dele)

    # build xdat, ydat: dat to fit (skipping pre-edge peaks)
    xdat = np.concatenate((energy[imin:ilo+1], energy[ihi:imax+1]))
    ydat = np.concatenate((norm[imin:ilo+1], norm[ihi:imax+1]))

    edat = energy[imin: imax+1]
    cen = dcen = 0.
    peak_energies = []

    # energy including pre-edge peaks, for output
    norm = norm[imin:imax+1]
    baseline = peaks = dpeaks = norm*0.0

    # build fitting model:
    modelcomps = []
    parvals = {}

    MODELDAT = {'gauss': (GaussianModel, dict(amplitude=1, center=emax, sigma=2)),
                'loren': (LorentzianModel, dict(amplitude=1, center=emax, sigma=2)),
                'voigt': (VoigtModel, dict(amplitude=1, center=emax, sigma=2)),
                'line': (LinearModel, dict(slope=0, intercept=0)),
                'quad': (QuadraticModel, dict(a=0, b=0, c=0)),
                'const': (ConstantModel, dict(c=0))}

    if '+' in form:
        forms = [f.lower() for f in form.split('+')]
    else:
        forms = [form.lower(), '']

    for form in forms[:2]:
        for key, dat in MODELDAT.items():
            if form.startswith(key):
                modelcomps.append(dat[0]())
                parvals.update(dat[1])

    if len(modelcomps) == 0:
        group.prepeaks = Group(energy=edat, norm=norm, baseline=0.0*edat,
                               peaks=0.0*edat, delta_peaks=0.0*edat,
                               centroid=0, delta_centroid=0,
                               peak_energies=[],
                               fit_details=None,
                               emin=emin, emax=emax, elo=elo, ehi=ehi,
                               form=form)
        return

    model = modelcomps.pop()
    if len(modelcomps) > 0:
        model += modelcomps.pop()

    params = model.make_params(**parvals)
    if 'amplitude' in params:
        params['amplitude'].min =  0.0
    if 'sigma' in params:
        params['sigma'].min = 0.05
        params['sigma'].max = 500.0
    if 'center' in params:
        params['center'].max = emax + 25.0
        params['center'].min = emin - 25.0

    result = model.fit(ydat, params, x=xdat)

    # get baseline and resulting norm over edat range
    if result is not None:
        baseline = result.eval(result.params, x=edat)
        peaks = norm-baseline

        # estimate centroid
        cen = (edat*peaks).sum() / peaks.sum()

        # uncertainty in norm includes only uncertainties in baseline fit
        # and uncertainty in centroid:
        try:
            dpeaks = result.eval_uncertainty(result.params, x=edat)
        except:
            dbpeaks = 0.0

        cen_plus = (edat*(peaks+dpeaks)).sum()/ (peaks+dpeaks).sum()
        cen_minus = (edat*(peaks-dpeaks)).sum()/ (peaks-dpeaks).sum()
        dcen = abs(cen_minus - cen_plus) / 2.0

        # locate peak positions
        if HAS_PEAKUTILS:
            peak_ids = peakutils.peak.indexes(peaks, thres=0.05, min_dist=2)
            peak_energies = [edat[pid] for pid in peak_ids]

    group = set_xafsGroup(group, _larch=_larch)
    group.prepeaks = Group(energy=edat, norm=norm, baseline=baseline,
                           peaks=peaks, delta_peaks=dpeaks,
                           centroid=cen, delta_centroid=dcen,
                           peak_energies=peak_energies,
                           fit_details=result,
                           emin=emin, emax=emax, elo=elo, ehi=ehi,
                           form=form)
    return


def prepeaks_fit(group, peakmodel, params, user_options=None, _larch=None):
    """do pre-edge peak fitting - must be done after setting up the fit
    returns a group with Peakfit data, including `result`, the lmfit ModelResult

    """
    prepeaks = getattr(group, 'prepeaks', None)
    if prepeaks is None:
        raise ValueError("must run prepeask_setup() for a group before doing fit")

    if not isinstance(peakmodel, Model):
        raise ValueError("peakmodel must be an lmfit.Model")

    if not isinstance(params, Parameters):
        raise ValueError("paramsl must be an lmfit.Parameters")

    if not hasattr(prepeaks, 'fit_history'):
        prepeaks.fit_history = []

    pkfit = Group()

    for k in ('energy', 'norm', 'norm_std', 'user_options'):
        if hasattr(prepeaks, k):
            setattr(pkfit, k, deepcopy(getattr(prepeaks, k)))

    if user_options is not None:
        pkfit.user_options = user_options

    pkfit.init_fit     = peakmodel.eval(params, x=prepeaks.energy)
    pkfit.init_ycomps  = peakmodel.eval_components(params=params, x=prepeaks.energy)

    norm_std = getattr(prepeaks, 'norm_std', 1.0)
    if isinstance(norm_std, np.ndarray):
        norm_std[np.where(norm_std<1.e-13)] = 1.e-13
    elif norm_std < 0:
        norm_std = 1.0

    pkfit.result = peakmodel.fit(prepeaks.norm, params=params, x=prepeaks.energy,
                                 weights=1.0/norm_std)

    pkfit.ycomps = peakmodel.eval_components(params=pkfit.result.params, x=prepeaks.energy)
    pkfit.label = 'Fit %i' % (1+len(prepeaks.fit_history))
    prepeaks.fit_history.insert(0, pkfit)
    return pkfit
