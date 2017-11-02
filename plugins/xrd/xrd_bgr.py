"""
Methods for fitting background x-ray diffraction data

"""
from larch import ValidateLarchPlugin
from larch_plugins.xray import XrayBackground

# @ValidateLarchPlugin
def xrd_background(xdata, ydata, width=4, compress=5, exponent=2, slope=None): #,_larch=None):
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
    -------
    bgr       background array
    bgr_info  dictionary of parameters used to calculate background
    """
   
    if slope is None:
        slope = (xdata[-1] - xdata[0])/len(xdata)

    xbgr = XrayBackground(ydata, width=width, compress=compress,
                         exponent=exponent, slope=slope, tangent=True,
                         type_int=False, data_type='xrd')

    return xbgr.bgr

# def registerLarchPlugin():
#     return ('_xrd', {'xrd_background': xrd_background})
