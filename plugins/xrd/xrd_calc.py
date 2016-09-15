#!/usr/bin/env python
"""
Wrapper for pyFAI integration and saving of xy 1D XRD data
mkak 2016.07.06 // updated 2013.08.23
"""
import time
import os

#import fabio
#from pyFAI.multi_geometry import MultiGeometry

HAS_pyFAI = False
try:
    import pyFAI
    HAS_pyFAI = True
except ImportError:
    pass

import numpy as np
import math

def integrate_xrd(xrd_map, AI=None, calfile=None, unit='q', steps=10000, 
                  save=True, aname = 'default', prefix = 'XRD', path = '~/',
                  mask=None, dark=None, verbose=False):

    if HAS_pyFAI:
        if AI is None:
            try:
                ai = pyFAI.load(calfile)
            except IOError:
                print('No calibration parameters specified.')
                return
        else:
            ai = calculate_ai(AI)
        
        if unit == 'q':
            iunit = 'q_A^-1'
        elif unit == '2th':
            iunit='2th_deg'
        else:
            print('Unknown unit: %s. Using q.' % unit)
            unit = 'q'
            iunit = 'q_A^-1'

        t0 = time.time()
    
        if save:
            counter = 1
            while os.path.exists('%s/%s-%s-%03d.xy' % (path,prefix,aname,counter)):
                counter += 1
            fname = '%s/%s-%s-%03d.xy' % (path,prefix,aname,counter)
            print('\nSaving %s data in file: %s\n' % (unit,fname))
            qI = ai.integrate1d(xrd_map,steps,unit=iunit,mask=mask,dark=dark,filename=fname)
        else:
            qI = ai.integrate1d(xrd_map,steps,unit=iunit,mask=mask,dark=dark)
        t1 = time.time()
        if verbose:
            print('\ttime to integrate data = %0.3f s' % ((t1-t0)))

        if verbose:
            print('Parameters for 1D integration:')
            print(ai)
    else:
        print('pyFAI not imported. Cannot calculate 1D integration without it.')
        return

    return qI

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
                                   

def calc_q_to_d(q):
    return (2.*math.pi)/q

def calc_q_to_2th(q,wavelength,units='degrees'):
    twth = 2.*np.arcsin((q*wavelength)/(4.*math.pi))
    if units == 'radians':
        return twth
    else:
        return np.degrees(twth)

def calc_d_to_q(d):
    return (2.*math.pi)/d

def calc_2th_to_q(twth,wavelength,units='degrees'):
    if units == 'degrees':
        twth = np.radians(twth)
    return ((4.*math.pi)/wavelength)*np.sin(twth/2.)
    