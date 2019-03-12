import logging
logging.getLogger('pyFAI').setLevel(logging.CRITICAL)

from .xrd import XRD, xrd1d, read_xrd_data
from .xrd_bgr import xrd_background

from .xrd_fitting import (peakfinder, peaklocater, peakfitter, peakfilter,
                          peakfinder_methods, data_gaussian_fit,
                          instrumental_fit_uvw, calc_broadening)

from .xrd_pyFAI import (integrate_xrd, integrate_xrd_row, read_lambda, calc_cake,
                        save1D, return_ai, twth_from_xy, q_from_xy, eta_from_xy)

from .xrd_tools import (d_from_q, d_from_twth, twth_from_d, twth_from_q,
                        E_from_lambda, lambda_from_E, q_from_d,
                        q_from_twth, qv_from_hkl, d_from_hkl,
                        unit_cell_volume, generate_hkl)

from .xrd_cif import (SPACEGROUPS, create_cif, check_elemsym, SPGRP_SYMM)
from .cifdb import (get_cifdb, cifDB, SearchCIFdb, match_database,
                    CATEGORIES, QSTEP, QMIN, QMAX, QAXIS)

MODDOC = '''

Functions for manipulating and analyzing x-ray diffraction
data.

The data and functions here include (but are not limited to):

member name     description
------------    ------------------------------
peakfinder      identifies peaks in x,y data
peakfilter      filters a set of data below a certain threshold
peaklocater     cross-references data for a give coordinates

'''

def initializeLarchPlugin(_larch=None):
   ''' initialize xrd '''
   if _larch is not None:
       cdb = get_cifdb(_larch=_larch)
       # mod = getattr(_larch.symtable, '_xrd')
       # mod.__doc__ = MODDOC


def registerLarchPlugin():
    return ('_xrd', {'d_from_q': d_from_q,
                     'd_from_twth': d_from_twth,
                     'twth_from_d': twth_from_d,
                     'twth_from_q': twth_from_q,
                     'q_from_d': q_from_d,
                     'q_from_twth': q_from_twth,
                     'E_from_lambda': E_from_lambda,
                     'lambda_from_E': lambda_from_E,
                     'generate_hkl': generate_hkl,
                      })
# def registerLarchPlugin():
#     return ('_xrd', {'xrd_background': xrd_background})
# def registerLarchPlugin():
#     return ('_xrd', {'integrate_xrd': integrate_xrd}) #,'calculate_ai': calculate_ai})


#
# def registerLarchPlugin():
#     return ('_xray', {'cif_match': cif_match,
#                       'get_cifdb': get_cifdb,
#                       'read_cif': read_cif})

# def registerLarchPlugin():
#     return ('_xrd', {'create_xrd': create_xrd, 'create_xrd1d': create_xrd1d})
#
#
# def registerLarchGroups():
#     return (XRD,xrd1d)
#
#
# def registerLarchPlugin():
#     return ('_xrd', {'peakfinder': peakfinder,
#                      'peakfitter': peakfitter,
#                      'peakfilter': peakfilter,
#                      'peaklocater': peaklocater,
#                      'data_gaussian_fit': data_gaussian_fit,
#                      'gaussian': gaussian,
#                      'doublegaussian': doublegaussian,
#                      'instrumental_fit_uvw': instrumental_fit_uvw,
#                      'poly_func': poly_func,
#                      'data_poly_fit': data_poly_fit
#                       })

# def registerLarchPlugin():
#     return ('_xrd', {'xy_file_reader': xy_file_reader})
