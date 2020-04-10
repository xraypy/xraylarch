#!/usr/bin/env python
# XAS spectral decovolution
#

import numpy as np
from scipy.signal import deconvolve
from larch import parse_group_args

from larch.math import (gaussian, lorentzian, interp,
                        index_of, index_nearest, remove_dups,
                        savitzky_golay)

from .xafsutils import set_xafsGroup

def xas_deconvolve(energy, norm=None, group=None, form='lorentzian',
                   esigma=1.0, eshift=0.0, smooth=True,
                   sgwindow=None, sgorder=3, _larch=None):
    """XAS spectral deconvolution

    de-convolve a normalized mu(E) spectra with a peak shape, enhancing the
    intensity and separation of peaks of a XANES spectrum.

    The results can be unstable, and noisy, and should be used
    with caution!

    Arguments
    ----------
    energy:   array of x-ray energies (in eV) or XAFS data group
    norm:     array of normalized mu(E)
    group:    output group
    form:     functional form of deconvolution function. One of
              'gaussian' or 'lorentzian' [default]
    esigma    energy sigma to pass to gaussian() or lorentzian()
              [in eV, default=1.0]
    eshift    energy shift to apply to result. [in eV, default=0]
    smooth    whether to smooth result with savitzky_golay method [True]
    sgwindow  window size for savitzky_golay [found from data step and esigma]
    sgorder   order for savitzky_golay [3]

    Returns
    -------
    None
       The array 'deconv' will be written to the output group.

    Notes
    -----
       Support See First Argument Group convention, requiring group
       members 'energy' and 'norm'

       Smoothing with savitzky_golay() requires a window and order.  By
       default, window = int(esigma / estep) where estep is step size for
       the gridded data, approximately the finest energy step in the data.
    """
    energy, mu, group = parse_group_args(energy, members=('energy', 'norm'),
                                         defaults=(norm,), group=group,
                                         fcn_name='xas_deconvolve')
    eshift = eshift + 0.5 * esigma

    en  = remove_dups(energy)
    estep1 = int(0.1*en[0]) * 2.e-5
    en  = en - en[0]
    estep = max(estep1, 0.01*int(min(en[1:]-en[:-1])*100.0))
    npts = 1  + int(max(en) / estep)
    if npts > 25000:
        npts = 25001
        estep = max(en)/25000.0

    x = np.arange(npts)*estep
    y = interp(en, mu, x, kind='cubic')

    kernel = lorentzian
    if form.lower().startswith('g'):
        kernel = gaussian

    yext = np.concatenate((y, np.arange(len(y))*y[-1]))

    ret, err = deconvolve(yext, kernel(x, center=0, sigma=esigma))
    nret = min(len(x), len(ret))

    ret = ret[:nret]*yext[nret-1]/ret[nret-1]
    if smooth:
        if sgwindow is None:
            sgwindow = int(1.0*esigma/estep)

        sqwindow = int(sgwindow)
        if sgwindow < (sgorder+1):
            sgwindow = sgorder + 2
        if sgwindow % 2 == 0:
            sgwindow += 1
        ret = savitzky_golay(ret, sgwindow, sgorder)

    out = interp(x+eshift, ret, en, kind='cubic')
    group = set_xafsGroup(group, _larch=_larch)
    group.deconv = out


def xas_convolve(energy, norm=None, group=None, form='lorentzian',
                   esigma=1.0, eshift=0.0, _larch=None):
    """
    convolve a normalized mu(E) spectra with a Lorentzian or Gaussian peak
    shape, degrading separation of XANES features.

    This is provided as a complement to xas_deconvolve, and to deliberately
    broaden spectra to compare with spectra measured at lower resolution.

    Arguments
    ----------
    energy:   array of x-ray energies (in eV) or XAFS data group
    norm:     array of normalized mu(E)
    group:    output group
    form:     form of deconvolution function. One of
              'lorentzian' or  'gaussian' ['lorentzian']
    esigma    energy sigma (in eV) to pass to gaussian() or lorentzian() [1.0]
    eshift    energy shift (in eV) to apply to result [0]

    Returns
    -------
    None
       The array 'conv' will be written to the output group.

    Notes
    -----
       Follows the First Argument Group convention, using group members named
       'energy' and 'norm'
    """

    energy, mu, group = parse_group_args(energy, members=('energy', 'norm'),
                                         defaults=(norm,), group=group,
                                         fcn_name='xas_convolve')
    eshift = eshift + 0.5 * esigma

    en  = remove_dups(energy)
    en  = en - en[0]
    estep = max(0.001, 0.001*int(min(en[1:]-en[:-1])*1000.0))

    npad = 1 + int(max(estep*2.01, 50*esigma)/estep)

    npts = npad  + int(max(en) / estep)

    x = np.arange(npts)*estep
    y = interp(en, mu, x, kind='cubic')

    kernel = lorentzian
    if form.lower().startswith('g'):
        kernel = gaussian

    k = kernel(x, center=0, sigma=esigma)
    ret = np.convolve(y, k, mode='full')

    out = interp(x-eshift, ret[:len(x)], en, kind='cubic')

    group = set_xafsGroup(group, _larch=_larch)
    group.conv = out / k.sum()
