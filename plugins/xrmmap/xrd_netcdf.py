#!/usr/bin/env python
"""
support for netcdf XRD files from **DETECTOR NAME**
in Epics Mapping Mode -- copied from xmap_netcdf.py (larch plugins)
mkak 2016.07.06
"""
import numpy as np
import time
import sys
import os

import glob
import re
import copy
from copy import deepcopy

import fabio
from pyFAI.multi_geometry import MultiGeometry
import pyFAI.calibrant
import pyFAI

import larch

import matplotlib.pyplot as plt


## Package for reading netcdf files (in scipy)
try:
    import scipy.io.netcdf
    netcdf_open = scipy.io.netcdf.netcdf_file
except ImportError:
    raise ImportError('cannot find scipy netcdf module')

## Not sure...
class NCxrdDATA(object):
    def __init__(self,data_shape):
        self.I0           = np.zeros(data_shape[0], dtype='f8')
##        self.XRDframes    = np.zeros(data_shape,    dtype='f8')
#        self.qrange       = []
#        self.irange       = []

## Does this need to change?
CLOCKTICK = 0.320  # xmap clocktick = 320 ns

def read_xrd_netcdf(fname,verbose=False): #npixels=self.nrows_expected
    ## Reads a netCDF file created for XRD mapping
    
    if verbose:
        print ' reading %s' % fname
    
    ## Reads an XRD netCDF file with the netCDF plugin buffers
    xrd_file = netcdf_open(fname,'r')
    xrd_data = xrd_file.variables['array_data'].data.copy()
    xrd_I0 = xrd_file.variables['Attr_IonChamberI0'].data.copy()
    data_shape = deepcopy(xrd_file.variables['array_data'].shape)
    xrd_file.close()
    
    ## Forces data into 3D shape
    shape = xrd_data.shape ## (no_images,pixels_x,pixels_y)
    if len(shape) == 2:
        print 'Reshaping to (%i, %i, %i)' % (1, shape[0], shape[1])
        xrd_data.shape = (1, shape[0], shape[1])

    ## Defines new variable in NCxrdDATA class
    XRDdata = NCxrdDATA(data_shape)
    XRDdata.I0 = xrd_I0
    
    XRDdata.XRDframes = np.zeros(data_shape,    dtype='f8')
    XRDdata.XRDframes = xrd_data[:]

    ## Trims negative data
    XRDdata.XRDframes[XRDdata.XRDframes<0] = 0
    #XRDdata.XRDframes[XRDdata.XRDframes>100000] = 0

    ## returns array of size data_shape (201 x 1024 x 1024)
#    return XRDdata
    return xrd_data[:]

## WHERE DOES THIS BELONG? perhaps even inside of roi.py?
def make_xrd_map(data_dir,xrd_roi,verbose=False):

    t0 = time.time()
    
    xrd_netcdf = glob.glob('%s/*.nc' % data_dir)
    
    xrd_file = netcdf_open(xrd_netcdf[0],'r')
    data_shape = deepcopy(xrd_file.variables['array_data'].shape)
    xrd_file.close()
    
    xrd_img = np.zeros([data_shape[1],data_shape[2]])
    count_roi = 0
    
    for i in range(len(xrd_netcdf)):
        if 1.0 in xrd_roi[i,]:
            count_roi += np.sum(xrd_roi[i,])
            if verbose:
                print 'Adding %i frames from %s...' %(np.sum(xrd_roi[i,]),xrd_netcdf[i])
            ## Reverse all odd numbered rows
            reverse = True if i%2 else False
            xrd_img += roi_xrd_netcdf(xrd_netcdf[i],xrd_roi[i,],rev=reverse,verbose=verbose)
    
    if verbose:
        print '\n%i frames inside of ROI.' % count_roi
    
    return xrd_img


def keys_xrd_netcdf(fname,verbose=False):
    ## Prints keys and sizes of data for specified xrd netcdf file
    
    ## Reads data from array_data variable of netcdf file
    xrd_file = netcdf_open(fname,'r')

    print 'Available keys: ', xrd_file.variables.keys()
    print '   ...and keys of keys: [data, typecode, size, shape, dimensions]'
    print
    print 'Attr_IonChamberI0'
    print '    xrd_file.variables[\'Attr_IonChamberI0\'].data'
    if verbose:
        print xrd_file.variables['Attr_IonChamberI0'].data
    print '    xrd_file.variables[\'Attr_IonChamberI0\'].dimensions: ', xrd_file.variables['Attr_IonChamberI0'].dimensions
    print '    xrd_file.variables[\'Attr_IonChamberI0\'].shape: ', xrd_file.variables['Attr_IonChamberI0'].shape
    print
    print 'array_data'
    print '    xrd_file.variables[\'array_data\'].data'
    if verbose:
        print xrd_file.variables['array_data'].data
    print '    xrd_file.variables[\'array_data\'].dimensions: ', xrd_file.variables['array_data'].dimensions
    print '    xrd_file.variables[\'array_data\'].shape: ', xrd_file.variables['array_data'].shape
    print
    print 'timeStamp'
    print '    xrd_file.variables[\'timeStamp\'].data'
    if verbose:
        print xrd_file.variables['timeStamp'].data
    print '    xrd_file.variables[\'timeStamp\'].dimensions: ', xrd_file.variables['timeStamp'].dimensions
    print '    xrd_file.variables[\'timeStamp\'].shape: ', xrd_file.variables['timeStamp'].shape
    print
    print 'epicsTSNsec'
    print '    xrd_file.variables[\'epicsTSNsec\'].data'
    if verbose:
        print xrd_file.variables['epicsTSNsec'].data
    print '    xrd_file.variables[\'epicsTSNsec\'].dimensions: ', xrd_file.variables['epicsTSNsec'].dimensions
    print '    xrd_file.variables[\'epicsTSNsec\'].shape: ', xrd_file.variables['epicsTSNsec'].shape
    print
    print 'epicsTSSec'
    print '    xrd_file.variables[\'epicsTSSec\'].data'
    if verbose:
        print xrd_file.variables['epicsTSSec'].data
    print '    xrd_file.variables[\'epicsTSSec\'].dimensions: ', xrd_file.variables['epicsTSSec'].dimensions
    print '    xrd_file.variables[\'epicsTSSec\'].shape: ', xrd_file.variables['epicsTSSec'].shape
    print
    print 'uniqueId'
    print '    xrd_file.variables[\'uniqueId\'].data'
    if verbose:
        print xrd_file.variables['uniqueId'].data
    print '    xrd_file.variables[\'uniqueId\'].dimensions: ', xrd_file.variables['uniqueId'].dimensions
    print '    xrd_file.variables[\'uniqueId\'].shape: ', xrd_file.variables['uniqueId'].shape
    print
    print 'Attr_RingCurrent'
    print '    xrd_file.variables[\'Attr_RingCurrent\'].data'
    if verbose:
        print xrd_file.variables['Attr_RingCurrent'].data
    print '    xrd_file.variables[\'Attr_RingCurrent\'].dimensions: ', xrd_file.variables['Attr_RingCurrent'].dimensions
    print '    xrd_file.variables[\'Attr_RingCurrent\'].shape: ', xrd_file.variables['Attr_RingCurrent'].shape
    print
    print 'Attr_PhiMotorRBV'
    print '    xrd_file.variables[\'Attr_PhiMotorRBV\'].data'
    if verbose:
        print xrd_file.variables['Attr_PhiMotorRBV'].data
    print '    xrd_file.variables[\'Attr_PhiMotorRBV\'].dimensions: ', xrd_file.variables['Attr_PhiMotorRBV'].dimensions
    print '    xrd_file.variables[\'Attr_PhiMotorRBV\'].shape: ', xrd_file.variables['Attr_PhiMotorRBV'].shape


    xrd_file.close()

    return

def roi_xrd_netcdf(fname, frames, rev = False, verbose=False):


    ## Reads an XRD netCDF file with the netCDF plugin buffers
    if verbose:
        print '  reading : %s' % fname
    t0 = time.time()

    ## Reads an XRD netCDF file with the netCDF plugin buffers
    xrd_file = netcdf_open(fname,'r')
    t1 = time.time()
    xrd_data = xrd_file.variables['array_data'].data.copy()
    xrd_I0 = xrd_file.variables['Attr_IonChamberI0'].data.copy()
    data_shape = deepcopy(xrd_file.variables['array_data'].shape)
    xrd_file.close()
    t2 = time.time()

    xrd_frames = np.zeros([data_shape[-2],data_shape[-1]])
    
    ## Forces data into 3D shape
    shape = xrd_data.shape ## (no_images,pixels_x,pixels_y)
    if len(shape) == 2:
        print 'Reshaping to (%i, %i, %i)' % (1, shape[0], shape[1])
        xrd_data.shape = (1, shape[0], shape[1])

    ## Defines new variable in NCxrdDATA class
    XRDdata = NCxrdDATA(data_shape)


    ## Defines direction of scan based on row number
    XRDdata.I0 = xrd_I0[:,] if rev is False else xrd_I0[::-1,]
    XRDdata.XRDframes = xrd_data[:,] if rev is False else xrd_data[::-1,]
    t3 = time.time()
    
    ## Trims negative data
    XRDdata.XRDframes[XRDdata.XRDframes<0] = 0
    #XRDdata.XRDframes[XRDdata.XRDframes>100000] = 0
    t4 = time.time()
    
    ## Sorts for frames in ROI, excluding first 3 frames in row (over-exposed)
    for i,j in enumerate(frames):
        if j == 1 and i > 2:
            ## Normalize wrt I0
            xrd_frames += XRDdata.XRDframes[i,]/(xrd_I0[i]/7000.0)
    t5 = time.time()

    if verbose:
        print '\ttime to read file     = %7.1f ms' % ((t1-t0)*1000)
        print '\ttime to copy          = %7.1f ms' % ((t2-t1)*1000)
        print '\ttime to extract data  = %7.1f ms' % ((t3-t2)*1000)
        print '\ttime to trim data     = %7.1f ms' % ((t4-t3)*1000)
        print '\ttime to sum frames    = %7.1f ms' % ((t5-t4)*1000)
        print '\tTOTAL: %0.2f s' % (t5-t0)

    return xrd_frames

def test_read(fname):
    print( fname,  os.stat(fname))
    fd = read_xrd_netcdf(fname, verbose=True)
    print(fd.counts.shape)

def registerLarchPlugin():
    return ('_xrd', {'roi_xrd_netcdf': roi_xrd_netcdf})
    return ('_xrd', {'read_xrd_netcdf': read_xrd_netcdf})
    return ('_xrd', {'make_xrd_map': make_xrd_map})
