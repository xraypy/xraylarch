#!/usr/bin/env python
"""
  Larch hdf5group() function
"""

import h5py
import numpy
from larch.utils import Closure

import scipy.io.netcdf

def netcdf_group(fname, _larch=None, **kws):
    """open a NetCDF file and map the variables in it to larch groups
    g = netcdf_group('tmp.nc')
    """
    if _larch is None:
        raise Warning("cannot run netcdf_file: larch broken?")
    finp = scipy.io.netcdf.netcdf_file(fname, mode='r')
    group = _larch.symtable.create_group()
    for k, v in finp.variables.items():
        setattr(group, k, v.data)
    finp.close()
    return group

def netcdf_file(fname, mode='r', _larch=None):
    """open and return a raw NetCDF file, equvialent to
    scipy.io.netcdf.netcdf_file(fname, mode=mode)
    """
    return scipy.io.netcdf.netcdf_file(fname, mode=mode)

def h5file(fname, mode='r', _larch=None):
    """open and return a raw HDF5 file, equvialent to
    import h5py
    h5py.File(fname, mode)
    """
    return h5py.File(fname, mode)

def h5group(fname, _larch=None):
    """open an HDF5 file, and map to larch groups
    g = h5group('myfile.h5')

    Notes:
    ------
     1. This leaves the file open (for read).
     2. The raw file handle will be held in the 'h5_file' group member.
     3. Attributes of groups and datasets are generally placed in
       'itemname_attrs'.
    """
    if _larch is None:
        raise Warning("cannot run h5group: larch broken?")
    fh = h5py.File(fname, mode)
    group = _larch.symtable.create_group

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
                getattr(top, current).attrs = dict(val.attrs)
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
    top.h5_file = fh
    fh.visititems(Closure(func=add_component, top=top))
    return top

def registerLarchPlugin():
    meths = {'h5group': h5group,
             'h5file': h5file,
             'netcdf_file': netcdf_file,
             'netcdf_group': netcdf_group}
    return ('_io', meths)


