#!/usr/bin/env python
"""
support for netcdf XRD files from **DETECTOR NAME**
in Epics Mapping Mode 
mkak 2016.07.06 / updated 2017.03.07
"""
import numpy as np
import os

## Package for reading netcdf files (in scipy)
try:
    import scipy.io.netcdf
    netcdf_open = scipy.io.netcdf.netcdf_file
except ImportError:
    raise ImportError('cannot find scipy netcdf module')

def read_xrd_netcdf(fname,verbose=False): #npixels=self.nrows_expected
    ## Reads a netCDF file created for XRD mapping
    
    if verbose:
        print(' reading %s' % fname)
    
    ## Reads an XRD netCDF file with the netCDF plugin buffers
    with netcdf_open(fname,'r') as xrd_file:

        xrd_data = xrd_file.variables['array_data'].data.astype('uint16')
        
        ## Forces data into 3D shape
        shape = xrd_data.shape
        if len(shape) == 2:
            xrd_data.shape = (1, shape[0], shape[1])
    
    return xrd_data

def test_read(fname):
    print( fname,  os.stat(fname))
    fd = read_xrd_netcdf(fname, verbose=True)
    print(fd.counts.shape)

def registerLarchPlugin():
    return ('_xrd', {'read_xrd_netcdf': read_xrd_netcdf})
