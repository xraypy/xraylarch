#!/usr/bin/env python
'''
Diffraction functions that require xrayutilities package

mkak 2017.03.14
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import os
import numpy as np

HAS_XRAYUTIL = False
try:
    import xrayutilities as xu
    HAS_XRAYUTIL = True
except ImportError:
    pass

from larch import ValidateLarchPlugin
from larch_plugins.xrd.xrd_hkl import generate_hkl

##########################################################################
# FUNCTIONS

@ValidateLarchPlugin
def structurefactor_from_cif(ciffile, wavelength, qmax=10, _larch=None):
    '''
    Calculate structure factor, F from cif
    mkak 2016.09.22
    
    ciffile    : 
    wavelength :
    qmax       :
    '''

    ## Calculate the wavelength/energy
    energy = E_from_lambda(wavelength,E_units='eV') ## check to make sure these are the proper units
    
    ## Generate hkl list
    hkllist = generate_hkl()

    try:
        ## Open CIF using xu functions
        cif_strc = xu.materials.Crystal.fromCIF(ciffile)
    except:
        print('xrayutilities failed to read %s' % os.path.split(ciffile)[-1])
        return
        
    ## For each hkl, calculate q and F
    q_cif, F_cif = [],[]
    qlist, Flist = [],[]
    for hkl in hkllist:
        qvec = cif_strc.Q(hkl) ## 
        q = np.linalg.norm(qvec)
        if q < qmax:
            F = cif_strc.StructureFactor(qvec,energy)
            if np.abs(F) > 0.01 and np.linalg.norm(qvec) > 0:
                q_cif += [q,q,q]
                F_cif += [0,np.abs(F),0]
                qlist += [q]
                Flist += [np.abs(F)]

    if F_cif and max(F_cif) > 0:
        q_cif = np.array(q_cif)
    else:
        print('Could not calculate any structure factors.')
        return
    
    return np.array([qlist,Flist]),np.array(q_cif),np.array(F_cif)

@ValidateLarchPlugin
def structurefactor_wrt_E(cry_strc, hkl, emin=500, emax=20000, esteps=5000, _larch=None):
    '''
    Dependence of F on E for single hkl for one cif
    mkak 2016.09.22
    
    cry_strc : 
    hkl      :
    emin     :
    emax     :
    esteps   :
    '''
    E = np.linspace(emin,emax,esteps)
    F = cry_strc.StructureFactorForEnergy(cry_strc.Q(hkl), E)

    return E,F

                     
def registerLarchPlugin():
    return ('_xrd', {'structurefactor_from_cif': structurefactor_from_cif,
                     'structurefactor_wrt_E': structurefactor_wrt_E
                      })
