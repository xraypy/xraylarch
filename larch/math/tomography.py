'''
This module defines a functions necessary for tomography calculations.

Authors/Modifications:
----------------------
* Margaret Koker, koker@cars.uchicago.edu
'''
import numpy as np

HAS_tomopy = False
try:
    import tomopy
    HAS_tomopy = True
except ImportError:
    pass

# GLOBAL VARIABLES
TOMOPY_ALG = ['gridrec', 'art', 'bart', 'mlem', 'osem', 'ospml_hybrid',
              'ospml_quad', 'pml_hybrid', 'pml_quad', 'sirt' ]

TOMOPY_FILT = ['shepp', 'ramlak', 'butterworth','parzen', 'cosine', 'hann',
               'hamming', 'None']

PIXEL_TRIM = 10

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
