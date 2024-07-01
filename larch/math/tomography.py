'''
This module defines a functions necessary for tomography calculations.

Authors/Modifications:
----------------------
* Margaret Koker, koker@cars.uchicago.edu
'''

import logging
logger = logging.getLogger(__name__)
logger.level = logging.ERROR
logger = logging.getLogger('tomopy.recon')
logger.level = logging.ERROR

import numpy as np
from scipy.optimize import leastsq, minimize

HAS_tomopy = False
try:
    import tomopy
    HAS_tomopy = True
except ImportError:
    pass

TAU = 2.0 * np.pi

# GLOBAL VARIABLES
TOMOPY_ALG = ['gridrec', 'art', 'bart', 'mlem', 'osem', 'ospml_hybrid',
              'ospml_quad', 'pml_hybrid', 'pml_quad', 'sirt' ]

TOMOPY_FILT = ['shepp', 'ramlak', 'butterworth','parzen', 'cosine', 'hann',
               'hamming', 'None']

def ensure_radians(a):
    """ensure angle data is in radians, not degrees,
    converts degrees to radians if a peak-to-peak > 32 or step size > 0.2
    """
    if np.ptp(a) > 32 or np.diff(a).mean() > 0.20:
        a = np.radians(a)
    return a


def reshape_sinogram(A, x, omega):

    ## == INPUTS ==
    ## A              :    array from .get_roimap()
    ## x              :    x array for checking shape of A
    ## omega          :    omega array for checking shape of A
    ##
    ## == RETURNS ==
    ## A              :    A in shape/format needed for tomopy reconstruction
    ## sinogram_order :  flag/argument for tomopy reconstruction (shape dependent)

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

    return A, sinogram_order

def trim_sinogram(sino, x, omega, pixel_trim=10):
    if len(omega) == sino.shape[-1]:
        omega = omega[pixel_trim:-1*(pixel_trim+1)]
    elif len(x) == sino.shape[-1]:
        x = x[pixel_trim:-1*(pixel_trim+1)]

    sino = sino[:,pixel_trim:-1*(pixel_trim+1)]

    return sino, x, omega

def find_tomo_center(sino, omega, center=None, tol=0.25, blur_weight=2.0,
                     sinogram_order=True):

    """find rotation axis center for a sinogram,
    mixing negative entropy (as tomopy uses) and other focusing scores

    Arguments
    ---------
    sino : ndarray for sinogram
    omega: ndarray of angles in radians
    center: initial value for center [mid-point]
    tol:    fit tolerance for center pixel [0.25]
    sinogram_order: bool for axis order of sinogram

    Returns
    -------
    pixel value for refined center

    Notes
    ------

     The algormithm combines a few focusing scores from Y. Sun, S. Duthaler, and B. Nelson,
     MICROSCOPY RESEARCH AND TECHNIQUE 65:139–149 (2004) (doi: 10.1002/jemt.20118a)

    For a reconstructed image `img` the variance is calculated as

       blur = -((img - img.mean())**2).sum()/img.size

    and is combined with negative-entropy is calculated as
       ioff = (img.max() - img.min())/25.0
       imin = img.min() - ioff
       imax = img.max() + ioff
       hist, _ = np.histogram(img, bins=512, range=[imin, imax])
       hist =  hist/(2*(imax-imin))
       hist[np.where(hist==0)] = 1.e-20
       negent = -np.dot(hist, np.log(hist))


    """
    xmax = sino.shape[0]
    if sinogram_order:
        xmax = sino.shape[2]
    if center is None:
        center = xmax/2.0

    omega = ensure_radians(omega)

    img = tomopy.recon(sino, omega, center,
                       sinogram_order=sinogram_order,
                       algorithm='gridrec', filter_name='shepp')
    img = tomopy.circ_mask(img, axis=0)
    ioff = (img.max() - img.min())/25.0
    imin = img.min() - ioff
    imax = img.max() + ioff

    out = minimize(center_score, center, method='Nelder-Mead', tol=tol,
                   args=(sino, omega, blur_weight, sinogram_order, imin, imax))
    return out.x[0]

def center_score(center, sino, omega, blur_weight=2.0, sinogram_order=True,
                  imin=None, imax=None, verbose=False):
    """Cost function used for the ``find_center`` routine:
    combines a few focusing scores from
    Y. Sun, S. Duthaler, and B. Nelson,
    MICROSCOPY RESEARCH AND TECHNIQUE 65:139–149 (2004)
    (doi: 10.1002/jemt.20118a)

       name   formula in paper   python

        blur (F 10)  -((img - img.mean())**2).sum()/img.size

     negent is calculated as
        hist, _ = np.histogram(img, bins=512, range=[imin, imax])
        hist =  hist/(2*(imax-imin))
        hist[np.where(hist==0)] = 1.e-20
        negent = -np.dot(hist, np.log(hist))

    """
    ns, nang, nx = sino.shape
    if isinstance(center, (list, tuple, np.ndarray)):
        center = center[0]

    img = tomopy.recon(sino, ensure_radians(omega), center,
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
    try:
        hist, _ = np.histogram(img, bins=512, range=[imin, imax])
        hist =  hist/(2*(imax-imin))
        hist[np.where(hist==0)] = 1.e-20
        negent = -np.dot(hist, np.log(hist))
    except:
        negent = blur
    if verbose:
        print("Center %.3f %13.5g, %13.5g" % (center, blur, negent))
    return blur*blur_weight + negent


def tomo_reconstruction(sino, omega, algorithm='gridrec',
                        filter_name='shepp', num_iter=1, center=None,
                        refine_center=False, sinogram_order=True):
    '''
    INPUT ->  sino : slice, 2th, x OR 2th, slice, x (with flag sinogram_order=True/False)
    OUTPUT -> tomo : slice, x, y
    '''
    if center is None:
        center = sino.shape[1]/2.

    x = tomopy.init_tomo(sino, sinogram_order)
    nomega = len(omega)
    ns, nth, nx = sino.shape
    if nth > nomega:
        sino = sino[:, :nomega, :]
    romega = ensure_radians(omega)

    if refine_center:
        center = find_tomo_center(sino, romega, center=center,
                                  sinogram_order=sinogram_order)
        print(">> Refine Center done>> ", center, sinogram_order)
    algorithm = algorithm.lower()
    recon_kws = {}
    if algorithm.startswith('gridr'):
        recon_kws['filter_name'] = filter_name
    else:
        recon_kws['num_iter'] = num_iter

    tomo = tomopy.recon(sino, romega, algorithm=algorithm,
                        center=center, sinogram_order=sinogram_order, **recon_kws)
    return center, tomo*(sino.mean()/tomo.mean())
