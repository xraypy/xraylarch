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
    tcounts[np.where(tcounts<0.01)] = 0.01

    bgr = -1.0*np.ones(nchans)

    # use 1% of 99% percentile of counts as height at which
    # the polynomial should have full width = width
    max_count = np.percentile(tcounts, [99])[0]

    indices = np.linspace(-nchans, nchans, 2*nchans+1) * (2.0 * slope / width)
    polynom = 0.01 * max_count * indices**exponent
    polynom = np.compress((polynom <= max_count), polynom)
    max_index = int(len(polynom)/2 - 1)
    for chan in range(nchans-1):
       chan0  = max((chan - max_index), 0)
       chan1  = min((chan + max_index), (nchans-1))
       chan1  = max(chan1, chan0) + 1
       idx0   = chan0 - chan + max_index
       idx1   = chan1 - chan + max_index
       offset = tcounts[chan] - polynom[idx0:idx1]
       test   = tcounts[chan0:chan1] - offset
       bgr[chan0:chan1] = np.maximum(bgr[chan0:chan1],
                                       min(test)+offset)

    bgr[np.where(bgr <= 0)] = 0.0

    if group is not None:
        group.bgr = bgr
        group.bgr_info = dict(width=width, exponent=exponent)
