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

TOMOPY_ALG  = [ 'art', 'bart', 'fbp', 'gridrec', 'mlem', 'osem', 'ospml_hybrid',
                'ospml_quad', 'pml_hybrid', 'pml_quad', 'sirt' ]
TOMOPY_FILT = [ 'none', 'shepp', 'cosine', 'hann', 'hamming', 'ramlak', 'parzen',
                'butterworth', 'custom', 'custom2d'] 

SCIKIT_FILT = [ None, 'ramp', 'shepp-logan', 'cosine', 'hamming', 'hann' ]
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

    methods = []
    algor   = []
    if HAS_tomopy:
        methods += ['tomopy']
        algor   += [['art','bart','fbp','gridrec','mlem','osem','ospml_hybrid','ospml_quad','pml_hybrid','pml_quad','sirt']]
    eif HAS_scikit:
        methods += ['scikit-image']
        algor   += [['']]

    return methods,algor


def refine_center(sino, center=None, method=None, omega=None):

    method = check_method(method)
    if method is None:
        print('No tomographic reconstruction packages available')
        return


    if method.lower().startswith('scikit') and HAS_scikit:
        npts = sino.shape[1]
        if center is None: center = npts/2. 
        if omega is None: omega = np.linspace(0,np.radians(360),sino.shape[2])

        rng,cen_list,entropy = 12,[],[]
        for cen in np.arange(center-rng, center+rng, 1):
            cen = int(cen)
            xslice = slice(npts-2*cen, -1) if cen < npts/2. else slice(0, npts-2*cen)
            recon = iradon(sino[0,xslice],
                           theta=omega, 
                           filter='shepp-logan',
                           interpolation='linear',
                           circle=True)
            recon = recon - recon.min() + 0.005*(recon.max()-recon.min())
            negentropy = (recon*np.log(recon)).sum()
            cen_list += [cen]
            entropy += [negentropy]
        center = cen_list[np.array(entropy).argmin()]
        #for c,e in zip(cen_list,entropy): print('%i %i' %(c,e))

    elif method.lower().startswith('tomopy') and HAS_tomopy:
        if center is None: center = sino.shape[2]/2. 
        if omega is None: omega = np.linspace(0,np.radians(360),sino.shape[0])
        center = tomopy.find_center(sino, omega, init=center, ind=0, tol=0.5)

    return center

def tomo_reconstruction(sino, refine_cen=False, center=None, method=None, algorithm=None, filter=None, interpolation=None, omega=None):
    '''
    sino : slice, x, 2th
    tomo : slice, x, y
    '''
    
    method = check_method(method)
    if method is None:
        print('No tomographic reconstruction packages available')
        return
    
    if center is None: center = sino.shape[1]/2.
    if omega is None: omega = np.linspace(0,360,sino.shape[2])
    
    if method.lower().startswith('scikit') and HAS_scikit:
        if filter not in SCIKIT_FILT:
            filter = 'shepp-logan'
        if interpolation not in SCIKIT_INTR:
            interpolation = 'linear'

        if refine_cen: center = refine_center(sino,center=center,method=method,omega=omega)
        tomo = []
        for sino0 in sino:
            tomo += [iradon(sino0, theta=omega, filter=filter, interpolation=interpolation, circle=True)]
        tomo = np.flip(tomo,1)

    elif method.lower().startswith('tomopy') and HAS_tomopy:
        
        if algorithm not in TOMOPY_ALG:
            algorithm = 'gridrec'
        if filter not in TOMOPY_FILT:
            filter = None

        ## reorder to: 2th,slice,x for tomopy
        sino = np.einsum('jki->ijk', np.einsum('kji->ijk', sino).T )
        
        omega = np.radians(omega)

        if refine_cen: center = refine_center(sino,center=center,omega=omega)
        tomo = tomopy.recon(sino, omega, center=center, algorithm=algorithm) #filter_name=filter, 
        
        ## reorder to slice, x, y
        tomo = np.flip(tomo,1)

    return center,tomo

# def registerLarchPlugin():
#     return ('_tomo', {'create_tomogrp': create_tomogrp})
# 
# 
# def registerLarchGroups():
#     return (tomogrp)