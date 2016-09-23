#!/usr/bin/env python
"""
Tools for searching XRD pattern matches from database or provided CIF files
mkak 2016.09.23
"""
import time
import os

#import fabio
#from pyFAI.multi_geometry import MultiGeometry

HAS_XRAYUTIL = False
try:
    import xrayutilities as xu
    HAS_XRAYUTIL = True
except ImportError:
    pass

#import matplotlib.pyplot as plt
import numpy as np
import glob
import os
import math

def struc_from_cif(ciffile,verbose=True):

    if verbose:
        print('Reading: %s' % ciffile)

    try:
        ## Open CIF using xu functions
        cif_strc = xu.materials.Crystal.fromCIF(ciffile)
    except:
        print('xrayutilities error: Could not read %s' % os.path.split(cif)[-1])
        return
        
    return cif_strc 

def calc_all_F(cry_strc,energy,maxhkl=10,qmax=10,twthmax=None):
    '''
    Calculate F for one energy for range of hkl for one structure
    mkak 2016.09.22
    '''
    ## Generate hkl list
    hkllist = []
    for i in range(maxhkl):
        for j in range(maxhkl):
            for k in range(maxhkl):
                hkllist.append([i,j,k])

    ## Calculate the wavelength
    wvlgth = xu.utilities.en2lam(energy)
    if twthmax:
        qmax = ((4*math.pi)/wvlgth)*np.sin(np.radians(twthmax/2))
    else:
        twthmax = 2*np.degrees(np.arcsin((wvlgth*qmax)/(4*math.pi)))

    q = []
    F_norm = []

    if verbose:
        print('Calculating XRD pattern for: %s' % cry_strc.name)
        
    ## For each hkl, calculate q and F
    for hkl in hkllist:
        qvec = cry_strc.Q(hkl)
        qnorm = np.linalg.norm(qvec)
        if qnorm < qmax:
            F = cry_strc.StructureFactor(qvec,energy)
            if np.abs(F) > 0.01 and np.linalg.norm(qvec) > 0:

                q.append(qnorm)
                q.append(qnorm)
                q.append(qnorm)

                F_norm.append(0)
                F_norm.append(np.abs(F))
                F_norm.append(0)

    if F_norm:  and max(F_norm) > 0:
        q = np.array(q)
        F_norm = np.array(F_norm)/max(F_norm)
        return q,F_norm


def show_F_depend_on_E(cry_strc,hkl,emin=500,emax=20000,esteps=5000):
    '''
    Dependence of F on E for single hkl for one cif
    mkak 2016.09.22
    '''
    E = np.linspace(emin,emax,esteps)
    F = cry_strc.StructureFactorForEnergy(cry_strc.Q(hkl), E)

    return E,F

