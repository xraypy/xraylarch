"""
This module defines a device-independent XRD class.

Authors/Modifications:
----------------------
* Margaret Koker, koker@cars.uchicago.edu
* modeled after MCA class
"""
import numpy as np
from larch import Group, isgroup

class XRD(Group):
    """
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
    """
    ###############################################################################
    def __init__(self, data2D=None, xpixels=2048, ypixels=2048,
                 data1D=None, nwedge=2, nchan=5001, 
                 name='xrd',**kws):

        self.name    = name
        self.xpix    = xpixels
        self.ypix    = ypixels
        self.data2D  = data2D
        self.nwedge  = nwedge
        self.nchan   = nchan
        self.data1D  = data1D
        
        ## Also include calibration data file?
        ## mkak 2016.08.20

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
        """add an Environment setting"""
        if len(desc) > 0 and len(val) > 0:
            self.environ.append(Environment(desc=desc, val=val, addr=addr))

    ########################################################################

def create_xrd(data2D=None, xpixels=2048, ypixels=2048,
               data1D=None, nwedge=2, nchan=5001, 
               name='xrd', **kws):

    """create an XRD object

     Parameters:
     ------------
      data2D:   2D diffraction patterns
      data1D:   1D diffraction patterns
      xpixels:  number of x pixels
      ypixels:  number of y pixels

     Returns:
     ----------
      an XRD object

    """
    return XRD(data2D=data2D, data1D=data1D, xpixels=xpixels, ypixels=ypixels,
               name=name, **kws)

def registerLarchPlugin():
    return ('_xrd', {'create_xrd': create_xrd})
