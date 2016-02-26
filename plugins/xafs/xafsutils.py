"""
Utility functions used for xafs analysis
"""
import numpy as np
from larch import Group, ValidateLarchPlugin

import scipy.constants as consts
KTOE = 1.e20*consts.hbar**2 / (2*consts.m_e * consts.e) # 3.8099819442818976
ETOK = 1.0/KTOE

MODDOC = '''
XAFS Functions for Larch, essentially Ifeffit 2

The functions here include (but are not limited too):

function         descrption
------------     ------------------------------
pre_edge         pre_edge subtraction, normalization
autobk           XAFS background subtraction (mu(E) to chi(k))
xftf             forward XAFS Fourier transform (k -> R)
xftr             backward XAFS Fourier transform, Filter (R -> q)
ftwindow         create XAFS Fourier transform window

feffpath         create a Feff Path from a feffNNNN.dat file
path2chi         convert a single Feff Path to chi(k)
ff2chi           sum a set of Feff Paths to chi(k)

feffit_dataset   create a Dataset for Feffit
feffit_transform create a Feffit transform group
feffit           fit a set of Feff Paths to Feffit Datasets
feffit_report    create a report from feffit() results




'''
def etok(energy):
    """convert photo-electron energy to wavenumber"""
    return np.sqrt(energy/KTOE)

def ktoe(k):
    """convert photo-electron wavenumber to energy"""
    return k*k*KTOE

@ValidateLarchPlugin
def set_xafsGroup(group, _larch=None):
    """set _sys.xafsGroup to the supplied group (if not None)

    return _sys.xafsGroup.

    if needed, a new, empty _sys.xafsGroup may be created.
    """
    if group is None:
        if not hasattr(_larch.symtable._sys, 'xafsGroup'):
            _larch.symtable._sys.xafsGroup = Group()
    else:
        _larch.symtable._sys.xafsGroup = group
    return _larch.symtable._sys.xafsGroup


def initializeLarchPlugin(_larch=None):
    """initialize _xafs"""
    if _larch is not None:
        mod = getattr(_larch.symtable, '_xafs')
        mod.__doc__ = MODDOC

def registerLarchPlugin():
    return ('_xafs', {'etok': etok, 'ktoe': ktoe})
