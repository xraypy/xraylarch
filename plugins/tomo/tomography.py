'''
This module defines a functions necessary for tomography calculations.

Authors/Modifications:
----------------------
* Margaret Koker, koker@cars.uchicago.edu
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import numpy as np

HAS_tomopy = False
try:
    import tomopy
    HAS_tomopy = True
except ImportError:
    pass

HAS_scikit = False
# try:
#     # from skimage.transform import iradon
#     #from skimage.transform import radon, iradon_sart
#     # HAS_scikit = True
# except:
#     pass

# HAS_larch = False
# try:
#     from larch import Group
#     grpobjt = Group
#     HAS_larch = True
# except:
#     grpobjt = object



##########################################################################
# GLOBAL VARIABLES

TOMOPY_ALG = ['gridrec', 'art', 'bart', 'mlem', 'osem', 'ospml_hybrid',
               'ospml_quad', 'pml_hybrid', 'pml_quad', 'sirt' ]

TOMOPY_FILT = ['shepp', 'ramlak', 'butterworth','parzen', 'cosine', 'hann',
               'hamming', 'None']


SCIKIT_FILT = ['shepp-logan', 'ramp','cosine', 'hamming', 'hann', 'None' ]
SCIKIT_INTR = ['linear', 'nearest', 'cubic']

PIXEL_TRIM = 10

##########################################################################
# FUNCTIONS

def check_method(method):

    if method is None:
        if HAS_tomopy:
            method = 'tomopy'
        elif HAS_scikit:
            method = 'scikit-image'
    return method

def return_methods():
    alg0, alg1, alg2 = [], [], []
    if HAS_tomopy:
        alg0 += ['tomopy']
        alg1 += [TOMOPY_ALG]
        alg2 += [TOMOPY_FILT]
    if HAS_scikit:
        alg0 += ['scikit-image']
        alg1 += [SCIKIT_FILT]
        alg2 += [SCIKIT_INTR]

    if len(alg0) < 1:
        return [''],[['']],[['']]

    return alg0,alg1,alg2

def check_parameters(sino, algorithm,  center, omega, sinogram_order):

    if type(tomo_alg) is str: tomo_alg = [tomo_alg]
    try:
        if len(tomo_alg) > 3: tomo_alg = tomo_alg[:3]
    except:
        tomo_alg = [tomo_alg]

    while len(tomo_alg) < 3:
        tomo_alg += [None]

    tomo_alg[0] = check_method(tomo_alg[0])

    if len(np.shape(sino)) == 2:
        sino.resize((1, sino.shape[0], sino.shape[1]))
        sinogram_order = True

    if center is None: center = sino.shape[1]/2.
    if omega is None:
        if sinogram_order:
            omega = np.linspace(0,360,sino.shape[1])
        else:
            omega = np.linspace(0,360,sino.shape[0])

    if tomo_alg[0].lower().startswith('scikit') and HAS_scikit:
        if tomo_alg[1] == 'None':
            tomo_alg[1] = None
        elif tomo_alg[1] not in SCIKIT_FILT:
            tomo_alg[1] = 'shepp-logan'
        if tomo_alg[2] not in SCIKIT_INTR:
            tomo_alg[2] = 'linear'
        npts = sino.shape[1]

    elif tomo_alg[0].lower().startswith('tomopy') and HAS_tomopy:

        if tomo_alg[1] not in TOMOPY_ALG:
            tomo_alg[1] = 'gridrec'
        if tomo_alg[2] not in TOMOPY_FILT or tomo_alg[2] == 'None':
            tomo_alg[2] = None

    return sino, center, omega, tomo_alg, sinogram_order

def reshape_sinogram(A,x=[],omega=[]):

    ## == INPUTS ==
    ## A              :    array from .get_roimap()
    ## x              :    x array for checking shape of A
    ## omega          :    omega array for checking shape of A
    ##
    ## == RETURNS ==
    ## A              :    A in shape/format needed for tomopy reconstruction
    ## sinogram_order :  flag/argument for tomopy reconstruction (shape dependent)

    A = np.array(A)
    if len(x) == len(omega):
        print('''Cannot reorder sinogram based on length of positional
                 arrays when same length. Acceptable orders:
                 sinogram_order = False : sino = [ 2th   , slice, X ]
                 sinogram_order = True  : sino = [ slice , 2th  , X ]''')
        return A,False
    if len(x) < 1 or len(omega) < 1:
        return A,False
    if len(A.shape) != 3:
       if len(A.shape) == 2:
           A = A.reshape(1,A.shape[0],A.shape[1])

    if len(A.shape) == 3:
        if len(x) == A.shape[0]:
             A = np.einsum('kij->ijk', A)
        if len(x) == A.shape[1]:
             A = np.einsum('ikj->ijk', A)
    sinogram_order = len(omega) == A.shape[1]

    return A,sinogram_order

def trim_sinogram(sino,x,omega,pixel_trim=None):

    if pixel_trim is None: pixel_trim = PIXEL_TRIM

    if len(omega) == sino.shape[-1]:
        omega = omega[pixel_trim:-1*(pixel_trim+1)]
    elif len(x) == sino.shape[-1]:
        x = x[pixel_trim:-1*(pixel_trim+1)]

    sino = sino[:,pixel_trim:-1*(pixel_trim+1)]

    return sino,x,omega

def tomo_reconstruction(sino, omega, algorithm='gridrec',
                        filter_name='shepp', num_iter=1, center=None,
                        refine_center=False, sinogram_order=True):

    '''
    INPUT ->  sino : slice, 2th, x OR 2th, slice, x (with flag sinogram_order=True/False)
    OUTPUT -> tomo : slice, x, y
    '''
    # check = check_parameters(sino, center, omega, tomo_alg, sinogram_order)
    # sino, center, omega, tomo_alg, sinogram_order = check
    if center is None:
        center = sino.shape[1]/2.
        refine_center = True

    if refine_center:
        center = tomopy.find_center(sino, np.radians(omega), init=center,
                                    ind=0, tol=0.5, sinogram_order=sinogram_order)

    algorithm = algorithm.lower()
    recon_kws = {}
    if algorithm.startswith('gridr'):
        recon_kws['filter_name'] = filter_name
    else:
        recon_kws['num_iter'] = num_iter
    tomo = tomopy.recon(sino, np.radians(omega), algorithm=algorithm,
                        center=center, sinogram_order=sinogram_order, **recon_kws)
    return center, tomo

# def registerLarchPlugin():
#     return ('_tomo', {'create_tomogrp': create_tomogrp})
#
#
# def registerLarchGroups():
#     return (tomogrp)
