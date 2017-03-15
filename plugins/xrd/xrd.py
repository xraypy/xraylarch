'''
This module defines a device-independent XRD class.

Authors/Modifications:
----------------------
* Margaret Koker, koker@cars.uchicago.edu
* modeled after MCA class
'''

##########################################################################
# IMPORT PYTHON PACKAGES

import numpy as np

HAS_larch = False
try:
    from larch import Group
    grpobjt = Group
    HAS_larch = True
except:
    grpobjt = object

##########################################################################
# FUNCTIONS

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

class xrd1d(grpobjt):
    '''


    mkak 2017.03.15
    '''

    def __init__(self,x,y,flag='q',wavelength=None,energy=None,name='',_larch=None):

        if len(x) != len(y):
            print('Arrays x (%i) and y (%i) must have same shape.' % (len(x),len(y)))
            return
        self.I = np.array(y)
        

        self.energy,self.wavelength = self.calculate_Evalues(energy,wavelength)
        self.q,self.d,self.twth = self.calculate_xvalues(x,flag,self.wavelength)
        
        self.name    = name
        
        
        if HAS_larch:
           Group.__init__(self)


    def calculate_xvalues(self,x,flag,wavelength):

        if flag.startswith('2th'):
            twth = np.array(x)
            if wavelength is not None:
                q = q_from_twth(twth,wavelength)
                d = d_from_twth(twth,wavelength)
            else:
                q = np.zeros(len(twth))
                d = np.zeros(len(twth))
        elif flag.startswith('d'):
            d = np.array(x)
            if wavelength is not None:
                q    = q_from_d(d)
                twth = twth_from_d(d,wavelength)
            else:
                q    = np.zeros(len(d))
                twth = np.zeros(len(d))
        else:
            q = np.array(x)
            if wavelength is not None:
                twth = twth_from_q(q,wavelength)
                d    = d_from_q(q)
            else:
                twth = np.zeros(len(q))
                d    = np.zeros(len(q))
        return q,d,twth
        
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

def registerLarchPlugin():
    return ('_xrd', {'create_xrd': create_xrd})
