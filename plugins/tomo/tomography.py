<<<<<<< HEAD
# '''
# This module defines a tomography dataset class.
# 
# Authors/Modifications:
# ----------------------
# * Margaret Koker, koker@cars.uchicago.edu
# * modeled after MCA class
# '''
# 
# ##########################################################################
# # IMPORT PYTHON PACKAGES
# 
# import numpy as np
# 
# import os
# import sys
# 
# HAS_tomopy = False
# HAS_scikit = False
# try:
#     import tomopy
#     HAS_tomopy = True
# except ImportError:
#     try:
#         from skimage.transform import radon, iradon, iradon_sart
#         HAS_scikit = True
#     except:
#         pass
# 
# HAS_larch = False
# try:
#     from larch import Group
#     grpobjt = Group
#     HAS_larch = True
# except:
#     grpobjt = object
# 
# ##########################################################################
# # CLASSES
# 
# class tomogrp(grpobjt):
#     '''
#     Tomography dataset class
#     
#     Attributes:
#     ------------
# 
#     # Raw data and collection parameters
#     * self.x_range       = None or array          # x-range for sampled data
#     * self.omega_range   = None or array          # omega-range for sampled data
#     * self.z_range       = None or array          # z-range for sampled data (slices)
#     * self.data_range    = None or array          # range for data sampling (e.g. 2th, E)
# 
#     * self.x_units       = 'um'|'mm'|'m'|...      # units for x-range
#     * self.omega_units   = 'degrees'|'radians     # units for omega-range
#     * self.z_units       = 'um'|'mm'|'m'|...      # units for z-range
#     * self.data_units    = 'degrees'|'eV'|...     # units for data sampling
# 
#     * self.dark          = None or array          # dark for tomography comparison
#     * self.flat          = None or array          # flat image for tomography
# 
#     * self.sinogram      = None or array          # raw data collected [xi,omei,datai,zi]
# 
#     # Data fitting parameters
#     * self.rot_center    = 100                    # rotation center along x-axis (pixel number)
#     
#     # Analysis
#     * self.recon         = None or array          # tomographic reconstruction
# 
#     mkak 2017.07.07
#     '''
# 
#     def __init__(self, sinogram, rot_center=None, dark=None, flat=None,
#                        x_range=None, omega_range=None,  z_range=None, data_range=None,
#                        x_units='mm', omega_units='deg', z_units='mm', data_units='eV'):
# 
#         self.x_range     = x_range
#         self.omega_range = omega_range
#         self.z_range     = z_range
#         self.data_range  = data_range
#         
#         self.x_units     = x_units
#         self.omega_units = omega_units
#         self.z_units     = z_units
#         self.data_units  = data_units
# 
#         self.dark = dark
#         self.flat = flat
# 
#         self.sinogram = sinogram
# 
#         self.rot_center = len(x_range)/2 if rot_center is None else rot_center
#     
#         self.recon = None
# 
#         if HAS_larch:
#            Group.__init__(self)
# 
#     
#     def reconstruction(self, normalize=False, invert=False, log=False, circle=True,
#                        center=False,algorithm='gridrec'):
#     
#         proj = self.sinogram
#         if invert: proj = 1.001*np.max(proj) - proj
# 
#         if HAS_tomopy:
#             if self.omega_units.startswith('deg'):
#                 theta = np.radians(omega_range)
#             else:
#                 theta = omega_range
#                 
#             if normalize: proj = tomopy.normalize(proj, self.flat, self.dark)
#             if log: proj = tomopy.minus_log(proj)
#             if center:
#                 cenval = tomopy.find_center(proj, theta, init=self.rot_center, ind=0, tol=0.5)
#             else:
#                 cenval = self.rot_center
# 
# 
#             self.recon = tomopy.recon(proj, theta, center=cenval, algorithm=algorithm)
# 
#         elif HAS_scikit:
#             if self.omega_units.startswith('deg'):
#                 theta = omega_range
#             else:
#                 theta = np.degrees(omega_range)
# 
#             omei,datai,xi = np.shape(proj)
#             self.recon = np.array([iradon(proj[:,i,:].T, theta=theta, circle=True) for i in np.arange(datai)])
# 
# 
# def make_slice(xmap, name='Fe Ka', center=None, n_angles=721, max_angle=360):
#     sino = xmap.get_roimap(name)[:, 2:2+n_angles]
#     npts, nth = sino.shape
#     if center is None:
#         mass = sino.sum(axis=1)
#         xx = arange(npts)
#         center = int(round((xx*mass).sum()/mass.sum()))
#     #endif
#     if center < npts/2.0:
#         xslice = slice(npts - 2*center, -1)
#     else:
#         xslice = slice(0, npts-2*center)
#     #endif
#     theta = linspace(0, max_angle, n_angles)
#     return iradon(sino[xslice,:], theta=theta, 
#                   filter='shepp-logan',
#                   interpolation='linear', circle=True)
# #enddef
# 
# def guess_center(xmap, name='Fe Ka', n_angles=721, max_angle=360):
#     sino = xmap.get_roimap(name)[:,2:2+n_angles]
#     theta = linspace(0, max_angle, n_angles)
#     npts, nth = sino.shape
#     mass = sino.sum(axis=1)
#     xx = arange(npts)
#     center = int(round((xx*mass).sum()/mass.sum()))
#     print( "Center guess ", npts, center)
#     for cen in range(center-12, center+12, 2):
#         if cen < npts/2.0:
#             xslice = slice(npts-2*cen, -1)
#         else:
#             xslice = slice(0, npts-2*cen)
#         #endif
#         recon = iradon(sino[xslice,:], theta=theta, 
#                        filter='shepp-logan',
#                        interpolation='linear', circle=True)
#         recon = recon - recon.min() + 0.005*(recon.max()-recon.min())
#         negentropy = (recon*log(recon)).sum()
#         print("%3.3i %.4g" % (cen, negentropy))
#     #endfor
# #enddef
# 
# def get_slices(xmap, center=None):
#     out = group(fname=xmap.filename)
#     out.fe = make_slice(xmap, name='Fe Ka', center=center)
#     out.mn = make_slice(xmap, name='Mn Ka', center=center)
#     out.ca = make_slice(xmap, name='Ca Ka',center=center) 
#     out.k  = make_slice(xmap, name='K Ka', center=center)
#     out.zn = make_slice(xmap, name='Zn Ka', center=center)
#     return out
# #enddef
# 
# def show_3color(out, r, g, b):
#     rmap = getattr(out, r.lower())
#     gmap = getattr(out, g.lower())
#     bmap = getattr(out, b.lower())
# 
#     subtitles = {'red': 'Red: %s' % r, 
#                  'green': 'Green: %s' % g, 
#                  'blue': 'Blue: %s' % b}
# 
#     rgb = array([rmap, gmap, bmap]).swapaxes(0, 2)
# 
#     imshow(rgb, subtitles=subtitles, title=out.fname)
# #enddef
# 
# def read_map(fname):
#    xrfmap = read_xrfmap(fname)
#    return xrfmap
# #enddef
# 
# 
# 
# 
# def create_tomogrp(sinogram, _larch=None, **kws):
# 
#     '''
#     create a tomography class
# 
#      Parameters:
#      ------------
#       data :     2D diffraction patterns
# 
# 
#      Returns:
#      ----------
#       a tomography class
# 
#     '''
#     return tomogrp(sinogram, **kws)
# 
#    
# 
=======
'''
This module defines a tomography dataset class.

Authors/Modifications:
----------------------
* Margaret Koker, koker@cars.uchicago.edu
* modeled after MCA class
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import numpy as np

import os
import sys

HAS_tomopy = False
try:
    import tomopy
    HAS_tomopy = True
except ImportError:
    pass

HAS_scikit = False
try:
    from skimage.transform import iradon
    #from skimage.transform import radon, iradon_sart
    HAS_scikit = True
except:
    pass

HAS_larch = False
try:
    from larch import Group
    grpobjt = Group
    HAS_larch = True
except:
    grpobjt = object

##########################################################################
# CLASSES

class tomogrp(grpobjt):
    '''
    Tomography dataset class
    
    Attributes:
    ------------

    # Raw data and collection parameters
    * self.x_range       = None or array          # x-range for sampled data
    * self.omega_range   = None or array          # omega-range for sampled data
    * self.z_range       = None or array          # z-range for sampled data (slices)
    * self.data_range    = None or array          # range for data sampling (e.g. 2th, E)

    * self.x_units       = 'um'|'mm'|'m'|...      # units for x-range
    * self.omega_units   = 'degrees'|'radians     # units for omega-range
    * self.z_units       = 'um'|'mm'|'m'|...      # units for z-range
    * self.data_units    = 'degrees'|'eV'|...     # units for data sampling

    * self.dark          = None or array          # dark for tomography comparison
    * self.flat          = None or array          # flat image for tomography

    * self.sinogram      = None or array          # raw data collected [xi,omei,datai,zi]

    # Data fitting parameters
    * self.rot_center    = 100                    # rotation center along x-axis (pixel number)
    
    # Analysis
    * self.recon         = None or array          # tomographic reconstruction

    mkak 2017.07.07
    '''

    def __init__(self, sinogram, rot_center=None, dark=None, flat=None,
                       x_range=None, omega_range=None,  z_range=None, data_range=None,
                       x_units='mm', omega_units='deg', z_units='mm', data_units='eV'):

        self.x_range     = x_range
        self.omega_range = omega_range
        self.z_range     = z_range
        self.data_range  = data_range
        
        self.x_units     = x_units
        self.omega_units = omega_units
        self.z_units     = z_units
        self.data_units  = data_units

        self.dark = dark
        self.flat = flat

        self.sinogram = sinogram

        self.rot_center = len(x_range)/2 if rot_center is None else rot_center
    
        self.recon = None

        if HAS_larch:
           Group.__init__(self)

    
    def reconstruction(self, normalize=False, invert=False, log=False, circle=True,
                       center=False,algorithm='gridrec'):
    
        proj = self.sinogram
        if invert: proj = 1.001*np.max(proj) - proj

        if HAS_tomopy:
            if self.omega_units.startswith('deg'):
                theta = np.radians(omega_range)
            else:
                theta = omega_range
                
            if normalize: proj = tomopy.normalize(proj, self.flat, self.dark)
            if log: proj = tomopy.minus_log(proj)
            if center:
                cenval = tomopy.find_center(proj, theta, init=self.rot_center, ind=0, tol=0.5)
            else:
                cenval = self.rot_center


            self.recon = tomopy.recon(proj, theta, center=cenval, algorithm=algorithm)

        elif HAS_scikit:
            if self.omega_units.startswith('deg'):
                theta = omega_range
            else:
                theta = np.degrees(omega_range)

            omei,datai,xi = np.shape(proj)
            self.recon = np.array([iradon(proj[:,i,:].T, theta=theta, circle=True) for i in np.arange(datai)])


def make_slice(xmap, name='Fe Ka', center=None, n_angles=721, max_angle=360):
    sino = xmap.get_roimap(name)[:, 2:2+n_angles]
    npts, nth = sino.shape
    if center is None:
        mass = sino.sum(axis=1)
        xx = arange(npts)
        center = int(round((xx*mass).sum()/mass.sum()))
    #endif
    if center < npts/2.0:
        xslice = slice(npts - 2*center, -1)
    else:
        xslice = slice(0, npts-2*center)
    #endif
    theta = linspace(0, max_angle, n_angles)
    return iradon(sino[xslice,:], theta=theta, 
                  filter='shepp-logan',
                  interpolation='linear', circle=True)
#enddef

def guess_center(xmap, name='Fe Ka', n_angles=721, max_angle=360):
    sino = xmap.get_roimap(name)[:,2:2+n_angles]
    theta = linspace(0, max_angle, n_angles)
    npts, nth = sino.shape
    mass = sino.sum(axis=1)
    xx = arange(npts)
    center = int(round((xx*mass).sum()/mass.sum()))
    print( "Center guess ", npts, center)
    for cen in range(center-12, center+12, 2):
        if cen < npts/2.0:
            xslice = slice(npts-2*cen, -1)
        else:
            xslice = slice(0, npts-2*cen)
        #endif
        recon = iradon(sino[xslice,:], theta=theta, 
                       filter='shepp-logan',
                       interpolation='linear', circle=True)
        recon = recon - recon.min() + 0.005*(recon.max()-recon.min())
        negentropy = (recon*log(recon)).sum()
        print("%3.3i %.4g" % (cen, negentropy))
    #endfor
#enddef

def get_slices(xmap, center=None):
    out = group(fname=xmap.filename)
    out.fe = make_slice(xmap, name='Fe Ka', center=center)
    out.mn = make_slice(xmap, name='Mn Ka', center=center)
    out.ca = make_slice(xmap, name='Ca Ka',center=center) 
    out.k  = make_slice(xmap, name='K Ka', center=center)
    out.zn = make_slice(xmap, name='Zn Ka', center=center)
    return out
#enddef

def show_3color(out, r, g, b):
    rmap = getattr(out, r.lower())
    gmap = getattr(out, g.lower())
    bmap = getattr(out, b.lower())

    subtitles = {'red': 'Red: %s' % r, 
                 'green': 'Green: %s' % g, 
                 'blue': 'Blue: %s' % b}

    rgb = array([rmap, gmap, bmap]).swapaxes(0, 2)

    imshow(rgb, subtitles=subtitles, title=out.fname)
#enddef

def read_map(fname):
   xrfmap = read_xrfmap(fname)
   return xrfmap
#enddef




def create_tomogrp(sinogram, _larch=None, **kws):

    '''
    create a tomography class

     Parameters:
     ------------
      data :     2D diffraction patterns


     Returns:
     ----------
      a tomography class

    '''
    return tomogrp(sinogram, **kws)


# def registerLarchPlugin():
#     return ('_tomo', {'create_tomogrp': create_tomogrp})
# 
# 
# def registerLarchGroups():
#     return (tomogrp)