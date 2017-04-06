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

def calcCIFpeaks(path,energy,verbose=True,fid=None,plotable=True,qmax=6):

    try:
        cif = xu.materials.Crystal.fromCIF(path,fid=fid)
        if verbose:
            print('Opening cif: %s' % os.path.split(path)[-1])
    except:
        print('incorrect file format: %s' % os.path.split(path)[-1])
        return

    ## generate hkl list
    hkllist = generate_hkl()
    
    ## For each hkl, calculate q and F
    qlist = cif.Q(hkllist)
    Flist = cif.StructureFactorForQ(qlist,energy,temp=300)

#     ## For each hkl, calculate q and F
#     qlist, Flist = [],[]
#     for hkl in hkllist:
#         qvec = cif.Q(hkl) ## 
#         F = cif.StructureFactor(qvec,energy,temp=300)
#         qlist += [np.linalg.norm(qvec)]
#         Flist += [np.abs(F)]
#     ##### both methods for identical 


    Fall,qall = [],[]
    for i,F in enumerate(Flist):
        if np.abs(F) > 0.01:
            Fadd,qadd = np.abs(F),np.linalg.norm(qlist[i])
            if qadd not in qall and qadd < qmax:
                if plotable:
                    Fall.extend((0,Fadd,0))
                    qall.extend((qadd,qadd,qadd))
                else:
                    Fall += [Fadd]
                    qall += [qadd]
      
    return np.array(qall),np.array(Fall)

                     
def registerLarchPlugin():
    return ('_xrd', {'calcCIFpeaks': calcCIFpeaks})
