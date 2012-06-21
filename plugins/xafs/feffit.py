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
    If you do change parameters, reset kwin / rwin to None.

    """
    def __init__(self, kmin=0, kmax=20, kweight=1, dk=1, dk2=None,
                 window='kaiser', nfft=2048, kstep=0.05,
                 rmin = 0, rmax=10, dr=0, rwindow='kaiser',
                 fitspace='r', _larch=None, **kws):
        larch.Group.__init__(self)
        self.kmin = kmin
        self.kmax = kmax
        self.kweight = kweight
        if 'kw' in kws:
            self.kweight = kws['kw']
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

        self.kwin = None
        self.rwin = None
        self.make_karrays()

    def make_karrays(self, k=None, chi=None):
        "this should be run in kstep or nfft changes"
        if self.kstep == self.__kstep and self.nfft == self.__nfft:
            return
        self.__kstep = self.kstep
        self.__nfft = self.nfft

        self.rstep = pi/(self.kstep*self.nfft)
        self.k_ = self.kstep * arange(self.nfft, dtype='float64')
        self.r_ = self.rstep * arange(self.nfft, dtype='float64')

    def estimate_noise(self, chi, rmin=15.0, rmax=25.0):
        """estimage noice from high r"""
        # print 'Estimate Noise!! ', rmin, self.transform.rmin
        self.make_karrays()

        save = self.rmin, self.rmax, self.fitspace

        # get chi(r) for high r
        highr = self.apply(chi, eps_scale=False,
                           fitspace='r', rmin=rmin, rmax=rmax)

        # get average of window function value, and eps_r scale by this
        ikmin = index_of(self.k_, self.kmin)
        ikmax = index_of(self.k_, self.kmax)
        kwin_ave = self.kwin[ikmin:ikmax].sum()/(ikmax-ikmin)

        eps_r = sqrt((highr*highr).sum() / len(highr)) / kwin_ave

        # use Parseval's theorem to convert epsilon_r to epsilon_k,
        # compensating for kweight
        w = 2 * self.kweight + 1
        scale = sqrt((2*pi*w)/(self.kstep*(self.kmax**w - self.kmin**w)))
        eps_k = scale*eps_r

        self.rmin, self.rmax, self.fitspace = save

        self.n_idp  = 2*(self.rmax-self.rmin)*(self.kmax-self.kmin)/pi
        self.epsilon_k = eps_k
        self.epsilon_r = eps_r

    def set_epsilon_k(self, eps_k):
        """set epsilon_k and epsilon_r -- ucertainties in chi(k) and chi(R)"""
        w = 2 * self.kweight + 1
        scale = 2*sqrt((pi*w)/(self.kstep*(self.kmax**w - self.kmin**w)))
        eps_r = eps_k / scale
        self.epsilon_k = eps_k
        self.epsilon_r = eps_r

    def xafsft(self, chi, group=None, rmax_out=10, **kws):
        "returns "
        for key, val in kws:
            if key == 'kw': key = 'kweight'
            setattr(self, key, val)
        self.make_karrays()

        out = self.fftf(chi)

        irmax = min(self.nfft/2, int(1.01 + rmax_out/self.rstep))
        if self._larch.symtable.isgroup(group):
            r   = self.rstep * arange(irmax)
            mag = sqrt(out.real**2 + out.imag**2)
            group.kwin  =  self.kwin[:len(chi)]
            group.r    =  r[:irmax]
            group.chir =  out[:irmax]
            group.chir_mag =  mag[:irmax]
            group.chir_re  =  out.real[:irmax]
            group.chir_im  =  out.imag[:irmax]
        else:
            return out[:irmax]

    def fftf(self, chi):
        """ forward FT -- meant to be used internally.
        chi must be on self.k_ grid"""
        self.make_karrays()
        if self.kwin is None:
            self.kwin = ftwindow(self.k_, xmin=self.kmin, xmax=self.kmax,
                                 dx=self.dk, dx2=self.dk2, window=self.window)

        cx = chi * self.kwin[:len(chi)] * self.k_[:len(chi)]**self.kweight
        return xafsft_fast(cx, kstep=self.kstep, nfft=self.nfft)

    def ffti(self, chir):
        " reverse FT -- meant to be used internally"
        self.make_karrays()
        if self.rwin is None:
            self.rwin = ftwindow(self.r_, xmin=self.rmin, xmax=self.rmax,
                                 dx=self.dr, dx2=self.dr2, window=self.rwindow)

        cx = chir * self.rwin[:len(chir)] * self.r_[:len(chir)]**self.rw,
        return xafsift_fast(cx, kstep=self.kstep, nfft=self.nfft)

    def apply(self, chi, eps_scale=False, **kws):
        """apply transform, returns real/imag components
        eps_scale: scale by appropriaat epsilon_k or epsilon_r
        """
        # print 'this  is transform apply ', len(k), len(chi), k[5:10], chi[5:10], kws
        for key, val in kws.items():
            if key == 'kw': key = 'kweight'
            setattr(self, key, val)

        # print 'fit space = ', self.fitspace
        if self.fitspace == 'k':
            return chi * self.k_[:len(chi)]**self.kweight
        elif self.fitspace in ('r', 'q'):
            self.make_karrays()
            chir = self.fftf(chi)
            if self.fitspace == 'r':
                irmin = int(0.01 + self.rmin/self.rstep)
                irmax = min(self.nfft/2,  int(1.01 + self.rmax/self.rstep))
                if eps_scale:
                    chir = chir /(self.epsilon_r)
                return realimag(chir[irmin:irmax])
            else:
                chiq = self.ffti(self.r_, chir)
                iqmin = int(0.01 + self.kmin/self.kstep)
                iqmax = min(self.nfft/2,  int(1.01 + self.kmax/self.kstep))
                return realimag(chiq[ikmin:ikmax])

class FeffitDataSet(larch.Group):
    def __init__(self, data=None, pathlist=None, transform=None, _larch=None, **kws):

        self._larch = _larch
        larch.Group.__init__(self,  residual=self.residual, **kws)

        self.pathlist = pathlist

        self.data = data
        if transform is None:
            transform = TransformGroup()
        self.transform = transform
        self.model = larch.Group()
        self.model.k = None
        self.datachi = None
        self.__prepared = False

    def prepare_fit(self):
        trans = self.transform

        trans.make_karrays()
        ikmax = int(1.01 + max(self.data.k)/trans.kstep)
        # ikmax = index_of(trans.k_, max(self.data.k))
        self.model.k = trans.k_[:ikmax]
        self.datachi = interp(self.model.k, self.data.k, self.data.chi)

        if hasattr(self.data, 'epsilon_k'):
            eps_k = self.data.epsilon_k
            if isinstance(self.eps_k, numpy.ndarray):
                eps_k = interp(self.model.k, self.data.k, self.data.epsilon_k)
                trans.set_epsilon_k(eps_k)
        else:
            trans.estimate_noise(self.datachi, rmin=15.0, rmax=25.0)

        self.__prepared = True

    def residual(self, paramgroup=None):
        if (paramgroup is not None and
            self._larch.symtable.isgroup(paramgroup)):
            self._larch.symtable._sys.paramGroup = paramgroup
        if not isinstance(self.transform, TransformGroup):
            print "Transform for DataSet is not set"
            return
        if not self.__prepared:
            self.prepare_fit()

        _ff2chi(self.pathlist, k=self.model.k, _larch=self._larch,
                group=self.model)
        return self.transform.apply(self.datachi-self.model.chi, eps_scale=True)

    def save_ffts(self, rmax_out=10):
        self.transform.xafsft(self.datachi,   group=self.data,  rmax_out=rmax_out)
        self.transform.xafsft(self.model.chi, group=self.model, rmax_out=rmax_out)

def feffit(params, datasets, _larch=None, **kws):

    def _resid(params, datasets=None, _larch=None, **kws):
        """ this is the residua function """
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
    # scale uncertainties to sqrt(n_idp - n_varys)
    n_idp = 0
    for ds in datasets:
        n_idp += ds.transform.n_idp
    err_scale = sqrt(n_idp - params.nvarys)
    for name in dir(params):
        p = getattr(params, name)
        if isParameter(p) and p.vary:
            p.stderr *= err_scale

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
