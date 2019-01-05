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

The functions here include (but are not limited to):

function         description
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
    """set _sys.xafsGroup to the supplied group (if not None)

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


def initializeLarchPlugin(_larch=None):
    """initialize _xafs"""
    if _larch is None:
        return

    mod = getattr(_larch.symtable, '_xafs')
    mod.__doc__ = MODDOC

    import_xafs_plot_module = """
    _larch("import xafs_plots")
    xplots = getattr(_larch.symtable, 'xafs_plots', None)
    if xplots is None:
        return

    # move xafs_plots macros to _xafs group
    for name in ('plotlabels', 'plot_bkg', 'plot_chifit', 'plot_chik',
                 'plot_chir', 'plot_mu', 'plot_path_k', 'plot_path_r',
                 'plot_paths_k', 'plot_paths_r'):
        item = getattr(xplots, name, None)
        if item is not None:
            setattr(_larch.symtable._xafs, name, item)
        delattr(xplots, name)
    delattr(_larch.symtable, 'xafs_plots')
    """

def registerLarchPlugin():
    return ('_xafs', {'etok': etok, 'ktoe': ktoe,
                      'guess_energy_units': guess_energy_units})
