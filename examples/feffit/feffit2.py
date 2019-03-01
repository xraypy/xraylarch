#!/usr/bin/env python
"""
   feffit sums Feff paths to match xafs data
"""

import sys, os
import numpy as np
from numpy import arange, interp, pi, zeros, sqrt
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
    def __init__(self, kmin=0, kmax=20, kw=2, dk=1, dk2=None, window='kaiser',
                 rmin = 0, rmax=10, dr=0, rwindow='kaiser', kweight=None,
                 nfft=2048, kstep=0.05, fitspace='r', _larch=None, **kws):
        larch.Group.__init__(self)

        self._kmin = kmin
        self._kmax = kmax
        self._kw = kw
        if kweight is not None:
            self._kw = kweight
        self._dk = dk
        self._dk2 = dk2
        self._window = window
        self._rmin = rmin
        self._rmax = rmax
        self._dr = dr
        self._rwindow = rwindow
        self._kstep = kstep

        self.nfft = nfft
        self.fitspace = fitspace
        self._larch = _larch
        self.rstep = pi/(self.kstep*self.nfft)

        self.kwin_array = None
        self.rwin_array = None

    ## these should all be properties that, when set, erase the
    ## corresponding window function, so that the window will be
    ## recalculated the next time it is needed

    @property
    def kmin(self): return self._kmin

    @property
    def kmax(self): return self._kmax

    @property
    def kw(self): return self._kw

    @property
    def dk(self): return self._dk

    @property
    def dk2(self): return self._dk2

    @property
    def window(self): return self._window

    @property
    def rmin(self): return self._rmin

    @property
    def rmax(self): return self._rmax

    @property
    def rw(self): return self._rw

    @property
    def dr(self): return self._dr

    @property
    def rwindow(self): return self._rwindow


    @property
    def kstep(self): return self._kstep

    @kmin.setter
    def kmin(self, val):
        self.kwin_array = None
        self._kmin = val

    @kmax.setter
    def kmax(self, val):
        self.kwin_array = None
        self._kmax = val

    @kw.setter
    def kw(self, val):
        self.kwin_array = None
        self._kw = val

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

    def calc_model(self):
        """calculate model spectra from pathlist -- essentially ff2chi"""
        _ff2chi(self.pathlist, _larch =_larch, group=self.model)

    def apply_transform(self):
        if not isinstance(self.filter, FilterGroup):
            self.filter.apply(self.datagroup.k, self.datagroup.chi)


class Feffit(Minimizer):
    def __init__(self, pathlist, params, _larch=None, **kws):
        Minimizer.__init__(self, self._feffit, params, _larch=_larch, **kws)

    def _feffit(self, x):
        """residual function for feffit"""

def feffit_fit(_larch=None):
    print( 'not yet!')


def feffit_dataset(data=None, pathlist=None, filter=None, _larch=None):
    return FeffitDataSet(data=data, pathlist=pathlist, filter=filter, _larch=_larch)


def feffit_filter(_larch=None, **kws):
    return FilterGroup(_larch=_larch, **kws)

def registerLarchPlugin():
    print( '====== test FEFFIT ======')
    return ('_xafs', {'feffit_fit': feffit_fit,
                      'feffit_dataset': feffit_dataset,
                      'feffit_filter': feffit_filter,


                      })
