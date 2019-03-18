#!/usr/bin/env python
"""
  Larch hdf5group() function
"""

import h5py
import numpy
from functools import partial
from larch.utils import fixName
from larch import ValidateLarchPlugin
import scipy.io.netcdf

@ValidateLarchPlugin
def netcdf_group(fname, _larch=None, **kws):
    """open a NetCDF file and map the variables in it to larch groups
    g = netcdf_group('tmp.nc')
    """
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

@ValidateLarchPlugin
def h5group(fname, mode='r+', _larch=None):
    """open an HDF5 file, and map to larch groups
    g = h5group('myfile.h5')

    Arguments
    ------
     mode    string for file access mode ('r', 'w', etc)
             default mode is 'r+' for read-write access.

    Notes:
    ------
     1. The raw file handle will be held in the 'h5_file' group member.
     2. Attributes of groups and datasets are generally placed in
       'itemname_attrs'.
    """
    fh = h5py.File(fname, mode)
    group = _larch.symtable.create_group

    def add_component(key, val, top):
        parents = [fixName(w, allow_dot=False) for w in key.split('/')]
        current = parents.pop()
        for word in parents:
            if not hasattr(top, word):
                setattr(top, word, group())
            top = getattr(top, word)
        tname = top.__name__
        if isinstance(val, h5py.Group):
            setattr(top, current,  group(name="%s/%s" % (tname, current)))
            if len(val.attrs) > 0:
                getattr(top, current)._attrs = dict(val.attrs)
        else:
            dat = fh.get(key)
            try:
                if dat.dtype.type == numpy.string_:
                    if len(dat) == 1:
                        dat = dat.value
                    else:
                        dat = list(dat)
            except (ValueError, TypeError):
                pass
            setattr(top, current, dat)
            if len(val.attrs) > 0:
                setattr(top, "%s_attrs" % current, dict(val.attrs))
    top = group(name=fname)
    top.h5_file = fh
    fh.visititems(partial(add_component, top=top))
    return top
