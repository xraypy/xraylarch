import logging
logging.getLogger('pyFAI').setLevel(logging.CRITICAL)

from .xrd import XRD, xrd1d, read_xrd_data, create_xrd, create_xrd1d, calculate_xvalues
from .xrd_bgr import xrd_background

from .xrd_fitting import (peakfinder, peaklocater, peakfitter, peakfilter,
                          peakfinder_methods, data_gaussian_fit,
                          instrumental_fit_uvw, calc_broadening)

from .xrd_pyFAI import (integrate_xrd, integrate_xrd_row, read_lambda,
                        calc_cake, save1D, return_ai, twth_from_xy,
                        q_from_xy, eta_from_xy)

from .xrd_tools import (d_from_q, d_from_twth, twth_from_d, twth_from_q,
                        E_from_lambda, lambda_from_E, q_from_d,
                        q_from_twth, qv_from_hkl, d_from_hkl,
                        unit_cell_volume, generate_hkl)

from .xrd_cif import (SPACEGROUPS, create_xrdcif, check_elemsym, SPGRP_SYMM)

from .cifdb import (get_cifdb, cifDB, cif_match, read_cif, SearchCIFdb,
                    match_database, CATEGORIES, QSTEP, QMIN, QMAX, QAXIS)

from .amscifdb import CifStructure, get_amscifdb, get_cif, find_cifs

from .xrd_files import xy_file_reader

__DOC_ = '''

Functions for manipulating and analyzing x-ray diffraction
data.

The data and functions here include (but are not limited to):

member name     description
------------    ------------------------------
peakfinder      identifies peaks in x,y data
peakfilter      filters a set of data below a certain threshold
peaklocater     cross-references data for a give coordinates

'''

_larch_name = '_xrd'
_larch_group = (XRD, xrd1d)

_larch_builtins = {'_xrd':  {'d_from_q': d_from_q,
                             'd_from_twth': d_from_twth,
                             'twth_from_d': twth_from_d,
                             'twth_from_q': twth_from_q,
                             'q_from_d': q_from_d,
                             'q_from_twth': q_from_twth,
                             'E_from_lambda': E_from_lambda,
                             'lambda_from_E': lambda_from_E,
                             'generate_hkl': generate_hkl,
                             'xrd_background': xrd_background,
                             'integrate_xrd': integrate_xrd,
                             'cif_match': cif_match,
                             'get_cifdb': get_cifdb,
                             'read_cif': read_cif,
                             'create_xrd': create_xrd,
                             'create_xrd1d': create_xrd1d,
                             'peakfinder': peakfinder,
                             'peakfitter': peakfitter,
                             'peakfilter': peakfilter,
                             'peaklocater': peaklocater,
                             'instrumental_fit_uvw': instrumental_fit_uvw,
                             'xy_file_reader': xy_file_reader,
                             'get_amscifdb': get_amscifdb,
                             'get_cif': get_cif,
                             'find_cifs': find_cifs,
                             }}

#                      'data_gaussian_fit': data_gaussian_fit,
#                      'gaussian': gaussian,
#                      'doublegaussian': doublegaussian,
#                      'poly_func': poly_func,
#                      'data_poly_fit': data_poly_fit
