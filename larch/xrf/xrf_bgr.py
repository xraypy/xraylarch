"""
Methods for fitting background in energy dispersive xray spectra

"""
import numpy as np
from .mca import isLarchMCAGroup

def xrf_background(energy, counts=None, group=None, width=None, exponent=2, **kws):
    """fit background for XRF spectra.

    xrf_background(energy, counts=None, group=None, exponent=2)

    Arguments
    ---------
    energy     array of energies OR an MCA group.  If an MCA group,
               it will be used to give ``counts`` and ``mca`` arguments
    counts     array of XRF counts (or MCA.counts)
    group      group for outputs

    width      full width (in keV) of the concave down polynomials when its
               value is ~1% of max counts.  Default width is (energy range)/4.0
    exponent   power of polynomial used.  Default is 2, should be even.

    Outputs (written to group)
    -------
    bgr       background array
    bgr_info  dictionary of parameters used to calculate background
    """
    if isLarchMCAGroup(energy):
        group  = energy
        energy = group.energy
        if counts is None:
            counts = group.counts

    nchans = len(counts)
    slope = energy[1] - energy[0]
    if width is None:
        width = max(energy)/4.0

    tcounts = 1.0 * counts
    tcounts[np.where(tcounts<1.e-12)] = 1.e-12

    bgr = 0*counts

    # use 99% percentile of counts as height at which
    # the polynomial should have full width = width
    max_count = np.percentile(tcounts, [99])[0]
    indices = np.linspace(-nchans, nchans, 2*nchans+1) * (2.0 * slope / width)
    polynom = 0.01 * max_count * indices**exponent
    polynom = np.compress((polynom <= max_count), polynom)
    max_index = int(len(polynom)/2 - 1)
    nx = int(len(polynom)/2)

    ch0 = np.arange(nchans) + 1 - nx
    ch0[np.where(ch0  < 0)] = 0

    ch1 = np.arange(nchans) + nx
    ch1[np.where(ch1 > nchans)] = nchans

    ix1 = np.linspace(nx-1, nx-nchans, nchans, dtype='i4')
    ix1[np.where(ix1 < 0)] = 0

    ix2 = np.linspace(nx+nchans-1, nx, nchans, dtype='i4')
    ix2[np.where(ix2 > (2*nx-1))] = 2*nx-1

    for chan in range(nchans-1):
       c0, c1, i0, i1 = ch0[chan], ch1[chan], ix1[chan], ix2[chan]
       offset = tcounts[chan] - polynom[i0:i1]
       tmax = offset + min(tcounts[c0:c1] - offset)
       bgr[c0:c1] = np.maximum(bgr[c0:c1], tmax)

    bgr[np.where(bgr < 0)] = 0.0
    bgr[np.where(counts < 1)] = 0.0

    if group is not None:
        group.bgr = bgr
        group.bgr_info = dict(width=width, exponent=exponent)
