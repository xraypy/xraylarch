#/usr/bin/env python
"""
XRF Calibration routines
"""

import numpy as np
from collections import OrderedDict

import larch
larch.use_plugin_path('xrf')
from mca import isLarchMCAGroup
from roi import split_roiname

larch.use_plugin_path('math')

from mathutils import index_of, linregress
from fitpeak import fit_peak

larch.use_plugin_path('xray')
from xraydb_plugin import xray_lines

def xray_line_mean(elem, family, _larch=None):
    """return mean X-ray line energy (weighted by sub-line strengths
    for a family 'ka', 'lb', ...
    """
    scale = 1.e-99
    value = 0.0
    lines = xray_lines(elem, _larch=_larch)    
    if family in ('ka', 'kb', 'la', 'lb', 'lg'):
        for key, val in lines.items():
            if key.lower().startswith(family):
                value += val[0]*val[1]
                scale += val[1]
    return value/scale

def xrf_calib_fitrois(mca, _larch=None):
    """initial calibration step for MCA:
    find energy locations for all ROIs

    """
    if not isLarchMCAGroup(mca):
        print 'Not a valid MCA'
        return
    
    energy = 1.0*mca.energy
    counts = mca.counts
    if hasattr(mca, 'bgr'):
        counts = counts - mca.bgr
    calib = OrderedDict()
    for roi in mca.rois:
        elem, line = split_roiname(roi.name)
        try:
            eknown = xray_lines(elem, _larch=_larch)[line][0]/1000.0
        except:
            continue

        llim = max(0, roi.left - roi.bgr_width)
        hlim = min(len(energy)-1, roi.right + roi.bgr_width)
        fit = fit_peak(energy[llim:hlim], counts[llim:hlim],
                       'Gaussian', background=None,
                       _larch=_larch)
        
        ecen = fit.params.center.value
        fwhm = fit.params.fwhm.value
        amp  = fit.params.amplitude.value
        calib[roi.name] = (eknown, ecen, fwhm, amp)
    mca.init_calib = calib

def xrf_calib_compute(mca, apply=False, _larch=None):
    """compute linear energy calibration
    from init_calib dictionary found from xrf_calib_fitrois()

    To exclude lines from the calibration, first run
     >>> xrf_calib_fitrois(mca)
    then remove items (by ROI name) from the mca.init_calib dictionay
    
    """
    if not isLarchMCAGroup(mca):
        print 'Not a valid MCA'
        return
    if not hasattr(mca, 'init_calib'):
        xrf_calib_fitrois(mca, _larch=_larch)

    # current calib
    offset, slope = mca.offset, mca.slope 
    x, y = [], []
    for cal in mca.init_calib.values():
        x.append((cal[0] - offset)/slope) 
        y.append(cal[1])
        
    _s, _o, r, p, std = linregress(np.array(x), np.array(y))
    mca.new_calib = (_o, _s)
    if apply:
        xrf_calib_apply(mca, offset=_o, slope=_s)

def xrf_calib_apply(mca, offset=None, slope=None, _larch=None):
    """apply calibration to MCA
    
    either supply offset and slope arguments (in keV and keV/chan)
    or run xrf_calib_compute(mca) to estimate these from ROI peaks
    """
    if not isLarchMCAGroup(mca):
        print 'Not a valid MCA'
        return
    if (offset is None or slope is None) and not hasattr(mca, 'new_calib'):
        print 'must supply offset and slope or run xrf_calib_compute()!'
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
                     'xrf_calib_apply': xrf_calib_apply,
                     'xray_line_mean': xray_line_mean})
