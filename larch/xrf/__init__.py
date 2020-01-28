__DOC__ = '''
X-ray Fluorescence Routines

The functions here include (but are not limited to):

function         description
------------     ------------------------------
create_roi       create an ROI
'''

from .mca import MCA, isLarchMCAGroup, Environment, create_mca
from .roi import ROI, split_roiname, create_roi
from .deadtime import calc_icr, correction_factor
from .xrf_bgr import xrf_background

from .xrf_calib import (xrf_calib_fitrois, xrf_calib_compute,
                        xrf_calib_apply, xrf_calib_init_roi)

from .xrf_peak import xrf_peak
from .xrf_model import xrf_model, xrf_fitresult, FanoFactors

_larch_groups = (ROI, MCA)

_larch_builtins = {'_xrf': dict(create_roi=create_roi,
                                create_mca=create_mca,
                                xrf_model=xrf_model,
                                xrf_fitresult=xrf_fitresult,
                                xrf_peak=xrf_peak,
                                xrf_background=xrf_background,
                                xrf_calib_fitrois=xrf_calib_fitrois,
                                xrf_calib_init_roi=xrf_calib_init_roi,
                                xrf_calib_compute=xrf_calib_compute,
                                xrf_calib_apply=xrf_calib_apply)}
