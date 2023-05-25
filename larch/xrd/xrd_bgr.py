"""
Methods for fitting background x-ray diffraction data

"""
from ..xray import XrayBackground

def xrd_background(xdata, ydata, width=4, compress=5, exponent=2, slope=None):
    """fit background for XRF spectra.  Arguments:

    xrd_background(xdata, ydata, group=None, width=4,
                   compress=2, exponent=2, slope=None)

    Arguments
    ---------
    xdata     array of q values (or 2th, d?)

    ydata     associated array of I values

    group     group for outputs

    width      full width of the concave down polynomials
               for when its full width is 100 counts.

    compress   compression factor to apply to spectra.

    exponent   power of polynomial used.  Should be even.

    slope      channel to energy conversion, from energy calibration
               (default == None --> found from input energy array)

    Returns
    -------
    bgr       background array
    """

    if slope is None:
        slope = (xdata[-1] - xdata[0])/len(xdata)
    bgr = ydata*1.0

    xb = XrayBackground(ydata, width=width, compress=compress,
                        exponent=exponent, slope=slope, tangent=True)
    bgr[:len(xb.bgr)] = xb.bgr
    return bgr
