"""
This module defines a region of interest class
and utility functions.

Authors/Modifications:
-----------------------
* Mark Rivers, GSECARS
* Modified for Tdl, tpt
* simplified, modified for larch, M Newville
"""

import numpy as np

class ROI(object):
    """
    Class that defines a Region-Of-Interest (ROI)

    Attributes:
    -----------
    * left      # Left channel
    * right     # Right channel
    * name     # Name of the ROI
    * bgr_width # Number of channels to use for background subtraction

    # Computed
    * total     # Total counts
    * net       # Net (bgr subtr) counts
    * center    # Centroid
    * width     # Width
    """
    def __init__(self, left=0, right=0, name='', bgr_width=3):
        """
        Parameters:
        -----------
        * left      Left limit in index/channels numbers
        * right     Right limit in index/channels numbers
        * name     Name of the ROI
        * bgr_width Number of channels to use for background subtraction
        """
        self.name     = name
        self.bgr_width = int(bgr_width)
        self.total  = 0
        self.net    = 0
        self.set_bounds(left, right)

    def __repr__(self):
        form = "<ROI %s: total=%g, net=%g, range=[%d, %d], center=%d, width=%d, nbgr=%d>"
        return form % (self.name, self.total, self.net, self.left, self.right,
                       self.center, self.width, self.bgr_width)

    def __cmp__(self, other):
        """
        Comparison operator.

        The .left field is used to define ROI ordering
        """
        return (self.left - other.left)

    def set_bounds(self, left=-1, right=-1):
        """set ROI bounds"""
        self.left   = int(left)
        self.right  = int(right)
        self.center = int((self.right + self.left)/2.)
        self.width  = abs((self.right - self.left)/2.)

    def get_counts(self, data, net=False):
        """
        calculate total and net counts for a spectra

        Parameters:
        -----------
        * data: numpy array of spectra
        * net:  bool to set net counts (default=False: total counts returned)
        """
        bgr_width = int(self.bgr_width)
        ilmin = max((self.left - bgr_width), 0)
        irmax = min((self.right + bgr_width), len(data)-1) + 1
        bgr_counts = np.concatenate((data[ilmin:self.left],
                                     data[self.right+1:irmax])).mean()

        #total and net cts
        self.total  = data[self.left:self.right+1].sum()
        self.net    = self.total - bgr_counts
        out = self.total
        if net:
            out = self.net
        return out

def create_roi(name, left, right, bgr_width=3, _larch=None):
    """create an ROI, a named portion of an MCA spectra defined by index

     Parameters:
     ------------
      name:     roi name
      left:     left index
      right:    right index

     Returns:
     ----------
      an ROI object which has properties
          name, left, right, center, width, bgr_width
      and methods
          set_bounds(left, right)
          get_counts(data, net=False)
    """
    return ROI(name=name, left=left, right=right, bgr_width=bgr_width)

def registerLarchPlugin():
    return ('_xrf', {'create_roi': create_roi})


