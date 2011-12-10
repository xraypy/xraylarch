#!/usr/bin/env python
"""
  Larch hdf5group() function
"""

import h5py
import numpy
from larch.closure import Closure

def h5group(fname, larch=None):
    """simple mapping of hdf5 file to larch groups"""
    if larch is None:
        raise Warning("cannot read h5group -- larch broken?")
    fh = h5py.File(fname, 'r')
    group = larch.symtable.create_group
    def add_component(key, val, top):
        parents = key.split('/')
        current = parents.pop()
        for word in parents:
            if not hasattr(top, word):
                setattr(top, word, group())
            top = getattr(top, word)
        tname = top.__name__
        if isinstance(val, h5py.Group):
            setattr(top, current,  group(name=tname+'/'+current))
            if len(val.attrs) > 0:
                setattr(top, 'attrs', dict(val.attrs))
        else:
            dat = fh.get(key)
            try:
                if len(dat) > 1 and dat.dtype.type == numpy.string_:
                    dat = list(dat)
            except:
                pass
            setattr(top, current, dat)
            if len(val.attrs) > 0:
                setattr(top, current+'_attrs', dict(val.attrs))
    top = group(name=fname)
    setattr(top, 'h5_file', fh)
    fh.visititems(Closure(func=add_component, top=top))
    return top

def registerLarchPlugin():
    return ('_io', {'h5group': h5group})


