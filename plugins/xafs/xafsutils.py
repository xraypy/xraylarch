"""
Utility functions used for xafs analysis
"""
import numpy as np
from larch import Group, isgroup
import scipy.constants as consts
KTOE = 1.e20*consts.hbar**2 / (2*consts.m_e * consts.e) # 3.8099819442818976
ETOK = 1.0/KTOE

def etok(energy):
    """convert photo-electron energy to wavenumber"""
    return np.sqrt(energy/KTOE)

def ktoe(k):
    """convert photo-electron wavenumber to energy"""
    return k*k*KTOE

_GROUPARG_ERRMSG_ = """%s: needs First Argument Group or valid arguments for 
  %s"""

def group_arg_parse(arg0,  names=None, group=None, fcn_name=None, args=None,
                    check_outputs=True):
    """parses initial arguments for Larch functions, testing for
       First Argument as Group

    That is, if the first argument is a Group and contains members named in 'names',
    this will return data extracted from that group.  For example, for the function
       find_e0(energy, mu=None, group=None)

    uses the following
    
       energy, mu, group = group_arg_parse(energy, args=(mu,), 
                                           names=('energy', 'mu'),
                                           group=group,                                   
                                           fcn_name='find_e0')

    allowing the caller to use
         find_e0(grp)
    in place of
         find_e0(grp.energy, grp.mu, group=grp)

    the args tuple should be passed so that the returned values are correct
    if the caller actually specifies arrays as for the full call signature.

    
    if check_outputs is True, all outputs (except the final group) a Warning will be
    raised if any output besides the final group is None.

    fcn_name is used only for error messages

    """
    if names is None:
        names = []
    if not isgroup(arg0, *names):
        out = [arg0]
        for a in args:
            out.append(a)
    else:
        if group is None:
            group = arg0
        out = [getattr(arg0, attr) for attr in names]

    # test that all outputs are non-None
    if check_outputs:
        if fcn_name is None: fcn_name ='unknown function'
        for i, nam in enumerate(names):
            if out[i] is None:
                raise Warning(_GROUPARG_ERRMSG_ % (fcn_name, ', '.join(names)))

    out.append(group)
    return out

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


def registerLarchPlugin():
    return ('_xafs', {'etok': etok, 'ktoe': ktoe})
