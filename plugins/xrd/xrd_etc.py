#!/usr/bin/env python
'''
Diffraction functions require for fitting and analyzing data.

mkak 2017.02.06 (originally written spring 2016)
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import math
import numpy as np
from scipy import constants

##########################################################################
# GLOBAL CONSTANTS

hc = constants.value(u'Planck constant in eV s')*constants.c*1e7 ## units: keV-A



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
    Converts d axis into 2th (d and wavelength must be in same units)
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
        return hc/wavelength
    else:
        return (hc/wavelength)*1e3 # eV


def lambda_from_E(E,E_units='keV',lambda_units='A'):
    '''
    Converts lambda into energy
    E = hf ; E = hc/lambda

    E_units      : default keV; can convert from 'eV' if given
    lambda_units : default 'A'; can convert to 'm' or 'nm' if given
    '''
    if E_units.lower() != 'kev':
        E = E*1e-3 # keV
    if lambda_units == 'm':
        return (hc/E)*1e-10
    elif lambda_units == 'nm':
        return (hc/E)*1e-1
    else:
        return hc/E # A

                   

MODDOC = '''

Functions for manipulating and analyzing x-ray diffraction
data.

The data and functions here include (but are not limited to):

member name     description
------------    ------------------------------
peakfinder      identifies peaks in x,y data
peakfilter      filters a set of data below a certain threshold
peaklocater     cross-references data for a give coordinates

'''

def initializeLarchPlugin(_larch=None):
   ''' initialize xrd '''
   if _larch is not None:
       mod = getattr(_larch.symtable, '_xrd')
       mod.__doc__ = MODDOC
                     

def registerLarchPlugin():
    return ('_xrd', {'d_from_q': d_from_q,
                     'd_from_twth': d_from_twth,
                     'twth_from_d': twth_from_d,
                     'twth_from_q': twth_from_q,
                     'q_from_d': q_from_d,
                     'q_from_twth': q_from_twth,
                     'E_from_lambda': E_from_lambda,
                     'lambda_from_E': lambda_from_E
                      })
