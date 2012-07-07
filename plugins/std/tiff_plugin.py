#!/usr/bin/env python
"""
Read/Write TIFF Files, using tifffile.py from Christoph Gohlke
"""
import sys
from larch.larchlib import plugin_path

sys.path.insert(0, plugin_path('std'))

from tifffile import imread, imshow, TIFFfile

def read_tiff(fname, _larch=None, *args, **kws):
    """read TIFF file as array"""
    if _larch is None:
        raise Warning("cannot read tiff -- larch broken?")
    return imread(fname, *args, **kws)

def tiff_object(fname, _larch=None, *args, **kws):
    """read TIFF file as a TIFF object"""
    if _larch is None:
        raise Warning("cannot read tiff -- larch broken?")
    return TIFFfile(fname)

def registerLarchPlugin():
    return ('_io', {'read_tiff': read_tiff,
                    'tiff_object': tiff_object})
