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
from larch import Group


def split_roiname(name):
    words = name.split()
    elem = words[0].title()
    line = 'ka'
    if len(words) > 1:
        line = words[1]
    line = line.title()
    if line == 'Ka': line = 'Ka1'
    if line == 'Kb': line = 'Kb1'
    if line == 'La': line = 'La1'
    if line == 'Lb': line = 'Lb1'
    return elem, line

class ROI(Group):
    """
    Class that defines a Region-Of-Interest (ROI)

    Attributes:
    -----------
    * left      # Left channel
    * right     # Right channel
    * name      # Name of the ROI
    * address   # Address of the ROI (PV name, for example)
    * bgr_width # Number of channels to use for background subtraction

    # Computed
    * total     # Total counts
    * net       # Net (bgr subtr) counts
    * center    # Centroid
    * width     # Width
    """
    def __init__(self, left=0, right=0, name='', bgr_width=3, counts=None,
                 address=''):
        """
        Parameters:
        -----------
        * left      Left limit in index/channels numbers
        * right     Right limit in index/channels numbers
        * name     Name of the ROI
        * bgr_width Number of channels to use for background subtraction
        """
        self.name     = name
        self.address  = address
        self.bgr_width = int(bgr_width)
        self.total  = 0
        self.net    = 0
        self.set_bounds(left, right)
        if counts is not None:
            self.get_counts(counts)
        Group.__init__(self)

    def __eq__(self, other):
        """used for comparisons"""
        return (self.left == getattr(other, 'left', None) and
                self.right == getattr(other, 'right', None) and
                self.bgr_width == getattr(other, 'bgr_width', None) )

    def __ne__(self, other): return not self.__eq__(other)
    def __lt__(self, other): return self.left <  getattr(other, 'left', None)
    def __le__(self, other): return self.left <= getattr(other, 'left', None)
    def __gt__(self, other): return self.left >  getattr(other, 'left', None)
    def __ge__(self, other): return self.left >= getattr(other, 'left', None)


    def __repr__(self):
        form = "<ROI(name='%s', left=%i, right=%i, bgr_width=%i)>"
        return form % (self.name, self.left, self.right, self.bgr_width)

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
        self.net    = self.total - bgr_counts*(self.right-self.left)
        out = self.total
        if net:
            out = self.net
        return out

def create_roi(name, left, right, bgr_width=3, address=''):
    """create an ROI, a named portion of an MCA spectra defined by index

     Parameters:
     ------------
      name:     roi name
      left:     left index
      right:    right index
      bgr_width (optional)  background width (default=3)
      address   (optional)  address (PV name) for ROI

     Returns:
     ----------
      an ROI object which has properties
          name, left, right, center, width, bgr_width
      and methods
          set_bounds(left, right)
          get_counts(data, net=False)
    """
    return ROI(name=name, left=left, right=right,
               bgr_width=bgr_width, address=address)
