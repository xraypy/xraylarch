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
        print("Warning: guessing that 2nd axis is omega")
        # Cannot reorder sinogram based on length of positional
        #         arrays when same length. Acceptable orders:
        #         sinogram_order = False : sino = [ 2th   , slice, X ]
        #         sinogram_order = True  : sino = [ slice , 2th  , X ]''')
        if len(A.shape) == 2:
           A = A.reshape(1, A.shape[0], A.shape[1])
        return A, True

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

def find_tomo_center(sino, omega, center=None, tol=0.25, blur_weight=1.0,
                     sinogram_order=True):
    """find rotation axis center for a sinogram,
    mixing negative entropy (as tomopy uses) and a simple "blur" score

    Arguments
    ---------
    sino : ndarray for sinogram
    omega: ndarray of angles in radians
    center: initial value for center [mid-point]
    tol:    fit tolerance for center pixel [0.25]
    blur_weight: weight to apply to `blur` score relative to negative entropy [1.0]
    sinogram_order: bool for axis order of sinogram

    Returns
    -------
    pixel value for refined center

    Notes
    ------

    For a reconstructed image `img` with a particular value for center,

       blur = -((img - img.mean())**2).sum()/img.size

    and negative-entropy is calculated as
       ioff = (img.max() - img.min())/25.0
       imin = img.min() - ioff
       imax = img.max() + ioff
       hist, _ = np.histogram(img, bins=512, range=[imin, imax])
       hist =  hist/(2*(imax-imin))
       hist[np.where(hist==0)] = 1.e-20
       negent = -np.dot(hist, np.log(hist))

    the "cost" to be minimized to set the center is then

       blur_weight*blur + negent

    """
    xmax = sino.shape[0]
    if sinogram_order:
        xmax = sino.shape[2]
    if center is None:
        center = xmax/2.0

    img = tomopy.recon(sino, omega, center,
                       sinogram_order=sinogram_order,
                       algorithm='gridrec', filter_name='shepp')
    img = tomopy.circ_mask(img, axis=0)
    ioff = (img.max() - img.min())/25.0
    imin = img.min() - ioff
    imax = img.max() + ioff

    out = minimize(_center_resid, center, method='Nelder-Mead', tol=tol,
                   args=(sino, omega, blur_weight, sinogram_order, imin, imax))
    return out.x[0]

def _center_resid(center, sino, omega, blur_weight=1, sinogram_order=True,
                  imin=None, imax=None, allout=False):
    """
    Cost function used for the ``find_center`` routine:
    combines "blur" and "negative entropy"
    """
    ns, nang, nx = sino.shape
    img = tomopy.recon(sino, omega, center,
                       sinogram_order=sinogram_order,
                       algorithm='gridrec', filter_name='shepp')
    img = tomopy.circ_mask(img, axis=0)
    blur = -((img - img.mean())**2).sum()/img.size

    if imin is None or imax is None:
        ioff = (img.max() - img.min())/25.0
        if imin is None:
            imin = img.min() - ioff
        if imax is None:
            imax = img.max() + ioff

    hist, _ = np.histogram(img, bins=512, range=[imin, imax])
    hist =  hist/(2*(imax-imin))
    hist[np.where(hist==0)] = 1.e-20
    negent = -np.dot(hist, np.log(hist))
    score = blur_weight*blur + negent
    if allout: return blur_weight*blur + negent, blur, negent
    return score


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
