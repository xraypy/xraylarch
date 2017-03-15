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
    import pyFAI.calibrant
    # from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass

##########################################################################
# FUNCTIONS

def integrate_xrd(xrd_map, ai=None,AI=None, calfile=None, unit='q', steps=10000, 
                  file='', mask=None, dark=None):
    '''
    Uses pyFAI (poni) calibration file and 2D XRD image to produce 1D XRD data

    Must provide one of following: ai, AI, or calfile
    
    ai      : pyFAI calibration file group
    AI      : hdf5 group with calibration information 
    calfile : poni calibration file
    unit    : unit for integration data ('2th'/'q'); default is 'q'
    steps   : number of steps in integration data; default is 10000
    file    : filename for saving data; if '' (default) will not save
    mask    : mask array for image
    dark    : dark image array
    '''

    if HAS_pyFAI:
        if ai is None:
            if AI is None:
                try:
                    ai = pyFAI.load(calfile)
                except IOError:
                    print('No calibration parameters specified.')
                    return
            else:
                ai = calculate_ai(AI)
        
        attrs = {}
        if unit.startswith('2th'):
            attrs.update({'unit':'2th_deg'})
        else:
            attrs.update({'unit':'q_A^-1'})
        if mask:
            if np.shape(mask) == np.shape(xrd_map): attrs.update({'mask':mask})
        if dark:
            if np.shape(dark) == np.shape(xrd_map): attrs.update({'dark':dark})        
        if file is not '':
            print('\nSaving %s data to file: %s' % (unit,file))
            attrs.update({'filename':file})

        return ai.integrate1d(xrd_map,steps,**attrs)

    else:
        print('pyFAI not imported. Cannot calculate 1D integration.')
        return

def calculate_ai(AI):
    '''
    Builds ai structure using AzimuthalIntegrator from hdf5 parameters
    mkak 2016.08.30
    '''

    if HAS_pyFAI:
        try:
            distance = float(AI.attrs['distance'])
        except:
            distance = 1
     
        ## Optional way to shorten this script... will need to change units of pixels
        ## mkak 2016.08.30   
        #floatattr = ['poni1','poni2','rot1','rot2','rot3','pixel1','pixel2']
        #valueattr = np.empty(7)
        #for f,fattr in enumerate(floatattr):
        #     try:
        #         valueattr[f] = float(AI.attr[fattr])
        #     except:
        #         valueattr[f] =  0
    
        try:
            poni_1 = float(AI.attrs['poni1'])
        except:
            poni_1 = 0
        try:
            poni_2 = float(AI.attrs['poni2'])
        except:
            poni_2 = 0
        
        try:
            rot_1 = float(AI.attrs['rot1'])
        except:
            rot_1 = 0
        try:
            rot_2 = float(AI.attrs['rot2'])
        except:
            rot_2 = 0
        try:
            rot_3 = float(AI.attrs['rot3'])
        except:
            rot_3 = 0

        try:
            pixel_1 = float(AI.attrs['ps1'])
        except:
            pixel_1 = 0
        try:
            pixel_2 = float(AI.attrs['ps2'])
        except:
            pixel_2 = 0

        try:
            spline = AI.attrs['spline']
            if spline == '':
                spline = None
        except:
            spline = None
        
        try:
            detname = AI.attrs['detector']
            if detname == '':
                detname = None
        except:
            detname = None
    
        try:
            xraylambda =float(AI.attrs['wavelength'])
        except:
            xraylambda = None
    else:
        print('pyFAI not imported. Cannot calculate ai for calibration.')
        return

        
    return pyFAI.AzimuthalIntegrator(dist = distance, poni1 = poni_1, poni2 = poni_2,
                                    rot1 = rot_1, rot2 = rot_2, rot3 = rot_3,
                                    pixel1 = pixel_1, pixel2 = pixel_2,
                                    splineFile = spline, detector = detname,
                                    wavelength = xraylambda)
#########################################################################

                     
def registerLarchPlugin():
    return ('_xrd', {'integrate_xrd': integrate_xrd,
                      'calculate_ai': calculate_ai
                      })
