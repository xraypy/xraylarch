#/usr/bin/env python
"""
XRF Calibration routines
"""

import numpy as np
from collections import OrderedDict
from lmfit.models import GaussianModel, ConstantModel

from xraydb import xray_line

from ..math import index_of, linregress, fit_peak
from .roi import split_roiname
from .mca import isLarchMCAGroup

def xrf_calib_init_roi(mca, roiname):
    """initial calibration step for MCA:
    find energy locations for one ROI
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
    if not hasattr(mca, 'init_calib'):
        mca.init_calib = OrderedDict()

    roi = None
    for xroi in mca.rois:
        if xroi.name == roiname:
            roi = xroi
            break
    if roi is None:
        return
    words = roiname.split()
    elem = words[0].title()
    family = 'Ka'
    if len(words) > 1:
        family = words[1].title()
    if family == 'Lb':
        family = 'Lb1'
    try:
        eknown = xray_line(elem, family).energy/1000.0
    except:
        eknown = 0.001
    llim = max(0, roi.left - roi.bgr_width)
    hlim = min(len(chans)-1, roi.right + roi.bgr_width)
    segcounts = counts[llim:hlim]
    maxcounts = max(segcounts)
    ccen = llim + np.where(segcounts==maxcounts)[0][0]
    ecen = ccen * mca.slope + mca.offset
    bkgcounts = counts[llim] + counts[hlim]
    if maxcounts < 2*bkgcounts:
        mca.init_calib[roiname] = (eknown, ecen, 0.0, ccen, None)
    else:
        model = GaussianModel() + ConstantModel()
        params = model.make_params(amplitude=maxcounts,
                                   sigma=(chans[hlim]-chans[llim])/2.0,
                                   center=ccen-llim, c=0.00)
        params['center'].min = -10
        params['center'].max = hlim - llim + 10
        params['c'].min = -10
        out = model.fit(counts[llim:hlim], params, x=chans[llim:hlim])
        ccen = llim + out.params['center'].value
        ecen = ccen * mca.slope + mca.offset
        fwhm = out.params['fwhm'].value * mca.slope
        mca.init_calib[roiname] = (eknown, ecen, fwhm, ccen, out)


def xrf_calib_fitrois(mca):
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
            eknown = xray_line(elem, family).energy/1000.0
        except:
            continue
        llim = max(0, roi.left - roi.bgr_width)
        hlim = min(len(chans)-1, roi.right + roi.bgr_width)
        fit = fit_peak(chans[llim:hlim], counts[llim:hlim],
                       'Gaussian', background='constant')


        ccen = fit.params['center'].value
        ecen = ccen * mca.slope + mca.offset
        fwhm = 2.354820 * fit.params['sigma'].value * mca.slope
        calib[roi.name] = (eknown, ecen, fwhm, ccen, fit)
    mca.init_calib = calib

def xrf_calib_compute(mca, apply=False):
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
        xrf_calib_fitrois(mca)

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

def xrf_calib_apply(mca, offset=None, slope=None):
    """apply calibration to MCA

    either supply offset and slope arguments (in keV and keV/chan)
    or run xrf_calib_compute(mca) to estimate these from ROI peaks
    """
    # print(" xrf calib apply ", mca, mca.offset, mca.slope, offset, slope)
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
    mca.energy = (offset + slope*np.arange(npts))
