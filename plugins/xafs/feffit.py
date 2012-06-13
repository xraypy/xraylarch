#!/usr/bin/env python
"""
   feffit sums Feff paths to match xafs data
"""

import sys, os
import numpy as np
from scipy.optimize import leastsq as scipy_leastsq

import larch
from larch.larchlib import Parameter, isParameter, plugin_path
from larch.utils import OrderedDict
from larch.symboltable import isgroup


sys.path.insert(0, plugin_path('std'))
sys.path.insert(0, plugin_path('fitter'))
sys.path.insert(0, plugin_path('xafs'))

from minimizer import Minimizer
from feffdat import FeffPathGroup

class FTParamGroup(larch.Group):
    def __init__(self, kmin=0, kmax=20, kw=2, dk=1, dk2=None, window='kaiser',
                 rmin = 0, rmax=10, dr=0, rwindow='kaiser',
                 nfft=2048, kstep=0.05, fitspace='r', _larch=None):
        larch.Group.__init__(self)
        self.kmin = kmin
        self.kmax = kmax
        self.kw = kw
        self.dk1 = dk1
        self.dk2 = dk2
        self.window = window
        self.rmin = rmin
        self.rmax = rmax
        self.dr = dr
        self.rwindow = rwindow
        self.kstep = kstep,
        self.nfft = nfft
        self.fitspace = fitspace
        self._larch = _larch

class FeffitDataSet(larch.Group):
    def __init__(self, datagroup=None, pathlist=None, _larch=None,
                 ftgroup=None):
        self._larch = _larch
        larch.Group.__init__(self,  **kws)
        self.pathlist = pathlist
        self.datagroup = datagroup
        self.ftgroup = ftgroup


class Feffit(Minimizer):
    def __init__(self, pathlist, params, _larch=None, **kws):
        Minimizer.__init__(self, self._feffit, params, _larch=_larch, **kws)

    def _feffit(self, ):
        """residual function for feffit"""

def registerLarchPlugin():
    return ('_xafs', {'feffit': _feffit})
