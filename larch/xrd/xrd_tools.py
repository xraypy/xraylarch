#!/usr/bin/env python
'''
Diffraction functions require for fitting and analyzing data.

mkak 2017.02.06 (originally written spring 2016)
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import math
import numpy as np
from numpy import cos, sin, arcsin,  degrees
from ..utils.physical_constants import PLANCK_HC, TAU, DEG2RAD, RAD2DEG

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
    return TAU/q

def d_from_twth(twth,wavelength,ang_units='degrees'):
    '''
    Converts 2th axis into d (returned units same as wavelength units)
    d = lambda/[2*sin(2th/2)]

    ang_unit : default in degrees; will convert from 'rad' if given
    '''
    if not ang_units.startswith('rad'):
        twth = DEG2RAD*twth
    return wavelength/(2*sin(twth/2.))


def twth_from_d(d,wavelength,ang_units='degrees'):
    '''
    Converts d axis into 2th (d and wavelength must be in same units)
    2th = 2*sin^-1(lambda/[2*d])

    ang_unit : default in degrees; will convert to 'rad' if given
    '''
    twth = 2*arcsin(wavelength/(2.*d))
    if ang_units.startswith('rad'):
        return twth
    else:
        return RAD2DEG*twth


def twth_from_q(q,wavelength,ang_units='degrees'):
    '''
    Converts q axis into 2th (q and wavelength will have inverse units)
    2th = 2*sin^-1(lambda/[2*d])

    ang_unit : default in degrees; will convert to 'rad' if given
    '''
    twth = 2*arcsin((q*wavelength)/(2*TAU))
    if ang_units.startswith('rad'):
        return twth
    else:
        return RAD2DEG*twth

def q_from_d(d):
    '''
    Converts d axis into q (returned units inverse of provided units)
    q = 2*PI/d
    '''
    return TAU/d


def q_from_twth(twth, wavelength, ang_units='degrees'):
    '''
    Converts 2th axis into q (q returned in inverse units of wavelength)
    q = [(4*PI)/lamda]*sin(2th/2)

    ang_unit : default in degrees; will convert from 'rad' if given
    '''
    if not ang_units.startswith('rad'):
        twth = DEG2RAD*twth
    return ((2*TAU)/wavelength)*sin(twth/2.)

def qv_from_hkl(hklall, a, b, c, alpha, beta, gamma):

    qv = np.zeros(np.shape(hklall))
    uvol = unit_cell_volume(a,b,c,alpha,beta,gamma)
    alpha, beta, gamma = DEG2RAD*alpha, DEG2RAD*beta, DEG2RAD*gamma
    q0 = [(b*c*sin(alpha))/uvol,(c*a*sin(beta))/uvol,(a*b*sin(gamma))/uvol]

    for i, hkl in enumerate(hklall):
        qv[i] = [TAU*hkl[0]*q0[0], TAU*hkl[1]*q0[1], TAU*hkl[2]*q0[2]]
    return qv

def d_from_hkl(hkl, a, b, c, alpha, beta, gamma):
    h, k, l = hkl[:, 0], hkl[:, 1], hkl[:, 2]
    alpha, beta, gamma = DEG2RAD*alpha, DEG2RAD*beta, DEG2RAD*gamma
    x = 1-cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 \
        + 2*cos(alpha)*cos(beta)*cos(gamma)
    y = (h*sin(alpha)/a)**2 + 2*k*l*(cos(beta)*cos(gamma)-cos(alpha))/(b*c) + \
        (k*sin(beta)/b)**2 + 2*l*h*(cos(gamma)*cos(alpha)-cos(beta))/(c*a) + \
        (l*sin(gamma)/c)**2 + 2*h*k*(cos(alpha)*cos(beta)-cos(gamma))/(a*b)
    d = np.sqrt(x/y)
    return d

def d_from_hkl_orig(hklall, a, b, c, alpha, beta, gamma):
    d = np.zeros(len(hklall))
    alpha, beta, gamma = DEG2RAD*alpha, DEG2RAD*beta, DEG2RAD*gamma
    for i,hkl in enumerate(hklall):
        h,k,l = hkl
        x = 1-cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 \
            + 2*cos(alpha)*cos(beta)*cos(gamma)
        y = (h*sin(alpha)/a)**2 + 2*k*l*(cos(beta)*cos(gamma)-cos(alpha))/(b*c) \
            + (k*sin(beta)/b)**2 + 2*l*h*(cos(gamma)*cos(alpha)-cos(beta))/(c*a) \
            + (l*sin(gamma)/c)**2 + 2*h*k*(cos(alpha)*cos(beta)-cos(gamma))/(a*b)
        d[i] = np.sqrt(x/y)
    return d

def unit_cell_volume(a, b, c, alpha, beta, gamma):
    alpha, beta, gamma = DEG2RAD*alpha, DEG2RAD*beta, DEG2RAD*gamma
    return a*b*c*(1-cos(alpha)**2-cos(beta)**2-cos(gamma)**2+
                  2*cos(alpha)*cos(beta)*cos(gamma))**0.5


def E_from_lambda(wavelength, E_units='keV', lambda_units='A'):
    '''
    Converts lambda into energy
    E = hf ; E = hc/lambda

    E_units      : default keV; can convert to 'eV' if given
    lambda_units : default 'A'; can convert from 'm' or 'nm' if given
    '''
    if lambda_units == 'm':
        wavelength = wavelength*1e10
    elif lambda_units == 'nm':
        wavelength = wavelength*10
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
    scale = 1.e-3
    if lambda_units == 'm':
        scale = 1.e-13
    elif lambda_units == 'nm':
        scale = 1e-4
    return scale*PLANCK_HC/E

def generate_hkl(hmax=15, kmax=15, lmax=15, positive_only=True):
    if positive_only:
        hklall = np.mgrid[0:hmax+1, 0:kmax+1, 0:lmax+1].reshape(3, -1).T
    else:
        hklall = np.mgrid[-hmax:hmax+1, -kmax:kmax+1, -lmax:lmax+1].reshape(3, -1).T
    return np.array([hkl for hkl in hklall if hkl[0]**2 + hkl[1]**2 + hkl[2]**2 > 0])
