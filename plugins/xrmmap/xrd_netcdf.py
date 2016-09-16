#!/usr/bin/env python
"""
support for netcdf XRD files from **DETECTOR NAME**
in Epics Mapping Mode -- copied from xmap_netcdf.py (larch plugins)
mkak 2016.07.06
"""
import numpy as np
import os

import copy
from copy import deepcopy

## Package for reading netcdf files (in scipy)
try:
    import scipy.io.netcdf
    netcdf_open = scipy.io.netcdf.netcdf_file
except ImportError:
    raise ImportError('cannot find scipy netcdf module')

## Does this need to change?
CLOCKTICK = 0.320  # xmap clocktick = 320 ns

def read_xrd_netcdf(fname,verbose=False): #npixels=self.nrows_expected
    ## Reads a netCDF file created for XRD mapping
    
    if verbose:
        print(' reading %s' % fname)
    
    ## Reads an XRD netCDF file with the netCDF plugin buffers
    xrd_file = netcdf_open(fname,'r')
    xrd_data = xrd_file.variables['array_data'].data.copy()
    xrd_data = xrd_data.astype('uint16')
    xrd_file.close()
    
    ## Forces data into 3D shape
    shape = xrd_data.shape ## (no_images,pixels_x,pixels_y)
    if len(shape) == 2:
        print('Reshaping to (%i, %i, %i)' % (1, shape[0], shape[1]))
        xrd_data.shape = (1, shape[0], shape[1])

    return xrd_data

def test_read(fname):
    print( fname,  os.stat(fname))
    fd = read_xrd_netcdf(fname, verbose=True)
    print(fd.counts.shape)

def registerLarchPlugin():
    return ('_xrd', {'read_xrd_netcdf': read_xrd_netcdf})
