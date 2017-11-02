"""
Methods for fitting background in energy dispersive xray spectra

"""
from larch import ValidateLarchPlugin
from larch_plugins.xrf import isLarchMCAGroup
from larch_plugins.xray import XrayBackground

@ValidateLarchPlugin
def xrf_background(energy, counts=None, group=None, width=4,
                   compress=2, exponent=2, slope=None,
                   _larch=None):
    """fit background for XRF spectra.  Arguments:

    xrf_background(energy, counts=None, group=None, width=4,
                   compress=2, exponent=2, slope=None)

    Arguments
    ---------
    energy     array of energies OR an MCA group.  If an MCA group,
               it will be used to give ``counts`` and ``mca`` arguments
    counts     array of XRF counts (or MCA.counts)
    group      group for outputs

    width      full width (in keV) of the concave down polynomials
               for when its full width is 100 counts. default = 4

    compress   compression factor to apply to spectra. Default is 2.

    exponent   power of polynomial used.  Default is 2, should be even.
    slope      channel to energy conversion, from energy calibration
               (default == None --> found from input energy array)

    outputs (written to group)
    -------
    bgr       background array
    bgr_info  dictionary of parameters used to calculate background
    """
    if isLarchMCAGroup(energy):
        group  = energy
        counts = group.counts
        energy = group.energy
    if slope is None:
        slope = (energy[-1] - energy[0])/len(energy)

    xbgr = XrayBackground(counts, width=width, compress=compress,
                         exponent=exponent, slope=slope)

    if group is not None:
        group.bgr = xbgr.bgr
        group.bgr_info = xbgr.parinfo

def registerLarchPlugin():
    return ('_xrf', {'xrf_background': xrf_background})
