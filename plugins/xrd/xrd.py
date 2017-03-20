'''
This module defines a device-independent XRD class.

Authors/Modifications:
----------------------
* Margaret Koker, koker@cars.uchicago.edu
* modeled after MCA class
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import os
import numpy as np

from xrd_etc import (d_from_q, d_from_twth, twth_from_d, twth_from_q, q_from_d,
                     q_from_twth, E_from_lambda)

HAS_larch = False
try:
    from larch import Group
    grpobjt = Group
    HAS_larch = True
except:
    grpobjt = object

##########################################################################
# FUNCTIONS
  
class xrd1d(grpobjt):
    '''
    1D XRD data class
    
    --> all length units in m (unless otherwise noted)
    
    Attributes:
    ------------
    * self.filename      = 'CeO2_Allende.xy'      # file containing x-y data
    * self.label         = 'Data: CeO2_Allende'   # name of data set

    # Data parameters
    * self.I             = None or array          # intensity (units: counts)
    * self.q             = None or array          # inverse lattice spacing (units: 1/A)
    * self.d             = None or array          # lattice spacing (units: A)
    * self.twth          = None or array          # 2-theta (units: degrees)

    # Calibration/experiemental parameters
    * self.wavelength    = 0.688801071778         # incident x-ray wavelength (units: A)
    * self.energy        = 18.000                 # incident x-ray energy (units: keV)
    * self.distance      = 0.49212785             # distance from sample to detector
    * self.poni          = [0.2286, 0.2547]       # center/point of normal incidence
    * self.rotation      = [0.010, -0.00857, 0.0] # detector rotations (units: radians)
    * self.pixelsize     = [0.0004, 0.0004]       # size of pixels
    * self.splinefile    = None                   # spline file for detector
    * self.polarization  = None                   # polarization of detector
    * self.normalization = 1.0                    # normalization factor for detector
    
    # Data fitting parameters
    * self.uvw           = [0.313, -0.109, 0.019] # instrumental broadening parameters


    # Plotting parameters
    * self.yscale        = 1.0                    # scale for y axis plotting


    mkak 2017.03.15
    '''

    def __init__(self,file=None,label=None,
                 I=None,q=None,d=None,twth=None,wavelength=None,energy=None,
                 _larch=None):

        self.filename = file
        self.label    = label


        self.I    = I
        self.q    = q
        self.d    = d
        self.twth = twth

        self.wavelength = wavelength
        self.energy     = energy

        ## Default values
        self.distance      = None
        self.poni          = None
        self.rotation      = None
        self.pixelsize     = None
        self.splinefile    = None
        self.polarization  = None
        self.normalization = None
        
        self.uvw = None
        self.yscale = 1.0
        
        
        if file is None:
            print('File not given. Leaving blank group for now.')
       
        else:
            self.xrd_from_file(file)

        
        
        if HAS_larch:
           Group.__init__(self)

    def xrd_from_file(self,filename,verbose=True):
        
        try:
            if verbose:
                print('Opening file: %s' % os.path.split(filename)[-1])

            from larch_plugins.xrmmap import read1DXRDFile
            h,d = read1DXRDFile(filename)
        except:
           print('incorrect xy file format: %s' % os.path.split(filename)[-1])
           return
           
        self.label = os.path.split(filename)[-1]

        ## header info
        units = 'q'
        for line in h:
            import re
            line = re.sub(',','',line)

            if 'SplineFile' in line:
                self.splinefile = line.split()[-1]
            if 'PixelSize' in line:
                self.pixelsize = [float(line.split()[2]),float(line.split()[3])]
            if 'PONI' in line:
                self.poni = [float(line.split()[2]),float(line.split()[3])]
            if 'Detector' in line:
                self.distance = float(line.split()[-2])
            if 'Rotations' in line:
                self.rotation = [float(line.split()[2]),float(line.split()[3]),float(line.split()[4])]

            if 'Wavelength' in line:
                self.wavelength = float(line.split()[-1])*1e10
                self.energy = E_from_lambda(self.wavelength)
            if 'Polarization' in line:
                if line.split()[-1] != 'None': self.polarization = float(line.split()[-1])
            if 'Normalization' in line:
                self.normalization = float(line.split()[-1])

            if 'q_' in line or '2th_' in line:
                units = line.split()[1]
        ## data
        x,y = np.split(np.array(d),2,axis=1)
        if units.startswith('q'):
            self.q = x
        elif units.startswith('2th'):
            self.twth = x
        else:
            print('x-axis units not correct. check file: %s' % os.path.split(filename)[-1])
            return
        self.calculate_xvalues()
        self.I = y

    def calculate_xvalues(self):

        if self.q is not None:
            self.q = np.array(self.q)
            self.d = d_from_q(self.q)
            if self.wavelength is not None:
                self.twth = twth_from_q(self.q,self.wavelength)
            else:
                self.twth = np.zeros(len(self.q))
        elif self.twth is not None:
            self.twth = np.array(self.twth)
            if self.wavelength is not None:
                self.q = q_from_twth(self.twth,self.wavelength)
                self.d = d_from_twth(self.twth,self.wavelength)
            else:
                self.q = np.zeros(len(self.twth))
                self.d = np.zeros(len(self.twth))
        elif self.d is not None:
            self.d = np.array(self.d)
            self.q = q_from_d(self.d)
            if self.wavelength is not None:
                self.twth = twth_from_d(self.d,self.wavelength)
            else:
                self.twth = np.zeros(len(self.d))
        else:
            print('All x-axis arrays are None. Cannot create an xrd1d object.')
        
    def calculate_Evalues(self,energy,wavelength):
    
        if energy is not None:
            if energy > 100:
                energy = energy/1000. # convert units to keV from eV
            wavelength = lambda_from_E(energy,E_units='keV',lambda_units='A')
        elif wavelength is not None:
            energy = E_from_lambda(wavelength,E_units='keV',lambda_units='A')
        else:
            energy = None
            wavelength = None
            
        return energy,wavelength

class XRD(grpobjt):
    '''
    X-Ray Diffraction (XRD) class

    Attributes:
    -----------
    * self.name        = 'xrd'  # Name of the object
    * self.xpix        = 2048   # number of x pixels
    * self.ypix        = 2048   # number of y pixels
    * self.data2D      = None   # 2D XRD data
    * self.data1D      = None   # 1D XRD data

    Notes:
    ------

    mkak 2016.08.20
    '''

    def __init__(self, data2D=None, xpixels=2048, ypixels=2048,
                 data1D=None, nwedge=2, nchan=5001, 
                 name='xrd', _larch=None, **kws):

        self.name    = name
        self.xpix    = xpixels
        self.ypix    = ypixels
        self.data2D  = data2D
        self.nwedge  = nwedge
        self.nchan   = nchan
        self.data1D  = data1D
        
        ## Also include calibration data file?
        ## mkak 2016.08.20

        if HAS_larch:
            Group.__init__(self)

    def __repr__(self):
        if self.data2D is not None:
            form = "<2DXRD %s: pixels = %d, %d>"
            return form % (self.name, self.xpix, self.ypix)
        elif self.data1D is not None:
            form = "<1DXRD %s: channels = %d>"
            return form % (self.name, self.nchan)
        else:
            form = "<no 1D or 2D XRD pattern given>"
            return form       

    def add_environ(self, desc='', val='', addr=''):
        '''add an Environment setting'''
        if len(desc) > 0 and len(val) > 0:
            self.environ.append(Environment(desc=desc, val=val, addr=addr))



def create_xrd(data2D=None, xpixels=2048, ypixels=2048,
               data1D=None, nwedge=2, nchan=5001, 
               name='xrd', _larch=None, **kws):

    '''
    create an XRD object

     Parameters:
     ------------
      data2D:   2D diffraction patterns
      data1D:   1D diffraction patterns
      xpixels:  number of x pixels
      ypixels:  number of y pixels

     Returns:
     ----------
      an XRD object

    '''
    return XRD(data2D=data2D, data1D=data1D, xpixels=xpixels, ypixels=ypixels,
               name=name, **kws)



        
## ADD IN TO XRD1D VIEWER mkak 2017.03.20
# # # def loadXYFILE(parent,event=None,verbose=False):
# # # 
# # #     wildcards = 'XRD data file (*.xy)|*.xy|All files (*.*)|*.*'
# # #     dlg = wx.FileDialog(parent, message='Choose 1D XRD data file',
# # #                        defaultDir=os.getcwd(),
# # #                        wildcard=wildcards, style=wx.FD_OPEN)
# # # 
# # #     path, read = None, False
# # #     if dlg.ShowModal() == wx.ID_OK:
# # #         read = True
# # #         path = dlg.GetPath().replace('\\', '/')
# # #     dlg.Destroy()
# # # 
# # #     if read:

# def readXYFILE(parent,event=None,verbose=False):
# 
# #     wildcards = 'XRD data file (*.xy)|*.xy|All files (*.*)|*.*'
# #     dlg = wx.FileDialog(parent, message='Choose 1D XRD data file',
# #                        defaultDir=os.getcwd(),
# #                        wildcard=wildcards, style=wx.FD_OPEN)
# # 
# #     path, read = None, False
# #     if dlg.ShowModal() == wx.ID_OK:
# #         read = True
# #         path = dlg.GetPath().replace('\\', '/')
# #     dlg.Destroy()
# # 
# #     if read:
# 
#     try:
#         if verbose:
#             print('Opening file: %s' % os.path.split(path)[-1])
# 
#         h,d = read1DXRDFile(path)
# 
#         ## header info
#         splfl = None
#         xpix,ypix = None,None
#         poni1,poni2 = None,None
#         dist = None
#         rot1,rot2,rot3 = None,None,None
#         wavelength = None
#         plr = None
#         nrm = None
#         units = None
# 
#         for line in h:
#             import re
#             line = re.sub(',','',line)
# 
#             if 'SplineFile' in line:
#                 splfl = line.split()[-1]
#             if 'PixelSize' in line:
#                 xpix,ypix = float(line.split()[2]),float(line.split()[3])
#             if 'PONI' in line:
#                 poni1,poni2 = float(line.split()[2]),float(line.split()[3])
#             if 'Detector' in line:
#                 dist = float(line.split()[-2])
#             if 'Rotations' in line:
#                 rot1,rot2,rot3 = float(line.split()[2]),float(line.split()[3]),float(line.split()[4])
# 
#             if 'Wavelength' in line:
#                 wavelength = float(line.split()[-1])
#             if 'Polarization' in line:
#                 if line.split()[-1] != 'None': plr = float(line.split()[-1])
#             if 'Normalization' in line:
#                 nrm = float(line.split()[-1])
# 
#             if 'q_' in line or '2th_' in line:
#                 units = line.split()[1]
#         ## data
#         x,y = np.split(np.array(d),2,axis=1)
# 
#     except:
#        print('incorrect xy file format: %s' % os.path.split(path)[-1])
#        return
# 
#     return x,y,units,path
#     

def registerLarchPlugin():
    return ('_xrd', {'create_xrd': create_xrd, 'loadXYFILE': loadXYFILE})
