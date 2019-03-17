#!/usr/bin/env python
"""
   feffit sums Feff paths to match xafs data
"""
from collections import Iterable
from copy import copy, deepcopy
from functools import partial
import numpy as np
from numpy import array, arange, interp, pi, zeros, sqrt, concatenate

from scipy.optimize import leastsq as scipy_leastsq

from lmfit import Parameters, Parameter, Minimizer, fit_report
from lmfit.printfuncs import gformat

from larch import Group, isNamedClass

from ..math import index_of, realimag, complex_phase
from ..fitting import (correlated_values, eval_stderr,
                       group2params, params2group, isParameter)

from .xafsutils import set_xafsGroup
from .xafsft import xftf_fast, xftr_fast, ftwindow
from .sigma2_models import sigma2_correldebye, sigma2_debye
from .feffdat import PATHPAR_FMT, FeffPathGroup, ff2chi

class TransformGroup(Group):
    """A Group of transform parameters.
    The apply() method will return the result of applying the transform,
    ready to use in a Fit.   This caches the FT windows (k and r windows)
    and assumes that once created (not None), these do not need to be
    recalculated....

    That is: don't simply change the parameters and expect different results.
    If you do change parameters, reset kwin / rwin to None to cause them to be
    recalculated.
    """
    def __init__(self, kmin=0, kmax=20, kweight=2, dk=4, dk2=None,
                 window='kaiser', nfft=2048, kstep=0.05,
                 rmin = 0, rmax=10, dr=0, dr2=None, rwindow='hanning',
                 fitspace='r', wavelet_mask=None, _larch=None, **kws):
        Group.__init__(self, **kws)
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
        self.dr2 = dr2
        if dr2 is None: self.dr2 = self.dr
        self.rwindow = rwindow
        self.__nfft = 0
        self.__kstep = None
        self.nfft  = nfft
        self.kstep = kstep
        self.rstep = pi/(self.kstep*self.nfft)

        self.fitspace = fitspace
        self.wavelet_mask = wavelet_mask
        self._cauchymask = None

        self._larch = _larch

        self.kwin = None
        self.rwin = None
        self.make_karrays()

    def __repr__(self):
        return '<FeffitTransform Group: %s>' % self.__name__

    def __copy__(self):
        return TransformGroup(kmin=self.kmin, kmax=self.kmax,
                              kweight=self.kweight, dk=self.dk, dk2=self.dk2,
                              window=self.window, kstep=self.kstep,
                              rmin=self.rmin, rmax=self.rmax,
                              dr=self.dr, dr2=self.dr2,
                              rwindow=self.rwindow, nfft=self.nfft,
                              fitspace=self.fitspace,
                              wavelet_mask=self.wavelet_mask,
                              _larch=self._larch)

    def __deepcopy__(self, memo):
        return TransformGroup(kmin=self.kmin, kmax=self.kmax,
                              kweight=self.kweight, dk=self.dk, dk2=self.dk2,
                              window=self.window, kstep=self.kstep,
                              rmin=self.rmin, rmax=self.rmax,
                              dr=self.dr, dr2=self.dr2,
                              rwindow=self.rwindow, nfft=self.nfft,
                              fitspace=self.fitspace,
                              wavelet_mask=self.wavelet_mask,
                              _larch=self._larch)

    def make_karrays(self, k=None, chi=None):
        "this should be run in kstep or nfft changes"
        if self.kstep == self.__kstep and self.nfft == self.__nfft:
            return
        self.__kstep = self.kstep
        self.__nfft = self.nfft

        self.rstep = pi/(self.kstep*self.nfft)
        self.k_ = self.kstep * arange(self.nfft, dtype='float64')
        self.r_ = self.rstep * arange(self.nfft, dtype='float64')

    def _xafsft(self, chi, group=None, rmax_out=10, **kws):
        "returns "
        for key, val in kws:
            if key == 'kw':
                key = 'kweight'
            setattr(self, key, val)
        self.make_karrays()

        out = self.fftf(chi)

        irmax = int(min(self.nfft/2, 1.01 + rmax_out/self.rstep))

        group = set_xafsGroup(group, _larch=self._larch)
        r   = self.rstep * arange(irmax)
        mag = sqrt(out.real**2 + out.imag**2)
        group.kwin  =  self.kwin[:len(chi)]
        group.r    =  r[:irmax]
        group.chir =  out[:irmax]
        group.chir_mag =  mag[:irmax]
        group.chir_pha =  complex_phase(out[:irmax])
        group.chir_re  =  out.real[:irmax]
        group.chir_im  =  out.imag[:irmax]

    def get_kweight(self):
        "if kweight is a list/tuple, use only the first one here"
        if isinstance(self.kweight, Iterable):
            return self.kweight[0]
        return self.kweight

    def fftf(self, chi, kweight=None):
        """ forward FT -- meant to be used internally.
        chi must be on self.k_ grid"""
        if self.kstep != self.__kstep or self.nfft != self.__nfft:
            self.make_karrays()
        if self.kwin is None:
            self.kwin = ftwindow(self.k_, xmin=self.kmin, xmax=self.kmax,
                                 dx=self.dk, dx2=self.dk2, window=self.window)
        if kweight is None:
            kweight = self.get_kweight()
        cx = chi * self.kwin[:len(chi)] * self.k_[:len(chi)]**kweight
        return xftf_fast(cx, kstep=self.kstep, nfft=self.nfft)

    def fftr(self, chir):
        " reverse FT -- meant to be used internally"
        if self.kstep != self.__kstep or self.nfft != self.__nfft:
            self.make_karrays()
        if self.rwin is None:
            self.rwin = ftwindow(self.r_, xmin=self.rmin, xmax=self.rmax,
                                 dx=self.dr, dx2=self.dr2, window=self.rwindow)

        cx = chir * self.rwin[:len(chir)]
        return xftr_fast(cx, kstep=self.kstep, nfft=self.nfft)


    def make_cwt_arrays(self, nkpts, nrpts):
        if self.kstep != self.__kstep or self.nfft != self.__nfft:
            self.make_karrays()
        if self.kwin is None:
            self.kwin = ftwindow(self.k_, xmin=self.kmin, xmax=self.kmax,
                                 dx=self.dk, dx2=self.dk2, window=self.window)

        if self._cauchymask is None:
            if self.wavelet_mask is not None:
                self._cauchymask = self.wavelet_mask
            else:
                ikmin = int(max(0, 0.01 + self.kmin/self.kstep))
                ikmax = int(min(self.nfft/2,  0.01 + self.kmax/self.kstep))
                irmin = int(max(0, 0.01 + self.rmin/self.rstep))
                irmax = int(min(self.nfft/2,  0.01 + self.rmax/self.rstep))
                cm = np.zeros(nrpts*nkpts, dtype='int').reshape(nrpts, nkpts)
                cm[irmin:irmax, ikmin:ikmax] = 1
                self._cauchymask = cm
                self._cauchyslice =(slice(irmin, irmax), slice(ikmin, ikmax))

    def cwt(self, chi, rmax=None, kweight=None):
        """cauchy wavelet transform -- meant to be used internally"""
        if self.kstep != self.__kstep or self.nfft != self.__nfft:
            self.make_karrays()
        nkpts = len(chi)
        nrpts = int(np.round(self.rmax/self.rstep))
        if self.kwin is None:
            self.make_cwt_arrays(nkpts, nrpts)

        omega = pi*np.arange(self.nfft)/(self.kstep*self.nfft)

        if kweight is None:
            kweight = self.get_kweight()
        if kweight != 0:
            chi = chi * self.kwin[:len(chi)] * self.k_[:len(chi)]**kweight

        if rmax is not None:
            self.rmax = rmax

        chix   = np.zeros(int(self.nfft/2)) * self.kstep
        chix[:nkpts] = chi
        chix   = chix[:int(self.nfft/2)]
        _ffchi = np.fft.fft(chix, n=2*self.nfft)[:self.nfft]

        nrpts = int(np.round(self.rmax/self.rstep))
        r   = self.rstep * arange(nrpts)
        r[0] = 1.e-19
        alpha = nrpts/(2*r)

        self.make_cwt_arrays(nkpts, nrpts)

        cauchy_sum = np.log(2*pi) - np.log(1.0+np.arange(nrpts)).sum()

        out = np.zeros(nrpts*nkpts, dtype='complex128').reshape(nrpts, nkpts)

        for i in range(nrpts):
            aom = alpha[i]*omega
            filt = cauchy_sum + nrpts*np.log(aom) - aom
            out[i, :] = np.fft.ifft(np.exp(filt)*_ffchi, 2*self.nfft)[:nkpts]

        return (out*self._cauchymask)[self._cauchyslice]

class FeffitDataSet(Group):
    def __init__(self, data=None, pathlist=None, transform=None,
                 epsilon_k=None, _larch=None, **kws):
        self._larch = _larch
        Group.__init__(self, **kws)

        self.pathlist = pathlist

        self.data = data
        if transform is None:
            transform = TransformGroup()
        self.transform = transform
        if epsilon_k is not None:
            self.data.epsilon_k = epsilon_k

        self.model = Group()
        self.model.k = None
        self.__chi = None
        self.__prepared = False

    def __repr__(self):
        return '<FeffitDataSet Group: %s>' % self.__name__

    def __copy__(self):
        return FeffitDataSet(data=copy(self.data),
                             pathlist=self.pathlist[:],
                             transform=copy(self.transform),
                             _larch=self._larch)

    def __deepcopy__(self, memo):
        return FeffitDataSet(data=deepcopy(self.data),
                             pathlist=self.pathlist[:],
                             transform=deepcopy(self.transform),
                             _larch=self._larch)

    def prepare_fit(self):
        """prepare for fit with this dataset"""

        trans = self.transform
        trans.make_karrays()
        ikmax = int(1.01 + max(self.data.k)/trans.kstep)

        # ikmax = index_of(trans.k_, max(self.data.k))
        self.model.k = trans.k_[:ikmax]
        self.__chi = interp(self.model.k, self.data.k, self.data.chi)
        self.n_idp = 1 + 2*(trans.rmax-trans.rmin)*(trans.kmax-trans.kmin)/pi

        if getattr(self.data, 'epsilon_k', None) is not None:
            eps_k = self.data.epsilon_k
            if isinstance(eps_k, np.ndarray):
                eps_k = interp(self.model.k, self.data.k, self.data.epsilon_k)
            self.set_epsilon_k(eps_k)
        else:
            self.estimate_noise(chi=self.__chi, rmin=15.0, rmax=30.0)
            # uncertainty in chi(k) from autobk or other source
            if hasattr(self.data, 'delta_chi'):
                if isinstance(self.epsilon_k, (list, tuple)):
                    eps_ave = 0.
                    for eps in self.epsilon_k:
                        eps_ave += eps
                    self.epsilon_k = eps_ave/len(self.epsilon_k)
                _dchi = interp(self.model.k, self.data.k, self.data.delta_chi)
                eps_k = np.sqrt(_dchi**2 + self.epsilon_k**2)
                self.set_epsilon_k(eps_k)

        # for each path in the pathlist, setup the Path Parameters to
        # use the current fiteval namespace
        for path in self.pathlist:
            path.create_path_params()
            if path.spline_coefs is None:
                path.create_spline_coefs()

        self.__prepared = True


    def estimate_noise(self, chi=None, rmin=15.0, rmax=30.0, all_kweights=True):
        """estimage noise in a chi spectrum from its high r components"""
        trans = self.transform
        trans.make_karrays()
        if chi is None: chi = self.__chi

        save = trans.rmin, trans.rmax, trans.fitspace

        all_kweights = all_kweights and isinstance(trans.kweight, Iterable)
        if all_kweights:
            chir = [trans.fftf(chi, kweight=kw) for kw in trans.kweight]
        else:
            chir = [trans.fftf(chi)]
        irmin = int(0.01 + rmin/trans.rstep)
        irmax = int(min(trans.nfft/2, 1.01 + rmax/trans.rstep))
        highr = [realimag(chir_[irmin:irmax]) for chir_ in chir]
        # get average of window function value, we will scale eps_r scale by this
        kwin_ave = trans.kwin.sum()*trans.kstep/(trans.kmax-trans.kmin)
        eps_r = [(sqrt((chi*chi).sum() / len(chi)) / kwin_ave) for chi in highr]
        eps_k = []
        # use Parseval's theorem to convert epsilon_r to epsilon_k,
        # compensating for kweight
        if all_kweights:
            kweights = trans.kweight[:]
        else:
            kweights = [trans.kweight]

        for i, kw in enumerate(kweights):
            w = 2 * kw + 1
            scale = sqrt((2*pi*w)/(trans.kstep*(trans.kmax**w - trans.kmin**w)))
            eps_k.append(scale*eps_r[i])

        trans.rmin, trans.rmax, trans.fitspace = save

        ## self.n_idp  = 1 + 2*(trans.rmax-trans.rmin)*(trans.kmax-trans.kmin)/pi
        self.epsilon_k = eps_k
        self.epsilon_r = eps_r
        if len(eps_r) == 1:
            self.epsilon_k = eps_k[0]
            self.epsilon_r = eps_r[0]
        if isinstance(eps_r, np.ndarray):
            self.epsilon_r = eps_r.mean()

    def set_epsilon_k(self, eps_k):
        """set epsilon_k and epsilon_r -- ucertainties in chi(k) and chi(R)"""
        trans = self.transform
        all_kweights = isinstance(trans.kweight, Iterable)
        if isinstance(trans.kweight, Iterable):
            self.epsilon_k = []
            self.epsilon_r = []
            for kw in trans.kweight:
                w = 2 * kw + 1
                scale = 2*sqrt((pi*w)/(trans.kstep*(trans.kmax**w - trans.kmin**w)))
                self.epsilon_k.append(eps_k)
                eps_r = eps_k / scale
                if isinstance(eps_r, np.ndarray): eps_r = eps_r.mean()
                self.epsilon_r.append(eps_r)

        else:
            w = 2 * trans.get_kweight() + 1
            scale = 2*sqrt((pi*w)/(trans.kstep*(trans.kmax**w - trans.kmin**w)))
            self.epsilon_k = eps_k
            eps_r = eps_k / scale
            if isinstance(eps_r, np.ndarray): eps_r = eps_r.mean()
            self.epsilon_r = eps_r


    def _residual(self, paramgroup, data_only=False, **kws):
        """return the residual for this data set
        residual = self.transform.apply(data_chi - model_chi)
        where model_chi is the result of ff2chi(pathlist)
        """
        if not isNamedClass(self.transform, TransformGroup):
            return
        if not self.__prepared:
            self.prepare_fit()

        ff2chi(self.pathlist, paramgroup=paramgroup, k=self.model.k,
                _larch=self._larch, group=self.model)

        eps_k = self.epsilon_k
        if isinstance(eps_k, np.ndarray):
            eps_k[np.where(eps_k<1.e-12)[0]] = 1.e-12

        diff  = (self.__chi - self.model.chi)
        if data_only:  # for extracting transformed data separately from residual
            diff  = self.__chi
        trans = self.transform
        k     = trans.k_[:len(diff)]

        all_kweights = isinstance(trans.kweight, Iterable)
        if trans.fitspace == 'k':
            iqmin = int(max(0, 0.01 + trans.kmin/trans.kstep))
            iqmax = int(min(trans.nfft/2,  0.01 + trans.kmax/trans.kstep))
            if all_kweights:
                out = []
                for i, kw in enumerate(trans.kweight):
                    out.append(((diff/eps_k[i])*k**kw)[iqmin:iqmax])
                return np.concatenate(out)
            else:
                return ((diff/eps_k) * k**trans.kweight)[iqmin:iqmax]
        elif trans.fitspace == 'w':
            if all_kweights:
                out = []
                for i, kw in enumerate(trans.kweight):
                    cwt = trans.cwt(diff/eps_k, kweight=kw)
                    out.append(realimag(cwt).ravel())
                return np.concatenate(out)
            else:
                cwt = trans.cwt(diff/eps_k, kweight=trans.kweight)
                return realimag(cwt).ravel()
        else: # 'r' space
            out = []
            if all_kweights:
                chir = [trans.fftf(diff, kweight=kw) for kw in trans.kweight]
                eps_r = self.epsilon_r
            else:
                chir = [trans.fftf(diff)]
                eps_r = [self.epsilon_r]
            if trans.fitspace == 'r':
                irmin = int(max(0, 0.01 + trans.rmin/trans.rstep))
                irmax = int(min(trans.nfft/2,  0.01 + trans.rmax/trans.rstep))
                for i, chir_ in enumerate(chir):
                    chir_ = chir_ / (eps_r[i])
                    out.append(realimag(chir_[irmin:irmax]))
            else:
                chiq = [trans.fftr(c)/eps for c, eps in zip(chir, eps_r)]
                iqmin = int(max(0, 0.01 + trans.kmin/trans.kstep))
                iqmax = int(min(trans.nfft/2,  0.01 + trans.kmax/trans.kstep))
                for chiq_ in chiq:
                    out.append( realimag(chiq_[iqmin:iqmax])[::2])
            return np.concatenate(out)

    def save_ffts(self, rmax_out=10, path_outputs=True):
        "save fft outputs"
        xft = self.transform._xafsft
        xft(self.__chi,   group=self.data,  rmax_out=rmax_out)
        xft(self.model.chi, group=self.model, rmax_out=rmax_out)
        if path_outputs:
            for p in self.pathlist:
                xft(p.chi, group=p, rmax_out=rmax_out)

def feffit_dataset(data=None, pathlist=None, transform=None,
                   epsilon_k=None, _larch=None):
    """create a Feffit Dataset group.

     Parameters:
     ------------
      data:      group containing experimental EXAFS (needs arrays 'k' and 'chi').
      pathlist:  list of FeffPath groups, as created from feffpath()
      transform: Feffit Transform group.
      epsilon_k: Uncertainty in data (either single value or array of
                 same length as data.k)

     Returns:
     ----------
      a Feffit Dataset group.


    """
    return FeffitDataSet(data=data, pathlist=pathlist,
                         transform=transform, _larch=_larch)

def feffit_transform(_larch=None, **kws):
    """create a feffit transform group

     Parameters:
     --------------
       fitspace: name of FT type for fit  ('r').
       kmin:     starting *k* for FT Window (0).
       kmax:     ending *k* for FT Window (20).
       dk:       tapering parameter for FT Window (4).
       dk2:      second tapering parameter for FT Window (None).
       window:   name of window type ('kaiser').
       nfft:     value to use for N_fft (2048).
       kstep:    value to use for delta_k (0.05).
       kweight:  exponent for weighting spectra by k^kweight (2).
       rmin:     starting *R* for Fit Range and/or reverse FT Window (0).
       rmax:     ending *R* for Fit Range and/or reverse FT Window (10).
       dr:       tapering parameter for reverse FT Window 0.
       rwindow:  name of window type for reverse FT Window ('kaiser').

     Returns:
     ----------
       a feffit transform group.

    """
    return TransformGroup(_larch=_larch, **kws)

def feffit(paramgroup, datasets, rmax_out=10, path_outputs=True, _larch=None, **kws):
    """execute a Feffit fit: a fit of feff paths to a list of datasets

    Parameters:
    ------------
      paramgroup:   group containing parameters for fit
      datasets:     Feffit Dataset group or list of Feffit Dataset group.
      rmax_out:     maximum R value to calculate output arrays.
      path_output:  Flag to set whether all Path outputs should be written.

    Returns:
    ---------
      a fit results group.  This will contain subgroups of:

        datasets: an array of FeffitDataSet groups used in the fit.
        params:   This will be identical to the input parameter group.
        fit:      an object which points to the low-level fit.

     Statistical parameters will be put into the params group.  Each
     dataset will have a 'data' and 'model' subgroup, each with arrays:
        k            wavenumber array of k
        chi          chi(k).
        kwin         window Omega(k) (length of input chi(k)).
        r            uniform array of R, out to rmax_out.
        chir         complex array of chi(R).
        chir_mag     magnitude of chi(R).
        chir_pha     phase of chi(R).
        chir_re      real part of chi(R).
        chir_im      imaginary part of chi(R).
    """


    def _resid(params, datasets=None, paramgroup=None, **kwargs):
        """ this is the residual function"""
        params2group(params, paramgroup)
        return concatenate([d._residual(paramgroup) for d in datasets])

    if isNamedClass(datasets, FeffitDataSet):
        datasets = [datasets]

    params = group2params(paramgroup, _larch=_larch)

    for ds in datasets:
        if not isNamedClass(ds, FeffitDataSet):
            print( "feffit needs a list of FeffitDataSets")
            return
        ds.prepare_fit()

    fit = Minimizer(_resid, params,
                    fcn_kws=dict(datasets=datasets,
                                 paramgroup=paramgroup),
                    scale_covar=True, **kws)

    result = fit.leastsq()

    params2group(result.params, paramgroup)
    dat = concatenate([d._residual(paramgroup, data_only=True) for d in datasets])

    n_idp = 0
    for ds in datasets:
        n_idp += ds.n_idp

    # here we rescale chi-square and reduced chi-square to n_idp
    npts =  len(result.residual)
    chi_square  = result.chisqr * n_idp*1.0 / npts
    chi_reduced = chi_square/(n_idp*1.0 - result.nvarys)
    rfactor = (result.residual**2).sum() / (dat**2).sum()
    # calculate 'aic', 'bic' rescaled to n_idp
    # note that neg2_loglikel is -2*log(likelihood)
    neg2_loglikel = n_idp * np.log(chi_square / n_idp)
    aic = neg2_loglikel + 2 * result.nvarys
    bic = neg2_loglikel + np.log(n_idp) * result.nvarys


    # With scale_covar = True, Minimizer() scales the uncertainties
    # by reduced chi-square assuming params.nfree is the correct value
    # for degrees-of-freedom. But n_idp-params.nvarys is a better measure,
    # so we rescale uncertainties here.

    covar = getattr(result, 'covar', None)
    # print("COVAR " , covar)
    if covar is not None:
        err_scale = (result.nfree / (n_idp - result.nvarys))
        for name in result.var_names:
            p = result.params[name]
            if isParameter(p) and p.vary:
                p.stderr *= sqrt(err_scale)

        # next, propagate uncertainties to constraints and path parameters.
        result.covar *= err_scale
        vsave, vbest = {}, []

        # 1. save current params
        for vname in result.var_names:
            par = result.params[vname]
            vsave[vname] = par
            vbest.append(par.value)

        # 2. get correlated uncertainties, set params accordingly
        uvars = correlated_values(vbest, result.covar)
        # 3. evaluate constrained params, save stderr
        for nam, obj in result.params.items():
            eval_stderr(obj, uvars,  result.var_names, result.params)

        # 3. evaluate path params, save stderr
        for ds in datasets:
            for p in ds.pathlist:
                p.store_feffdat()
                for pname in ('degen', 's02', 'e0', 'ei',
                              'deltar', 'sigma2', 'third', 'fourth'):
                    obj = p.params[PATHPAR_FMT % (pname, p.label)]
                    eval_stderr(obj, uvars,  result.var_names, result.params)


        # restore saved parameters again
        for vname in result.var_names:
            # setattr(params, vname, vsave[vname])
            params[vname] = vsave[vname]

        # clear any errors evaluting uncertainties
        if _larch is not None and (len(_larch.error) > 0):
            _larch.error = []

    # reset the parameters group with the newly updated uncertainties
    params2group(result.params, paramgroup)

    # here we create outputs arrays for chi(k), chi(r):
    for ds in datasets:
        ds.save_ffts(rmax_out=rmax_out, path_outputs=path_outputs)

    out = Group(name='feffit results', datasets=datasets,
                fitter=fit, fit_details=result, chi_square=chi_square,
                n_independent=n_idp, chi_reduced=chi_reduced,
                rfactor=rfactor, aic=aic, bic=bic, covar=covar)

    for attr in ('params', 'nvarys', 'nfree', 'ndata', 'var_names', 'nfev',
                 'success', 'errorbars', 'message', 'lmdif_message'):
        setattr(out, attr, getattr(result, attr, None))
    return out


def feffit_report(result, min_correl=0.1, with_paths=True, _larch=None):
    """return a printable report of fit for feffit

    Parameters:
    ------------
      result:      Feffit result, output group from feffit()
      min_correl:  minimum correlation to report [0.1]
      wit_paths:   boolean (True/False) for whether to list all paths [True]

    Returns:
    ---------
      printable string of report.

    """
    input_ok = False
    try:
        params = result.params
        datasets = result.datasets
        input_ok = True
    except:
        pass
    if not input_ok:
        print( 'must pass output of feffit()!')
        return

    topline = '=================== FEFFIT RESULTS ===================='
    header = '[[%s]]'
    varformat  = '   %12s = %s +/-%s   (init= %s)'
    fixformat  = '   %12s = %s (fixed)'
    exprformat = '   %12s = %s +/-%s  = \'%s\''
    out = [topline, header % 'Statistics']

    out.append('   nvarys, npts       =  %i, %i' % (result.nvarys,
                                                   result.ndata))
    out.append('   n_independent      =  %.3f'  % (result.n_independent))
    out.append('   chi_square         = %s'  % gformat(result.chi_square))
    out.append('   reduced chi_square = %s'  % gformat(result.chi_reduced))
    out.append('   r-factor           = %s'  % gformat(result.rfactor))
    out.append('   Akaike info crit   = %s'  % gformat(result.aic))
    out.append('   Bayesian info crit = %s'  % gformat(result.bic))
    out.append(' ')

    if len(datasets) == 1:
        out.append(header % 'Data')
    else:
        out.append(header % 'Datasets (%i)' % len(datasets))
    for i, ds in enumerate(datasets):
        tr = ds.transform
        if len(datasets) > 1:
            out.append(' dataset %i:' % (i+1))
        if isinstance(tr.kweight, Iterable):
            if isinstance(ds.epsilon_k[0], np.ndarray):
                msg = []
                for eps in ds.epsilon_k:
                    msg.append('Array(mean=%s, std=%s)' % (gformat(eps.mean()).strip(),
                                                           gformat(eps.std()).strip()))
                eps_k = ', '.join(msg)
            else:
                eps_k = ', '.join([gformat(eps).strip() for eps in ds.epsilon_k])
            eps_r = ', '.join([gformat(eps).strip() for eps in ds.epsilon_r])
            kweigh = ', '.join(['%i' % kwe for kwe in tr.kweight])
        else:
            if isinstance(ds.epsilon_k, np.ndarray):
                eps_k = 'Array(mean=%s, std=%s)' % (gformat(ds.epsilon_k.mean()).strip(),
                                                    gformat(ds.epsilon_k.std()).strip())
            else:
                eps_k = gformat(ds.epsilon_k)
            eps_r = gformat(ds.epsilon_r).strip()
            kweigh = '%i' % tr.kweight
        out.append('   fit space          = \'%s\''  % (tr.fitspace))
        out.append('   r-range            = %.3f, %.3f' % (tr.rmin, tr.rmax))
        out.append('   k-range            = %.3f, %.3f' % (tr.kmin, tr.kmax))
        kwin = '   k window, dk       = \'%s\', %.3f'   % (tr.window, tr.dk)
        if tr.dk2 is not None:
            kwin = "%s, %.3f" % (kwin, tr.dk2)
        out.append(kwin)
        pathfiles = [p.filename for p in ds.pathlist]
        out.append('   paths used in fit  = %s' % (repr(pathfiles)))
        out.append('   k-weight           = %s' % kweigh)
        out.append('   epsilon_k          = %s'  % eps_k)
        out.append('   epsilon_r          = %s'  % eps_r)
        out.append('   n_independent      = %.3f'  % (ds.n_idp))
        #
    out.append(' ')
    out.append(header % 'Variables')

    # exprs = []
    for name, par in params.items():
        # var = getattr(params, name)
        # print(name, par, dir(par))
        if len(name) < 14:
            name = (name + ' '*14)[:14]
        if isParameter(par):
            if par.vary:
                stderr = 'unknown'
                if par.stderr is not None:
                    stderr = gformat(par.stderr)
                out.append(varformat % (name, gformat(par.value),
                                        stderr, gformat(par.init_value)))

            elif par.expr is not None:
                stderr = 'unknown'
                if par.stderr is not None:
                    stderr = gformat(par.stderr)
                out.append(exprformat % (name, gformat(par.value),
                                         stderr, par.expr))
            else:
                out.append(fixformat % (name, gformaat(par.value)))
    # if len(exprs) > 0:
    #     out.append(header % 'Constraint Expressions')
    #     out.extend(exprs)

    covar_vars = result.var_names
    if len(covar_vars) > 0:
        out.append(' ')
        out.append(header % 'Correlations' +
                   '    (unreported correlations are < % .3f)' % min_correl)
        correls = {}
        for i, name in enumerate(covar_vars):
            par = params[name]
            if not par.vary:
                continue
            if hasattr(par, 'correl') and par.correl is not None:
                for name2 in covar_vars[i+1:]:
                    if name != name2 and name2 in par.correl:
                        correls["%s, %s" % (name, name2)] = par.correl[name2]

        sort_correl = sorted(correls.items(), key=lambda it: abs(it[1]))
        sort_correl.reverse()
        for name, val in sort_correl:
            if abs(val) < min_correl:
                break
            if len(name) < 20:
                name = (name + ' '*20)[:20]
            out.append('   %s = % .3f' % (name, val))

    if with_paths:
        out.append(' ')
        out.append(header % 'Paths')
        for ids, ds in enumerate(datasets):
            if len(datasets) > 1:
                out.append(' dataset %i:' % (ids+1))
            for p in ds.pathlist:
                out.append('%s\n' % p.report())
    out.append('='*len(topline))
    return '\n'.join(out)
