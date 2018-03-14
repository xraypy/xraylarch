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
try:
    from skimage.transform import iradon
    #from skimage.transform import radon, iradon_sart
    HAS_scikit = True
except:
    pass

# HAS_larch = False
# try:
#     from larch import Group
#     grpobjt = Group
#     HAS_larch = True
# except:
#     grpobjt = object



##########################################################################
# GLOBAL VARIABLES

TOMOPY_ALG  = [ 'gridrec', 'art', 'bart', 'fbp', 'mlem', 'osem', 'ospml_hybrid',
                'ospml_quad', 'pml_hybrid', 'pml_quad', 'sirt' ]
TOMOPY_FILT = [ 'None', 'shepp', 'cosine', 'hann', 'hamming', 'ramlak', 'parzen',
                'butterworth', 'custom', 'custom2d'] 

SCIKIT_FILT = [ 'shepp-logan', 'ramp','cosine', 'hamming', 'hann', 'None' ]
SCIKIT_INTR = [ 'linear', 'nearest', 'cubic']

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

    alg0,alg1,alg2 = [],[],[]
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

def check_parameters(sino, center, omega, tomo_alg, sinogram_order):


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
                 sinogram_order = False : sino = [ 2th   x slice x X ]
                 sinogram_order = True  : sino = [ slice x 2th   x X ]''')
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
            
def tomo_reconstruction(sino, refine_center=False, center_range=None, center=None,
                        tomo_alg=[], omega=None, sinogram_order=False, **args):
    '''
    INPUT ->  sino : slice, 2th, x OR 2th, slice, x (with flag sinogram_order=True/False)
    OUTPUT -> tomo : slice, x, y
    '''

    check = check_parameters(sino,center,omega,tomo_alg,sinogram_order)
    sino,center,omega,tomo_alg,sinogram_order = check
    
    if tomo_alg[0] is None:
        print('No tomographic reconstruction packages available')
        return center, np.zeros((1,sino.shape[-1],sino.shape[-1]))
    
    if tomo_alg[0].lower().startswith('scikit') and HAS_scikit:

        npts = sino.shape[2]
        center = int(center)
        cntr = npts - center   ## switch reference direction for compatibility with tomopy convention
        if not sinogram_order: sino = np.einsum('jik->ijk',sino)

        args.update({'theta':omega, 
                     'filter':tomo_alg[1],
                     'interpolation':tomo_alg[2],
                     'circle':True})

        if refine_center:
            print(' Refining center; start value: %i' % center)
            if center_range is None: center_range = 12
            rng = int(center_range) if center_range > 0 and center_range < 21 else 12

            center_list,negentropy = [],[]
            
            for cen in np.arange(cntr-rng, cntr+rng, 1, dtype=int):
                xslice = slice(npts-2*cen, -1) if cen <= npts/2. else slice(0, npts-2*cen)
                if sinogram_order:
                    recon = iradon(sino[0,:,xslice].T, **args)
                else:
                    recon = iradon(sino[0,xslice], **args)
                recon = recon - recon.min() + 0.005*(recon.max()-recon.min())
                negentropy += [(recon*np.log(recon)).sum()]
                center_list += [cen]
            cntr = center_list[np.array(negentropy).argmin()]
            center = float(npts-cntr) # flip axis for compatibility with tomopy convention
            print('   Best center: %i' % center)

        tomo = []
        xslice = slice(npts-2*cntr, -1) if cntr <= npts/2. else slice(0, npts-2*cntr)
        for sino0 in sino:
            tomo += [iradon(sino0[:,xslice].T, **args)]
        tomo = np.array(tomo)

    elif tomo_alg[0].lower().startswith('tomopy') and HAS_tomopy:

        if refine_center: 
            center = tomopy.find_center(sino, np.radians(omega), init=center, ind=0, tol=0.5, sinogram_order=sinogram_order)

        args.update({'center':center,
                     'algorithm':tomo_alg[1],
                     'sinogram_order':sinogram_order})
        tomo = tomopy.recon(sino, np.radians(omega),**args)

    return center,tomo

# def registerLarchPlugin():
#     return ('_tomo', {'create_tomogrp': create_tomogrp})
# 
# 
# def registerLarchGroups():
#     return (tomogrp)