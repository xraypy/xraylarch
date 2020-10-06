'''
This module defines a functions necessary for tomography calculations.

Authors/Modifications:
----------------------
* Margaret Koker, koker@cars.uchicago.edu
'''

import logging

logger = logging.getLogger(__name__)

import numpy as np
from scipy.optimize import leastsq, minimize

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

def find_tomo_center(sino, omega, center=None, sinogram_order=True):

    xmax = sino.shape[0]
    if sinogram_order:
        xmax = sino.shape[1]
    if center is None:
        center = xmax/2.0

    # init center to scale recon
    rec = tomopy.recon(sino, omega, center=center, sinogram_order=sinogram_order,
                       algorithm='gridrec', filter_name='shepp')
    rec = tomopy.circ_mask(rec, axis=0)

    # tomopy score, tweaked slightly
    rmin, rmax = rec.min(), rec.max()
    rmin  -= 0.5*(rmax-rmin)
    rmax  += 0.5*(rmax-rmin)
    out = minimize(_center_resid_negent, center,
                   args=(sino, omega, rmin, rmax, sinogram_order),
                   method='Nelder-Mead', tol=0.5)
    cen = out.x
    # if cen > 0  and cen < xmax:
    #    out = minimize(_center_resid_blur, cen,
    #                   args=(sino, omega, rmin, rmax, sinogram_order),
    #                   method='Nelder-Mead', tol=0.5)
    #    cen = out.x
    return cen

def _center_resid_negent(center, sino, omega, rmin, rmax, sinogram_order=True):
    """
    Cost function used for the ``find_center`` routine.
    """
    _, nang, nx = sino.shape
    if center < 1:
        return 10*(1-center)
    if center > nx-2:
        return 10*(center-nx+2)
    n1 = int(nx/4.0)
    n2 = int(3*nx/4.0)
    rec = tomopy.recon(sino, omega, center,algorithm='gridrec',
                       sinogram_order=sinogram_order)
    rec = tomopy.circ_mask(rec, axis=0)[:, n1:n2, n1:n2]
    hist, e = np.histogram(rec, bins=64, range=[rmin, rmax])
    hist = hist/rec.size
    score = -np.dot(hist, np.log(1.e-12+hist))
    logger.info("negent center = %.4f  %.4f" % (center, score))
    return score

def _center_resid_blur(center, sino, omega, rmin, rmax, sinogram_order=True):
    """
    Cost function used for the ``find_center`` routine.
    """
    rec = tomopy.recon(sino, omega, center,
                       sinogram_order=sinogram_order,
                       algorithm='gridrec', filter_name='shepp')
    rec = tomopy.circ_mask(rec, axis=0)
    score = -((rec - rec.mean())**2).sum()
    logger.info("blur center = %.4f  %.4f" % (center, score))
    return score

def tomo_reconstruction(sino, omega, algorithm='gridrec',
                        filter_name='shepp', num_iter=1, center=None,
                        refine_center=False, sinogram_order=True):
    '''
    INPUT ->  sino : slice, 2th, x OR 2th, slice, x (with flag sinogram_order=True/False)
    OUTPUT -> tomo : slice, x, y
    '''
    if center is None:
        center = sino.shape[1]/2.

    if refine_center:
        print(">> Refine Center start>> ", center, sinogram_order)
        # center = tomopy.find_center(sino, np.radians(omega), init=center,
        #                            ind=0, tol=0.5, sinogram_order=sinogram_order)

        center = find_tomo_center(sino, np.radians(omega), center=center,
                                  sinogram_order=sinogram_order)
        print(">> Refine Center done>> ", center, sinogram_order)
    algorithm = algorithm.lower()
    recon_kws = {}
    if algorithm.startswith('gridr'):
        recon_kws['filter_name'] = filter_name
    else:
        recon_kws['num_iter'] = num_iter
    tomo = tomopy.recon(sino, np.radians(omega), algorithm=algorithm,
                        center=center, sinogram_order=sinogram_order, **recon_kws)
    return center, tomo
