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
    import pyFAI.units
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
                start = -180 + nslc*slice
                end   = start+slice
                attrs.update({'azimuth_range':(start,end)})
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

def save1D(filename, xaxis, I, error=None, xaxis_unit=None, calfile=None,
           has_dark=False, has_flat=False, polarization_factor=None, normalization_factor=None):
    '''
    copied and modified from pyFAI/io.py
    '''
    if xaxis_unit is None:
        xaxis_unit = pyFAI.units.Q_A
    if calfile is None:
        ai = None
    else:
        ai = pyFAI.load(calfile)

    xaxis_unit = pyFAI.units.to_unit(xaxis_unit)
    with open(filename, 'w') as f:
        f.write(make_headers(has_dark=has_dark, has_flat=has_flat, ai=ai,
                                 polarization_factor=polarization_factor,
                                 normalization_factor=normalization_factor))
        try:
            f.write('\n# --> %s\n' % (filename))
        except UnicodeError:
            f.write('\n# --> %s\n' % (filename.encode('utf8')))
        if error is None:
            try:
                f.write('#%14s %14s\n' % (xaxis_unit.REPR, 'I '))
            except:
                f.write('#%14s %14s\n' % (xaxis_unit.name, 'I '))
            f.write('\n'.join(['%14.6e  %14.6e' % (t, i) for t, i in zip(xaxis, I)]))
        else:
            f.write('#%14s  %14s  %14s\n' %
                    (xaxis_unit.REPR, 'I ', 'sigma '))
            f.write('\n'.join(['%14.6e  %14.6e %14.6e' % (t, i, s) for t, i, s in zip(xaxis, I, error)]))
        f.write('\n')

def make_headers(hdr='#', has_dark=False, has_flat=False, ai=None,
                 polarization_factor=None, normalization_factor=None):
    '''
    copied and modified from pyFAI/io.py
    '''
    if ai is not None:
        headerLst = ['== pyFAI calibration ==']
        headerLst.append('SplineFile: %s' % ai.splineFile)
        headerLst.append('PixelSize: %.3e, %.3e m' %
                         (ai.pixel1, ai.pixel2))
        headerLst.append('PONI: %.3e, %.3e m' % (ai.poni1, ai.poni2))
        headerLst.append('Distance Sample to Detector: %s m' %
                         ai.dist)
        headerLst.append('Rotations: %.6f %.6f %.6f rad' %
                         (ai.rot1, ai.rot2, ai.rot3))
        headerLst += ['', '== Fit2d calibration ==']

        f2d = ai.getFit2D()
        headerLst.append('Distance Sample-beamCenter: %.3f mm' %
                         f2d['directDist'])
        headerLst.append('Center: x=%.3f, y=%.3f pix' %
                         (f2d['centerX'], f2d['centerY']))
        headerLst.append('Tilt: %.3f deg  TiltPlanRot: %.3f deg' %
                         (f2d['tilt'], f2d['tiltPlanRotation']))
        headerLst.append('')

        if ai._wavelength is not None:
            headerLst.append('Wavelength: %s' % ai.wavelength)
        if ai.maskfile is not None:
            headerLst.append('Mask File: %s' % ai.maskfile)
        if has_dark or (ai.darkcurrent is not None):
            if ai.darkfiles:
                headerLst.append('Dark current: %s' % ai.darkfiles)
            else:
                headerLst.append('Dark current: Done with unknown file')
        if has_flat or (ai.flatfield is not None):
            if ai.flatfiles:
                headerLst.append('Flat field: %s' % ai.flatfiles)
            else:
                headerLst.append('Flat field: Done with unknown file')
        if polarization_factor is None and ai._polarization is not None:
            polarization_factor = ai._polarization_factor
        headerLst.append('Polarization factor: %s' % polarization_factor)
        headerLst.append('Normalization factor: %s' % normalization_factor)
    else:
        headerLst = ' '

    return '\n'.join([hdr + ' ' + i for i in headerLst])

                    
def registerLarchPlugin():
    return ('_xrd', {'integrate_xrd': integrate_xrd}) #,'calculate_ai': calculate_ai})
