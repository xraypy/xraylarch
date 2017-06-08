#!/usr/bin/env python
'''
Diffraction functions that use pyFAI

mkak 2017.03.14
'''

##########################################################################
# IMPORT PYTHON PACKAGES
import numpy as np

HAS_pyFAI = False
try:
    import pyFAI
    HAS_pyFAI = True
except ImportError:
    pass

##########################################################################
# FUNCTIONS

def read_lambda(calfile):
    
    ai = pyFAI.load(calfile)
    return ai._wavelength*1e10 ## units A

def integrate_xrd_row(rowxrd2d, calfile, unit='q', steps=10001, wedge=1,
                      mask=None, dark=None, flip=True):

    '''
    Uses pyFAI (poni) calibration file to produce 1D XRD data from a row of 2D XRD images 

    Must provide pyFAI calibration file
    
    rowxrd2d : 2D diffraction images for integration
    calfile  : poni calibration file
    unit     : unit for integration data ('2th'/'q'); default is 'q'
    steps    : number of steps in integration data; default is 10000
    wedge    : azimuthal slices
    mask     : mask array for image
    dark     : dark image array
    flip     : vertically flips image to correspond with Dioptas poni file calibration
    '''
    if HAS_pyFAI:
        try:
            ai = pyFAI.load(calfile)
        except:
            print('Provided calibration file could not be loaded.')
            return
        
        attrs = {'mask':mask,'dark':dark}
        if unit.startswith('2th'):
            attrs.update({'unit':'2th_deg'})
        else:
            attrs.update({'unit':'q_A^-1'})
        if wedge != 1:
            xrd1d = np.zeros((np.shape(rowxrd2d)[0],(wedge+1)*2,steps))

            ii = 0            
            if flip:
                xrd1d[:,ii:(ii+2),:] = [calcXRD1d(xrd2d[::-1,:],ai,steps,attrs) for i,xrd2d in enumerate(rowxrd2d)]        
            else:
                xrd1d[:,ii:(ii+2),:] = [calcXRD1d(xrd2d,ai,steps,attrs) for i,xrd2d in enumerate(rowxrd2d)]
            
            slice = 360./wedge            
            for nslc in np.arange(wedge):
                start = -180+(nslc*slice)
                end = start+(nslc*slice)
                azimuth_range = (start,end)
                attrs.update({'azimuth_range':azimuth_range})
                ii += 2

                if flip:
                    xrd1d[:,ii:(ii+2),:] = [calcXRD1d(xrd2d[::-1,:],ai,steps,attrs) for i,xrd2d in enumerate(rowxrd2d)]
                else:
                    xrd1d[:,ii:(ii+2),:] = [calcXRD1d(xrd2d,ai,steps,attrs) for i,xrd2d in enumerate(rowxrd2d)]

            return xrd1d


        
        else:
            if flip:
                return [calcXRD1d(xrd2d[::-1,:],ai,steps,attrs) for i,xrd2d in enumerate(rowxrd2d)]        
            else:
                return [calcXRD1d(xrd2d,ai,steps,attrs) for i,xrd2d in enumerate(rowxrd2d)]

    else:
        print('pyFAI not imported. Cannot calculate 1D integration.')

def integrate_xrd(xrd2d, calfile, unit='q', steps=10000, file='', mask=None, dark=None,
                  verbose=False):
    '''
    Uses pyFAI (poni) calibration file and 2D XRD image to produce 1D XRD data

    Must provide pyFAI calibration file
    
    xrd2d    : 2D diffraction images for integration
    calfile  : poni calibration file
    unit     : unit for integration data ('2th'/'q'); default is 'q'
    steps    : number of steps in integration data; default is 10000
    file     : filename for saving data; if '' (default) will not save
    mask     : mask array for image
    dark     : dark image array
    '''
    
    if HAS_pyFAI:
        try:
            ai = pyFAI.load(calfile)
        except:
            print('Provided calibration file could not be loaded.')
            return
        
        attrs = {}
        if unit.startswith('2th'):
            attrs.update({'unit':'2th_deg'})
        else:
            attrs.update({'unit':'q_A^-1'})
        if mask:
            if np.shape(mask) == np.shape(xrd2d): attrs.update({'mask':mask})
        if dark:
            if np.shape(dark) == np.shape(xrd2d): attrs.update({'dark':dark})        

        if file is not '':
            if verbose:
                print('\nSaving %s data to file: %s' % (unit,file))
            attrs.update({'filename':file})
        return calcXRD1d(xrd2d,ai,steps,attrs)
    else:
        print('pyFAI not imported. Cannot calculate 1D integration.')

def calc_cake(xrd2d, calfile, unit='q', mask=None, dark=None, verbose=False):
    
    if HAS_pyFAI:
        try:
            ai = pyFAI.load(calfile)
        except:
            print('Provided calibration file could not be loaded.')
            return
        
        attrs = {}
        if unit.startswith('2th'):
            attrs.update({'unit':'2th_deg'})
        else:
            attrs.update({'unit':'q_A^-1'})
        if mask:
            if np.shape(mask) == np.shape(xrd2d): attrs.update({'mask':mask})
        if dark:
            if np.shape(dark) == np.shape(xrd2d): attrs.update({'dark':dark})        

        return calcXRDcake(xrd2d,ai,attrs)
        
    else:
        print('pyFAI not imported. Cannot calculate 1D integration.')

def calcXRD1d(xrd2d,ai,steps,attrs):
    return ai.integrate1d(xrd2d,steps,**attrs)

def calcXRDcake(xrd2d,ai,attrs):
    return ai.integrate2d(xrd2d,2048,2048,**attrs) ## returns I,q,eta
                    
def registerLarchPlugin():
    return ('_xrd', {'integrate_xrd': integrate_xrd}) #,'calculate_ai': calculate_ai})
