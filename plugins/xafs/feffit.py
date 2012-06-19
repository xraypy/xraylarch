#!/usr/bin/env python
"""
   feffit sums Feff paths to match xafs data
"""

import sys, os
import numpy as np
from numpy import array, arange, interp, pi, zeros, sqrt, concatenate

from scipy.optimize import leastsq as scipy_leastsq

import larch
from larch.larchlib import Parameter, isParameter, plugin_path
from larch.utils import OrderedDict

sys.path.insert(0, plugin_path('std'))
sys.path.insert(0, plugin_path('fitter'))
sys.path.insert(0, plugin_path('xafs'))

from mathutils import index_of, realimag

from minimizer import Minimizer
from xafsft import xafsft, xafsift, xafsft_fast, xafsift_fast, ftwindow

from feffdat import FeffPathGroup, _ff2chi

class TransformGroup(larch.Group):
    """A Group of transform parameters.
    The apply() method will return the result of applying the transform,
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
        self.__nfft = 0
        self.__kstep = None
        self.nfft  = nfft
        self.kstep = kstep
        self.rstep = pi/(self.kstep*self.nfft)

        self.fitspace = fitspace
        self._larch = _larch

        self.kwin_array = None
        self.rwin_array = None
        self.__check_kstep()

    def __check_kstep(self):
        "this should be run in kstep or nfft changes"
        if self.kstep == self.__kstep and self.nfft == self.__nfft:
            return
        self.rstep = pi/(self.kstep*self.nfft)
        self.k_ = self.kstep * arange(self.nfft, dtype='float64')
        self.r_ = self.rstep * arange(self.nfft, dtype='float64')

    def xafsft(self, chi, group=None, rmax_out=10, **kws):
        "returns "
        for key, val in kws:
            if key == 'kweight': key = 'kw'
            setattr(self, key, val)
        self.__check_kstep()

        out = self.__fftf__(chi)

        irmax = min(self.nfft/2, 1 + int(rmax_out/self.rstep))
        if self._larch.symtable.isgroup(group):
            r   = self.rstep * arange(irmax)
            mag = sqrt(out.real**2 + out.imag**2)
            group.r    =  r[:irmax]
            group.chir =  out[:irmax]
            group.chir_mag =  mag[:irmax]
            group.chir_re  =  out.real[:irmax]
            group.chir_im  =  out.imag[:irmax]
        else:
            return out[:irmax]

    def __fftf__(self, chi):
        """ forward FT -- meant to be used internally.
        chi must be on self.k_ grid"""
        self.__check_kstep()
        if self.kwin_array is None:
            self.kwin_array = ftwindow(self.k_, xmin=self.kmin, xmax=self.kmax,
                                       dx=self.dk, dx2=self.dk2,
                                       window=self.window)
        cx = chi * self.kwin_array[:len(chi)] * self.k_[:len(chi)]**self.kw
        return xafsft_fast(cx, kstep=self.kstep, nfft=self.nfft)

    def __ffti__(self, chir):
        " reverse FT -- meant to be used internally"
        self.__check_kstep()
        if self.rwin_array is None:
            self.rwin_array = ftwindow(self.r_, xmin=self.rmin, xmax=self.rmax,
                                       dx=self.dr, dx2=self.dr2,
                                       window=self.rwindow)

        cx = chir * self.rwin_array[:len(chir)] * self.r_[:len(chir)]**self.rw,
        return xafsift_fast(cx, kstep=self.kstep, nfft=self.nfft)

    def apply(self, k, chi, **kws):
        """apply transform"""
        print 'this  is transform apply ', len(k), len(chi), k[5:10], chi[5:10], kws
        for key, val in kws.items():
            if key == 'kweight': key = 'kw'
            setattr(self, key, val)

        print 'fit space = ', self.fitspace
        if self.fitspace == 'k':
            return chi * k**self.kw
        elif self.fitspace in ('r', 'q'):
            self.__check_kstep()
            chir = self.__fftf__(chi)
            if self.fitspace == 'r':
                irmin = index_of(self.r_, self.rmin)
                irmax = min(self.nfft/2,  1 + index_of(self.r_, self.rmax))
                print ' I ', irmin, irmax, len(chir)
                return realimag(chir[irmin:irmax])
            else:
                chiq = self.__ffti__(self.r_, chir)
                iqmin = index_of(self.k_, self.kmin)
                iqmax = min(self.nfft/2,  1 + index(self.k_, self.kmax))
                return realimag(chiq[ikmin:ikmax])

class FeffitDataSet(larch.Group):
    def __init__(self, data=None, pathlist=None, transform=None, _larch=None, **kws):

        self._larch = _larch
        larch.Group.__init__(self,  residual=self._residual, **kws)

        self.pathlist = pathlist

        self.data = data
        if transform is None:
            transform = TransformGroup()
        self.transform = transform
        self.model = larch.Group()
        self.model.k = None
        self.data_chi = None
        self.residual = self._residual
        self.eps_r  = 0
        self.eps_k  = 0

    def estimate_noise(self, rmin=15.0, rmax=25.0):
        """estimage noice from high r"""
        print 'Estimate Noise!! ', rmin, self.transform.rmin
        trans = self.transform
        rmin_save = trans.rmin
        rmax_save = trans.rmax
        fitspace_save = trans.fitspace
        self._make_modelk()
        print 'Have mode.k ' , len(self.model.k), len(self.data_chi)
        chi_highr = trans.apply(self.model.k, self.data_chi,
                                fitspace='r', rmin=rmin, rmax=rmax)
        print type(chi_highr), len(chi_highr)

        eps_r = sqrt( (chi_highr*chi_highr).sum() / len(chi_highr)) # /2

        w = 2 * trans.kw + 1
        kstep = trans.kstep
        kmax = trans.kmax
        kmin = trans.kmin
        print trans.kw, w, kstep, kmin, kmax
        print sqrt( (2*pi* w) / kstep*(kmax**w - kmin**w))
        eps_k = eps_r * sqrt( (2*pi* w) / (kstep*(kmax**w - kmin**w)))

        trans.rmin = rmin_save
        trans.rmax = rmax_save
        trans.fitspace = fitspace_save
        return eps_k, eps_r

    def _make_modelk(self):
        """create model k with uniform kstep and interpolate data onto this"""
        if self.model.k is None:
            # print '_resid create .k ',
            kstep = self.transform.kstep
            nkmax = (0.1*kstep + max(self.data.k)) / kstep
            self.model.k = self.transform.kstep * arange(nkmax)
            self.data_chi =  interp(self.model.k, self.data.k, self.data.chi)

    def _residual(self, paramgroup=None):
        if paramgroup is not None:
            self._larch.symtable._sys.paramGroup = paramgroup
        if not isinstance(self.transform, TransformGroup):
            print "Transform for DataSet is not set"
            return
        self._make_modelk()

        _ff2chi(self.pathlist, _larch =self._larch,
                kstep=self.transform.kstep, kmax=max(self.model.k),
                group=self.model)
        return self.transform.apply(self.model.k, self.data_chi-self.model.chi)

    def save_ffts(self, rmax_out=10):
        # print ' SAVE FFTs ' , len(self.model.k), len(self.data_chi), len(self.model.chi)
        self.transform.xafsft(self.data_chi, group=self.data, rmax_out=rmax_out)
        self.transform.xafsft(self.model.chi, group=self.model, rmax_out=rmax_out)

def feffit(params, datasets, _larch=None, **kws):

    def _resid(params, datasets=None, _larch=None, **kws):
        """ this is the residua function """
        # for p in dir(params):
        #    print 'Param: ', p, getattr(params, p)
        return concatenate([d.residual() for d in datasets])

    if isinstance(datasets, FeffitDataSet):
        datasets = [datasets]
    for ds in datasets:
        if not isinstance(ds, FeffitDataSet):
            print "feffit needs a list of FeffitDataSets"
            return
    fitkws = dict(datasets=datasets)
    fit = Minimizer(_resid, params, fcn_kws=fitkws, _larch=_larch)
    fit.leastsq()
    # here we create outputs:
    for ds in datasets:
        ds.save_ffts()

    out = larch.Group(name='feffit fit results',
                      params = params,
                      datasets = datasets)

    return out

def feffit_dataset(data=None, pathlist=None, transform=None, _larch=None):
    return FeffitDataSet(data=data, pathlist=pathlist, transform=transform, _larch=_larch)

def feffit_transform(_larch=None, **kws):
    return TransformGroup(_larch=_larch, **kws)

def registerLarchPlugin():
    return ('_xafs', {'feffit': feffit,
                      'feffit_dataset': feffit_dataset,
                      'feffit_transform': feffit_transform,


                      })
