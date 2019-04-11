#!/usr/bin/env python
'''
Diffraction functions require for fitting and analyzing data.

mkak 2017.02.06 (originally written spring 2016)
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import math
import numpy as np

from ..utils.physical_constants import PLANCK_HC

import re
import os
import cmath

HAS_CifFile = False
try:
    import CifFile
    HAS_CifFile = True
except ImportError:
    pass

##########################################################################
# FUNCTIONS

def d_from_q(q):
    '''
    Converts q axis into d (returned units inverse of provided units)
    d = 2*PI/q
    '''
    return (2.*math.pi)/q

def d_from_twth(twth,wavelength,ang_units='degrees'):
    '''
    Converts 2th axis into d (returned units same as wavelength units)
    d = lambda/[2*sin(2th/2)]

    ang_unit : default in degrees; will convert from 'rad' if given
    '''
    if not ang_units.startswith('rad'):
        twth = np.radians(twth)
    return wavelength/(2*np.sin(twth/2.))


def twth_from_d(d,wavelength,ang_units='degrees'):
    '''
    Converts d axis into 2th (d and wavelength must be in same units)
    2th = 2*sin^-1(lambda/[2*d])

    ang_unit : default in degrees; will convert to 'rad' if given
    '''
    twth = 2.*np.arcsin(wavelength/(2.*d))
    if ang_units.startswith('rad'):
        return twth
    else:
        return np.degrees(twth)


def twth_from_q(q,wavelength,ang_units='degrees'):
    '''
    Converts q axis into 2th (q and wavelength will have inverse units)
    2th = 2*sin^-1(lambda/[2*d])

    ang_unit : default in degrees; will convert to 'rad' if given
    '''
    twth = 2.*np.arcsin((q*wavelength)/(4.*math.pi))
    if ang_units.startswith('rad'):
        return twth
    else:
        return np.degrees(twth)


def q_from_d(d):
    '''
    Converts d axis into q (returned units inverse of provided units)
    q = 2*PI/d
    '''
    return (2.*math.pi)/d


def q_from_twth(twth,wavelength,ang_units='degrees'):
    '''
    Converts 2th axis into q (q returned in inverse units of wavelength)
    q = [(4*PI)/lamda]*sin(2th/2)

    ang_unit : default in degrees; will convert from 'rad' if given
    '''
    if not ang_units.startswith('rad'):
        twth = np.radians(twth)
    return ((4.*math.pi)/wavelength)*np.sin(twth/2.)

def qv_from_hkl(hklall,a,b,c,alp,bet,gam):

    qv = np.zeros(np.shape(hklall))
    uvol = unit_cell_volume(a,b,c,alp,bet,gam)

    alp,bet,gam = np.radians(alp),np.radians(bet),np.radians(gam)
    q0 = [(b*c*np.sin(alp))/uvol,(c*a*np.sin(bet))/uvol,(a*b*np.sin(gam))/uvol]

    for i,hkl in enumerate(hklall):
        qv[i] = [2*math.pi*hkl[0]*q0[0],
                 2*math.pi*hkl[1]*q0[1],
                 2*math.pi*hkl[2]*q0[2]]
    return qv

def d_from_hkl(hklall,a,b,c,alp,bet,gam):

    d = np.zeros(len(hklall))
    alp,bet,gam = np.radians(alp),np.radians(bet),np.radians(gam)
    for i,hkl in enumerate(hklall):
        h,k,l = hkl
        x = 1-np.cos(alp)**2 - np.cos(bet)**2 - np.cos(gam)**2 \
                + 2*np.cos(alp)*np.cos(bet)*np.cos(gam)
        y =   (h*np.sin(alp)/a)**2 + 2*k*l*(np.cos(bet)*np.cos(gam)-np.cos(alp))/(b*c) \
            + (k*np.sin(bet)/b)**2 + 2*l*h*(np.cos(gam)*np.cos(alp)-np.cos(bet))/(c*a) \
            + (l*np.sin(gam)/c)**2 + 2*h*k*(np.cos(alp)*np.cos(bet)-np.cos(gam))/(a*b)
        d[i] = np.sqrt(x/y)

    return d

def unit_cell_volume(a,b,c,alp,bet,gam):

    alp,bet,gam = np.radians(alp),np.radians(bet),np.radians(gam)
    return a*b*c*(1-np.cos(alp)**2-np.cos(bet)**2-np.cos(gam)**2+2*np.cos(alp)*np.cos(bet)*np.cos(gam))**0.5


def E_from_lambda(wavelength,E_units='keV',lambda_units='A'):
    '''
    Converts lambda into energy
    E = hf ; E = hc/lambda

    E_units      : default keV; can convert to 'eV' if given
    lambda_units : default 'A'; can convert from 'm' or 'nm' if given
    '''
    if lambda_units == 'm':
        wavelength = wavelength*1e10
    elif lambda_units == 'nm':
        wavelength = wavelength*1e1
    if E_units.lower() == 'kev':
        return PLANCK_HC/wavelength*1e-3 # keV
    else:
        return (PLANCK_HC/wavelength)    # eV


def lambda_from_E(E, E_units='keV', lambda_units='A'):
    '''
    Converts lambda into energy
    E = hf ; E = hc/lambda

    E_units      : default keV; can convert from 'eV' if given
    lambda_units : default 'A'; can convert to 'm' or 'nm' if given
    '''
    if E_units.lower() != 'kev':
        E = E*1e-3 # keV
    if lambda_units == 'm':
        return (PLANCK_HC/E)*1e-13
    elif lambda_units == 'nm':
        return (PLANCK_HC/E)*1e-4
    else:
        return PLANCK_HC/E*1e-3 # A

def generate_hkl(hmax=10,kmax=10,lmax=10,positive_only=True):
    if positive_only is True:
        hklall = np.mgrid[0:hmax+1, 0:kmax+1, 0:lmax+1].reshape(3, -1).T
    else:
        hklall = np.mgrid[-hmax:hmax+1, -kmax:kmax+1, -lmax:lmax+1].reshape(3, -1).T
    return np.array([hkl for hkl in hklall if hkl[0]**2 + hkl[1]**2 + hkl[2]**2 > 0])
