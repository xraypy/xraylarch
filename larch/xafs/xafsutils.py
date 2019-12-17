"""
Utility functions used for xafs analysis
"""
import numpy as np
from larch import Group

import scipy.constants as consts
KTOE = 1.e20*consts.hbar**2 / (2*consts.m_e * consts.e) # 3.8099819442818976
ETOK = 1.0/KTOE

def etok(energy):
    """convert photo-electron energy to wavenumber"""
    return np.sqrt(energy/KTOE)

def ktoe(k):
    """convert photo-electron wavenumber to energy"""
    return k*k*KTOE

def guess_energy_units(e):
    """guesses the energy units of the input array of energies
    returns one of
        'eV'     energy looks to be in eV
        'keV'    energy looks to be in keV
        'deg'    energy looks to be in degrees
        'steps'  energy looks to be in angular steps

    The default is 'eV'.
      keV   :  max(e) < 120, smallest step < 0.005, e increasing
      deg   :  max(e) <  90, smallest step < 0.005, e decreasing
      steps :  max(e) > 200,000

    Note that there is a potential for ambiguity between data
    measured in 'deg' and data measured in 'keV' with e decreasing!
    """

    ework = e.flatten()
    ediff = np.diff(ework)
    emax = max(ework)

    units = 'eV'
    if emax > 200000:
        units = 'steps'
    if emax < 120.0 and (abs(ediff).min() < 0.005):
        units = 'keV'
        if emax < 90.0 and (ediff.mean() < 0.0):
            units = 'deg'
    return units

def set_xafsGroup(group, _larch=None):
    """set _sys.xafsGroup to the s<upplied group (if not None)

    return _sys.xafsGroup.

    if needed, a new, empty _sys.xafsGroup may be created.
    """
    if group is None:
        if _larch is None:
            group = Group()
        else:
            group = getattr(_larch.symtable._sys, 'xafsGroup', Group())
    if _larch is not None:
        _larch.symtable._sys.xafsGroup = group
    return group
