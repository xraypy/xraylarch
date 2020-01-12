#!/usr/bin/env python
'''
Diffraction functions that use pyFAI

mkak 2017.03.14
'''

##########################################################################
# IMPORT PYTHON PACKAGES
import os
import numpy as np

HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.units
    HAS_pyFAI = True
except ImportError:
    pass

from larch.io import tifffile

##########################################################################
# FUNCTIONS

def return_ai(calfile):

    if calfile is not None and os.path.exists(calfile):
        return pyFAI.load(calfile)

def q_from_xy(x, y, ai=None, calfile=None):

    if ai is None: ai = pyFAI.load(calfile)

    try:
        return ai.qFunction(np.array([y,]),np.array([x,]))[0]
    except:
        return 0

def twth_from_xy(x, y, ai=None, calfile=None, ang_units='degrees'):

    if ai is None: ai = pyFAI.load(calfile)

    try:
        twth = ai.tth(np.array([y,]),np.array([x,]))
    except:
        return 0

    if ang_units.startswith('rad'):
        return twth[0]
    else:
        return np.degrees(twth[0])

def eta_from_xy(x, y, ai=None, calfile=None, ang_units='degrees'):

    if ai is None: ai = pyFAI.load(calfile)

    try:
        eta = ai.chi(np.array([y,]),np.array([x,]))
    except:
        return 0

    if ang_units.startswith('rad'):
        return eta[0]
    else:
        return np.degrees(eta[0])

def read_lambda(calfile):

    ai = pyFAI.load(calfile)
    return ai._wavelength*1e10 ## units A

def integrate_xrd_row(rowxrd2d, calfile, unit='q', steps=2048,
                      wedge_limits=None, mask=None, dark=None,
                      flip=True):
    '''
    Uses pyFAI (poni) calibration file to produce 1D XRD data from a row of 2D XRD images

    Must provide pyFAI calibration file

    rowxrd2d     : 2D diffraction images for integration
    calfile      : poni calibration file
    unit         : unit for integration data ('2th'/'q'); default is 'q'
    steps        : number of steps in integration data; default is 10000
    wedge_limits : azimuthal slice limits
    mask         : mask array for image
    dark         : dark image array
    flip         : vertically flips image to correspond with Dioptas poni file calibration
    '''

    if not HAS_pyFAI:
        print('pyFAI not imported. Cannot calculate 1D integration.')
        return

    try:
        ai = pyFAI.load(calfile)
    except:
        print('calibration file "%s" could not be loaded.' % calfile)
        return

    if type(dark) is str:
        try:
            dark = np.array(tifffile.imread(xrd2dbkgd))
        except:
            dark = None

    dir = -1 if flip else 1
    attrs = dict(mask=mask, dark=dark, method='csr',
             polarization_factor=0.999, correctSolidAngle=True)

    if unit.startswith('2th'):
        attrs.update({'unit':'2th_deg'})
    else:
        attrs.update({'unit':'q_A^-1'})

    if wedge_limits is not None:
        attrs.update({'azimuth_range':wedge_limits})

    # print("Calc XRD 1D for row", ai, steps, attrs)
    q, xrd1d = [], []
    for i, xrd2d in enumerate(rowxrd2d):
        row_q,row_xrd1d = calcXRD1d(xrd2d[::dir,:], ai, steps, attrs)
        q     += [row_q]
        xrd1d += [row_xrd1d]

    return np.array(q), np.array(xrd1d)

def integrate_xrd(xrd2d, calfile, unit='q', steps=2048, file='',  wedge_limits=None,
                  mask=None, dark=None, is_eiger=True, save=False, verbose=False):
    '''
    Uses pyFAI (poni) calibration file and 2D XRD image to produce 1D XRD data

    Must provide pyFAI calibration file

    xrd2d        : 2D diffraction images for integration
    calfile      : poni calibration file
    unit         : unit for integration data ('2th'/'q'); default is 'q'
    steps        : number of steps in integration data; default is 10000
    wedge_limits : azimuthal slice limits
    file         : filename for saving data; if '' (default) will not save
    mask         : mask array for image
    dark         : dark image array
    '''

    if HAS_pyFAI:
        try:
            ai = pyFAI.load(calfile)
        except:
            print('Provided calibration file could not be loaded.')
            return
    else:
        print('pyFAI not imported. Cannot calculate 1D integration.')
        return

    attrs = {}
    if unit.startswith('2th'):
        attrs.update({'unit':'2th_deg'})
    else:
        attrs.update({'unit':'q_A^-1'})

    if wedge_limits is not None:
        attrs.update({'azimuth_range':wedge_limits})

    if mask:
        if np.shape(mask) == np.shape(xrd2d): attrs.update({'mask':mask})
    if dark:
        if np.shape(dark) == np.shape(xrd2d): attrs.update({'dark':dark})

    if file != '':
        if verbose:
            print('\nSaving %s data to file: %s' % (unit,file))
        attrs.update({'filename':file})
    return calcXRD1d(xrd2d, ai, steps, attrs)


def calc_cake(xrd2d, calfile, unit='q', mask=None, dark=None,
              xsteps=2048, ysteps=2048, verbose=False):

    if HAS_pyFAI:
        try:
            ai = pyFAI.load(calfile)
        except:
            print('Provided calibration file could not be loaded.')
            return
    else:
        print('pyFAI not imported. Cannot calculate 1D integration.')
    attrs = {}
    if unit.startswith('2th'):
        attrs.update({'unit':'2th_deg'})
    else:
        attrs.update({'unit':'q_A^-1'})
    if mask:
        if np.shape(mask) == np.shape(xrd2d): attrs.update({'mask':mask})
    if dark:
        if np.shape(dark) == np.shape(xrd2d): attrs.update({'dark':dark})

    return calcXRDcake(xrd2d, ai, xsteps, ysteps, attrs)


def calcXRD1d(xrd2d ,ai, steps, attrs):
    return ai.integrate1d(xrd2d, steps, **attrs)

def calcXRDcake(xrd2d,ai,xstp,ystp,attrs):
    return ai.integrate2d(xrd2d,xstp,ystp,**attrs) ## returns I,q,eta

def save1D(filename, xaxis, I, error=None, xaxis_unit=None, calfile=None,
           has_dark=False, has_flat=False, polarization_factor=None,
           normalization_factor=None):
    '''
    copied and modified from pyFAI/io.py
    '''
    if xaxis_unit is None or xaxis_unit == 'q':
        xaxis_unit = pyFAI.units.Q_A
    elif xaxis_unit.startswith('2th'):
        xaxis_unit = pyFAI.units.TTH_DEG

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
        if polarization_factor is None:
            try:
                polarization_factor = ai._polarization_factor
            except:
                pass
        headerLst.append('Polarization factor: %s' % polarization_factor)
        headerLst.append('Normalization factor: %s' % normalization_factor)
    else:
        headerLst = ' '

    return '\n'.join([hdr + ' ' + i for i in headerLst])
