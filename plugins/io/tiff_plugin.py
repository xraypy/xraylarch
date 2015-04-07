#!/usr/bin/env python
"""
Read/Write TIFF Files, using tifffile.py from Christoph Gohlke
"""
import larch
from larch_plugins.io.tifffile import imread, imshow, TIFFfile

def read_tiff(fname, _larch=None, *args, **kws):
    """read image data from a TIFF file as an array"""
    return imread(fname, *args, **kws)

def tiff_object(fname, _larch=None, *args, **kws):
    """read TIFF file, giving access to TIFF object, with several
    methods, including:

      series():  series of TIFF pages, with shape and properties
      asarray(): return image data as array (as read_tiff)
    """
    return TIFFfile(fname)

def registerLarchPlugin():
    return ('_io', {'read_tiff': read_tiff,
                    'tiff_object': tiff_object})
