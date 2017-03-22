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

from larch_plugins.xrd.xrd_hkl import generate_hkl

##########################################################################
# FUNCTIONS

# def structurefactor_from_cif(ciffile, wavelength, qmax=10):
#     '''
#     Calculate structure factor, F from cif
#     mkak 2016.09.22
#     
#     ciffile    : 
#     wavelength :
#     qmax       :
#     '''
# 
#     ## Calculate the wavelength/energy
#     energy = E_from_lambda(wavelength,E_units='eV') ## check to make sure these are the proper units
#     
#     ## Generate hkl list
#     hkllist = generate_hkl()
# 
#     try:
#         ## Open CIF using xu functions
#         cif_strc = xu.materials.Crystal.fromCIF(ciffile)
#     except:
#         print('xrayutilities failed to read %s' % os.path.split(ciffile)[-1])
#         return
#         
#     ## For each hkl, calculate q and F
#     q_cif, F_cif = [],[]
#     qlist, Flist = [],[]
#     for hkl in hkllist:
#         qvec = cif_strc.Q(hkl) ## 
#         q = np.linalg.norm(qvec)
#         if q < qmax:
#             F = cif_strc.StructureFactor(qvec,energy)
#             if np.abs(F) > 0.01 and np.linalg.norm(qvec) > 0:
#                 q_cif += [q,q,q]
#                 F_cif += [0,np.abs(F),0]
#                 qlist += [q]
#                 Flist += [np.abs(F)]
# 
#     if F_cif and max(F_cif) > 0:
#         q_cif = np.array(q_cif)
#     else:
#         print('Could not calculate any structure factors.')
#         return
#     
#     return np.array([qlist,Flist]),np.array(q_cif),np.array(F_cif)
# 
# 
# def structurefactor_wrt_E(cry_strc, hkl, emin=500, emax=20000, esteps=5000):
#     '''
#     Dependence of F on E for single hkl for one cif
#     mkak 2016.09.22
#     
#     cry_strc : 
#     hkl      :
#     emin     :
#     emax     :
#     esteps   :
#     '''
#     E = np.linspace(emin,emax,esteps)
#     F = cry_strc.StructureFactorForEnergy(cry_strc.Q(hkl), E)
# 
#     return E,F

def calcCIFpeaks(path,energy,verbose=True):

    try:
        cif = xu.materials.Crystal.fromCIF(path)
        if verbose:
            print('Opening cif: %s' % os.path.split(path)[-1])
    except:
        print('incorrect file format: %s' % os.path.split(path)[-1])
        return

    ## generate hkl list
    hkllist = generate_hkl()

    qlist = cif.Q(hkllist)
    Flist = cif.StructureFactorForQ(qlist,energy)

    Fall = []
    qall = []
    hklall = []
    for i,hkl in enumerate(hkllist):
        if np.abs(Flist[i]) > 0.01:
            Fadd = np.abs(Flist[i])
            qadd = np.linalg.norm(qlist[i])
            if qadd not in qall and qadd < 6:
                Fall.extend((0,Fadd,0))
                qall.extend((qadd,qadd,qadd))
                
    return np.array(qall),np.array(Fall)


                     
def registerLarchPlugin():
    return ('_xrd', {'calcCIFpeaks': calcCIFpeaks})
