#!/usr/bin/env python
"""
Some common math utilities
"""
from larch.utils import (linregress, polyfit, realimag, as_ndarray,
                         complex_phase, deriv, interp, interp1d, remove_dups,
                         remove_nans2, index_of, index_nearest)

def registerLarchPlugin():
    return ('_math', dict(linregress=linregress,
                          polyfit=polyfit,
                          realimag=realimag,
                          as_ndarray=as_ndarray,
                          complex_phase=complex_phase,
                          deriv=deriv,
                          interp=interp,
                          interp1d=interp1d,
                          remove_dups=remove_dups,
                          remove_nans2=remove_nans2,
                          index_of=index_of,
                          index_nearest=index_nearest))
