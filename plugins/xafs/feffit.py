#!/usr/bin/env python
"""
   feffit sums Feff paths to match xafs data
"""

import sys, os
import numpy as np
from numpy import array, arange, interp, pi, zeros, sqrt, concatenate
from numpy.fft import fft, ifft

from scipy.optimize import leastsq as scipy_leastsq

import larch
from larch.larchlib import Parameter, isParameter, plugin_path
from larch.utils import OrderedDict
from larch.symboltable import isgroup


sys.path.insert(0, plugin_path('std'))
sys.path.insert(0, plugin_path('fitter'))
sys.path.insert(0, plugin_path('xafs'))

from mathutils import index_of, realimag

from minimizer import Minimizer
from xafsft import xafsft, xafsft_prep, xafsft_fast, xafsift, ftwindow
from feffdat import FeffPathGroup, _ff2chi

class FilterGroup(larch.Group):
    """A Group of filter parameters.
    The apply() method will return the result of applying the filter,
    ready to use in a Fit.   This caches the FT windows (k and r windows)
    and assumes that once created (not None), these do not need to be
    recalculated....

    That is: don't change the parameters are expect the different things.
    If you do change parameters, reset kwin_array / rwin_array to None.

    """
    def __init__(self, kmin=0, kmax=20, kw=2, dk=1, dk2=None, window='kaiser',
                 rmin = 0, rmax=10, dr=0, rwindow='kaiser', kweight=None,
                 nfft=2048, kstep=0.05, fitspace='r', _larch=None, **kws):
        larch.Group.__init__(self)

        self.kmin = kmin
        self.kmax = kmax
        self.kw = kw
        if kweight is not None:
            self.kw = kweight
        self.dk = dk
        self.dk2 = dk2
        self.window = window
        self.rmin = rmin
        self.rmax = rmax
        self.dr = dr
        self.rwindow = rwindow
        self.kstep = kstep

        self.nfft = nfft
        self.fitspace = fitspace
        self._larch = _larch
        self.rstep = pi/(self.kstep*self.nfft)

        self.kwin_array = None
        self.rwin_array = None

    def fft(self, k, chi):
        if self.kwin_array is None:
            self.kwin_array = ftwindow(k, xmin=self.kmin, xmax=self.kmax,
                                       dx=self.dk, dx2=self.dk2,
                                       window=self.window)
        cchi = zeros(self.nfft, dtype='complex128')
        cchi[0:len(chi)] = chi
        out = fft(cchi * self.kwin_array * k**self.kw)
        return self.kstep*sqrt(pi) * out[:self.nfft/2]

    def ifft(self, r, chir):
        if self.rwin_array is None:
            self.rwin_array = ftwindow(r, xmin=self.rmin, xmax=self.rmax,
                                       dx=self.dr, dx2=self.dr2,
                                       window=self.rwindow)

        cchir = zeros(self.nfft, dtype='complex128')
        cchir[0:len(chir)] = chir
        out = ifft(cchir * self.rwin_array * r**self.rw)
        return sqrt(pi)/(2*self.kstep) * out[:self.nfft/2]

    def apply(self, k, chi, **kws):
        """apply filter"""

        for key, val in kws:
            if key == 'kweight': key = 'kw'
            setattr(self, key, val)

        if self.fitspace == 'k':
            return chi * k**self.kw
        elif self.fitspace in ('r', 'q'):

            k_ = self.kstep * arange(self.nfft, dtype='float64')
            r_ = self.rstep * arange(self.nfft, dtype='float64')
            chir = self.fft(k_, chi)
            if self.fitspace == 'r':
                irmin = index_of(r_, self.rmin)
                irmax = min(self.nfft/2,  1 + index_of(r_, self.rmax))
                return realimag(chir[irmin:irmax])
            else:
                chiq = self.ifft(r_, chir)
                iqmin = index_of(k_, self.kmin)
                iqmax = min(self.nfft/2,  1 + index(k_, self.kmax))
                return realimag(chiq[ikmin:ikmax])

class FeffitDataSet(larch.Group):
    def __init__(self, data=None, pathlist=None, filter=None, _larch=None):
        self._larch = _larch
        larch.Group.__init__(self,  **kws)
        self.pathlist = pathlist

        self.datagroup = data
        if filter is None:
            filter = FilterGroup()
        self.filter = filter
        self.model = Group()
        self.k = None
        self.data_chi = None
        self.model_chi = None

    def residual(self):
        if not isinstance(self.filter, FilterGroup):
            print "Filter for DataSet is not set"
            return
        if self.k is None:
            self.k = self.filter.kstep * arange(max(self.datagroup.k))
            self.data_chi =  interp(self.k, self.datgroup.k, self.datagroup.chi)
        self.model_chi = _ff2chi(self.pathlist, _larch =_larch,
                                 kstep=self.filter.kstep, group=self.model)

        return self.filter.apply(self.k, self.data_chi-self.model_chi)


def feffit_fit(params, datasets, _larch=None):

    def _resid(self, params, datasets=None, _larch=None, **kws):
        """ this is the residua function """
        return concatenate([d.residual() for d in self.datasets])

    fitkws = dict(datasets=datasets)
    fit = Minimizer(_resid, params, fcn_kws=_fitkws, _larch=_larch)
    fit.leastsq()

def feffit_dataset(data=None, pathlist=None, filter=None, _larch=None):
    return FeffitDataSet(data=data, pathlist=pathlist, filter=filter, _larch=_larch)

def feffit_filter(_larch=None, **kws):
    return FilterGroup(_larch=_larch, **kws)

def registerLarchPlugin():
    print '====== Test FEFFIT ======'
    return ('_xafs', {'feffit_fit': feffit_fit,
                      'feffit_dataset': feffit_dataset,
                      'feffit_filter': feffit_filter,


                      })
