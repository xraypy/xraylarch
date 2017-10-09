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

def check_parameters(sino, method, center, omega, algorithm_A, algorithm_B):

    method = check_method(method)
    
    if center is None: center = sino.shape[1]/2.
    if omega is None: omega = np.linspace(0,360,sino.shape[2])

    if method.lower().startswith('scikit') and HAS_scikit:
        if algorithm_A == 'None':
            algorithm_A = None
        elif algorithm_A not in SCIKIT_FILT:
            algorithm_A = 'shepp-logan'
        if algorithm_B not in SCIKIT_INTR:
            algorithm_B = 'linear'
        npts = sino.shape[1]

    elif method.lower().startswith('tomopy') and HAS_tomopy:

        if algorithm_A not in TOMOPY_ALG:
            algorithm_A = 'gridrec'
        if algorithm_B not in TOMOPY_FILT or algorithm_B == 'None':
            algorithm_B = None
        
    return method, center, omega, algorithm_A, algorithm_B

def tomo_reconstruction(sino, refine_cen=False, cen_range=None, center=None, method=None,
                        algorithm_A=None, algorithm_B=None, omega=None):
    '''
    INPUT ->  sino : slice, x, 2th
    OUTPUT -> tomo : slice, x, y
    '''
    
    method,center,omega,algorithm_A,algorithm_B = check_parameters(sino,method,center,
                                                        omega,algorithm_A,algorithm_B)
                                                        
    if method is None:
        print('No tomographic reconstruction packages available')
        return
    
    if method.lower().startswith('scikit') and HAS_scikit:

        tomo = []
        npts = sino.shape[1]
        cntr = int(npts - center) # flip axis for compatibility with tomopy convention

        if refine_cen:
            if cen_range is None: cen_range = 12
            rng = int(cen_range) if cen_range > 0 and cen_range < 21 else 12

            cen_list,negentropy = [],[]
            
            print('Testing centers in range %i to % i...' % (cntr-rng, cntr+rng))
            for cen in np.arange(cntr-rng, cntr+rng, 1, dtype=int):
                xslice = slice(npts-2*cen, -1) if cen <= npts/2. else slice(0, npts-2*cen)
                recon = iradon(sino[0,xslice],
                               theta=omega, 
                               filter=algorithm_A,
                               interpolation=algorithm_B,
                               circle=True)
                recon = recon - recon.min() + 0.005*(recon.max()-recon.min())
                negentropy += [(recon*np.log(recon)).sum()]
                cen_list += [cen]
            cntr = cen_list[np.array(negentropy).argmin()]
            print('  Best value: %i' % int(npts - cntr))

        xslice = slice(npts-2*cntr, -1) if cntr <= npts/2. else slice(0, npts-2*cntr)

        for sino0 in sino:
            tomo += [iradon(sino0[xslice], theta=omega, filter=algorithm_A,
                                           interpolation=algorithm_B, circle=True)]
        tomo = np.flip(tomo,1)
        center = (npts-cntr)/1. # flip axis for compatibility with tomopy convention

    elif method.lower().startswith('tomopy') and HAS_tomopy:

        ## reorder to: 2th,slice,x for tomopy
        sino = np.einsum('jki->ijk', np.einsum('kji->ijk', sino).T )

        if refine_cen: 
            center = tomopy.find_center(sino, np.radians(omega), init=center, ind=0, tol=0.5)

        tomo = tomopy.recon(sino, np.radians(omega), center=center, algorithm=algorithm_A) #,
#                             filter_name=algorithm_B) 
        
        ## reorder to slice, x, y
        tomo = np.flip(tomo,1)

    else:
        tomo = np.zeros((1,np.shape(sino)[0],np.shape(sino)[0]))

    return center,tomo

# def registerLarchPlugin():
#     return ('_tomo', {'create_tomogrp': create_tomogrp})
# 
# 
# def registerLarchGroups():
#     return (tomogrp)