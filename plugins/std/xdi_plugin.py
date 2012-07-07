#!/usr/bin/env python
"""
Read/Write XAS Data Interchange Format for larch

install the xdi python module from
    https://github.com/XraySpectroscopy/XAS-Data-Interchange
"""
import sys
from larch.larchlib import plugin_path

sys.path.insert(0, plugin_path('std'))

from xdi import XDIFile

def xdigroup(fname, _larch=None):
    """simple mapping of XDI file to larch groups"""
    if _larch is None:
        raise Warning("cannot read xdigroup -- larch broken?")

    x = XDIFile(fname)
    group = _larch.symtable.create_group()
    group.__name__ ='XDI file %s' % fname
    for key, val in x.__dict__.items():
        if not key.startswith('_'):
            setattr(group, key, val)
    return group

def registerLarchPlugin():
    return ('_io', {'xdigroup': xdigroup})
