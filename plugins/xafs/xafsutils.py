"""
Utility functions used for xafs analysis
"""
import numpy as np

KTOE = 3.809980849311092
ETOK = 1.0/KTOE

def etok(energy):
    """convert photo-electron energy to wavenumber"""
    return np.sqrt(energy/KTOE)

def ktoe(k):
    """convert photo-electron wavenumber to energy"""    
    return k*k*KTOE

def registerLarchPlugin():
    return ('_xafs', {'etok': etok, 'ktoe': ktoe})
