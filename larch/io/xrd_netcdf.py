#!/usr/bin/env python
"""
support for netcdf XRD files from **DETECTOR NAME**
in Epics Mapping Mode -- copied from xmap_netcdf.py (larch plugins)
mkak 2016.07.06 // updated 2018.03.30 to increase speed and read other
variables in netcdf file (or return all as dictionary)
"""

import os

## Package for reading netcdf files (in scipy)
try:
    import scipy.io.netcdf
    netcdf_open = scipy.io.netcdf.netcdf_file
except ImportError:
    raise ImportError('cannot find scipy netcdf module')

def read_xrd_netcdf(fname,verbose=False):

    ## Reads a netCDF file created for XRD mapping
    if verbose:
        print(' reading %s' % fname)

    ## Reads an XRD netCDF file with the netCDF plugin buffers
    xrd_data = read_netcdf(fname, keyword='array_data')
    xrd_data = xrd_data.astype('uint16')

    ## Forces data into 3D shape
    xrdshape = xrd_data.shape ## (no_images,pixels_x,pixels_y)
    if len(xrdshape) == 2:
        if verbose:
            print('Reshaping to (%i, %i, %i)' % (1, xrdshape[0], xrdshape[1]))
        xrd_data.shape = (1, xrdshape[0], xrdshape[1])

    return xrd_data

def read_xrd_netcdf_exptime(fname,verbose=False):
    '''
    returns header information for provided xrd netcdf file
    '''
    return read_netcdf(fname,keyword='Attr_FrameTime')

def read_netcdf(fname,verbose=False,keyword=None):
    '''
    returns dictionary of all information in provided xrd netcdf file
    unless data from only one key is specified
    '''

    with netcdf_open(fname, mmap=False) as file_netcdf:
        if keyword is not None and keyword in file_netcdf.variables.keys():
            return file_netcdf.variables[keyword].data
        else:
            netcdf_dict = {}
            for key,val in dict(file_netcdf.variables).items():
                netcdf_dict[key] = val.data
            return netcdf_dict

def test_read(fname):
    print( fname,  os.stat(fname))
    fd = read_xrd_netcdf(fname, verbose=True)
    print(fd.counts.shape)
