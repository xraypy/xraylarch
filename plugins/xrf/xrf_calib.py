#/usr/bin/env python
"""
XRF Calibration routines
"""

import numpy as np
from larch import ValidateLarchPlugin

try:
    from collections import OrderedDict
except ImportError:
    from larch.utils import OrderedDict

from larch_plugins.xrf import isLarchMCAGroup
from larch_plugins.xrf import split_roiname

from larch_plugins.math import index_of, linregress, fit_peak
from larch_plugins.xray import xray_line, xray_lines

def xrf_calib_fitrois(mca, _larch=None):
    """initial calibration step for MCA:
    find energy locations for all ROIs

    """
    if not isLarchMCAGroup(mca):
        print( 'Not a valid MCA')
        return

    energy = 1.0*mca.energy
    chans = 1.0*np.arange(len(energy))
    counts = mca.counts
    bgr = getattr(mca, 'bgr', None)
    if bgr is not None:
        counts = counts - bgr
    calib = OrderedDict()
    for roi in mca.rois:
        words = roi.name.split()
        elem = words[0].title()
        family = 'ka'
        if len(words) > 1:
            family = words[1]
        try:
            eknown = xray_line(elem, family, _larch=_larch)[0]/1000.0
        except:
            continue
        llim = max(0, roi.left - roi.bgr_width)
        hlim = min(len(chans)-1, roi.right + roi.bgr_width)
        fit = fit_peak(chans[llim:hlim], counts[llim:hlim],
                       'Gaussian', background='constant',
                       _larch=_larch)

        ccen = fit.params.center.value
        ecen = ccen * mca.slope + mca.offset
        fwhm = 2.354820 * fit.params.sigma.value * mca.slope
        calib[roi.name] = (eknown, ecen, fwhm, ccen, fit)
    mca.init_calib = calib

def xrf_calib_compute(mca, apply=False, _larch=None):
    """compute linear energy calibration
    from init_calib dictionary found from xrf_calib_fitrois()

    To exclude lines from the calibration, first run
     >>> xrf_calib_fitrois(mca)
    then remove items (by ROI name) from the mca.init_calib dictionay

    """
    if not isLarchMCAGroup(mca):
        print( 'Not a valid MCA')
        return
    if not hasattr(mca, 'init_calib'):
        xrf_calib_fitrois(mca, _larch=_larch)

    # current calib
    offset, slope = mca.offset, mca.slope
    x = np.array([c[3] for c in mca.init_calib.values()])
    y = np.array([c[0] for c in mca.init_calib.values()])
    _s, _o, r, p, std = linregress(x, y)

    mca.new_calib = (_o, _s)
    mca.cal_x = x
    mca.cal_y = y

    if apply:
        xrf_calib_apply(mca, offset=_o, slope=_s)

def xrf_calib_apply(mca, offset=None, slope=None, _larch=None):
    """apply calibration to MCA

    either supply offset and slope arguments (in keV and keV/chan)
    or run xrf_calib_compute(mca) to estimate these from ROI peaks
    """
    if not isLarchMCAGroup(mca):
        print( 'Not a valid MCA')
        return
    if (offset is None or slope is None) and not hasattr(mca, 'new_calib'):
        print( 'must supply offset and slope or run xrf_calib_compute()!')
        return

    if (offset is None or slope is None):
        offset, slope = mca.new_calib
    mca.offset = offset
    mca.slope = slope
    npts = len(mca.energy)
    mca.energy = offset + slope*np.arange(npts)

def registerLarchPlugin():
    return ('_xrf', {'xrf_calib_fitrois': xrf_calib_fitrois,
                     'xrf_calib_compute': xrf_calib_compute,
                     'xrf_calib_apply': xrf_calib_apply})
