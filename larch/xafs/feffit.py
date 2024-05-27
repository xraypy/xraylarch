#!/usr/bin/env python
"""
   feffit sums Feff paths to match xafs data
"""
try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable
from copy import copy, deepcopy
from functools import partial
import ast
import numpy as np
from numpy import array, arange, interp, pi, zeros, sqrt, concatenate

from scipy.interpolate import splrep, splev
from scipy.interpolate import InterpolatedUnivariateSpline as IUSpline
from lmfit import Parameters, Parameter, Minimizer, conf_interval2d
from lmfit.printfuncs import getfloat_attr

from larch import Group, isNamedClass
from larch.utils import fix_varname, gformat
from larch.utils.strutils import b32hash, random_varname
from ..math import index_of, realimag, complex_phase, remove_nans
from ..fitting import (correlated_values, eval_stderr, ParameterGroup,
                       group2params, params2group, isParameter)

from .xafsutils import set_xafsGroup, gfmt
from .xafsft import xftf_fast, xftr_fast, ftwindow
from .autobk import autobk_delta_chi
from .feffdat import FeffPathGroup, ff2chi

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
                 fitspace='r', wavelet_mask=None, rbkg=0, _larch=None, **kws):
        Group.__init__(self, **kws)
        self.kmin = kmin
        self.kmax = kmax
        self.kweight = kweight
        if 'kw' in kws:
            self.kweight = kws['kw']

        self.dk = dk
        self.dk2 = dk2
        self.window = window
        self.rbkg = rbkg
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
                              rmin=self.rmin, rmax=self.rmax, rbkg=self.rbkg,
                              dr=self.dr, dr2=self.dr2,
                              rwindow=self.rwindow, nfft=self.nfft,
                              fitspace=self.fitspace,
                              wavelet_mask=self.wavelet_mask,
                              _larch=self._larch)

    def __deepcopy__(self, memo):
        return TransformGroup(kmin=self.kmin, kmax=self.kmax,
                              kweight=self.kweight, dk=self.dk, dk2=self.dk2,
                              window=self.window, kstep=self.kstep,
                              rmin=self.rmin, rmax=self.rmax, rbkg=self.rbkg,
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
        if self.rwin is None:
            xmin = max(self.rbkg, self.rmin)
            self.rwin = ftwindow(self.r_, xmin=xmin, xmax=self.rmax,
                                 dx=self.dr, dx2=self.dr2, window=self.rwindow)
        group.rwin = self.rwin[:irmax]

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
            xmin = max(self.rbkg, self.rmin)
            self.rwin = ftwindow(self.r_, xmin=xmin, xmax=self.rmax,
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
    def __init__(self, data=None, paths=None, transform=None, epsilon_k=None,
                 refine_bkg=False, model=None, pathlist=None,  _larch=None, **kws):

        self._larch = _larch
        Group.__init__(self, **kws)
        self.refine_bkg = refine_bkg
        if paths is None and pathlist is not None:
            paths = pathlist

        if isinstance(paths, dict):
            self.paths = {key: copy(path) for key, path in paths.items()}
        elif isinstance(paths, (list, tuple)):
            self.paths = {path.label: copy(path) for path in paths}
        else:
            self.paths = {}
        self.pathlist = list(self.paths.values())

        if transform is None:
            transform = TransformGroup()
        else:
            trasform = copy(transform)
        self.transform = transform

        if model is None:
            self.model = Group(__name__='Feffit Model for %s' % repr(data))
            self.model.k = None
        else:
            self.model = model
        # make datagroup from passed in data: copy of k, chi, delta_chi, epsilon_k
        self.set_datagroup(data, epsilon_k=epsilon_k, refine_bkg=refine_bkg)

    def set_datagroup(self, data, epsilon_k=None, refine_bkg=False):
        "set the data group for the Dataset"
        if data is None:
            self.data = Group(__name__='Feffit DatasSet (no data)',
                              groupname=None,filename=None,
                              k=np.arange(401)/20.0, chi=np.zeros(401))
            self.has_data = False
        else:
            self.data = Group(__name__='Feffit DatasSet from %s' % repr(data),
                            groupname=getattr(data, 'groupname', repr(data)),
                            filename=getattr(data, 'filename', repr(data)),
                            k=data.k[:]*1.0, chi=data.chi[:]*1.0)
            self.has_data = True
        if hasattr(data, 'config'):
            self.data.config = deepcopy(data.config)
        else:
            self.data.config = Group()
        self.data.epsilon_k = getattr(data, 'epsilon_k', epsilon_k)
        if epsilon_k is not None:
            self.data.epsilon_k = epsilon_k

        dat_attrs = ['delta_chi', 'r', 'chir_mag', 'chir_re', 'chir_im']
        if data is not None:
            dat_attrs.extend(dir(data))
        for attr in dat_attrs:
            if attr not in ('feffit_history',) and not hasattr(self.data, attr):
                setattr(self.data, attr, getattr(data, attr, None))
        self.hashkey = None
        self.bkg_spline = {}
        self._chi = None
        self._bkg = 0.0
        self._prepared = False


    def __generate_hashkey(self, other_hashkeys=None):
        """generate hash for dataset"""
        if self.hashkey is not None:
            return
        hlen = 7
        dat = []
        for aname in ('e0', 'ek0', 'rbkg', 'edge_step'):
            dat.append(getattr(self.data, aname, 0.00))

        for aname in ('energy', 'norm', 'chi'):
            arr = getattr(self.data, aname, None)
            if isinstance(arr, np.ndarray):
                dat.extend([arr.min(), arr.max(), arr.mean(),
                            (arr**2).mean(), len(arr)])
                dat.extend(arr[:30:3])
        s = "|".join([gformat(x) for x in dat])
        self.hashkey = f"d{(b32hash(s)[:hlen].lower())}"
        # may need to look for hash collisions: hlen=6 gives 1e9 keys
        # collision are probably the same dataset, so just go with a
        # random string
        if other_hashkeys is not None:
            ntry = 0
            while self.hashkey in other_hashkeys:
                ntry += 1
                if ntry > 1e6:
                    ntry = 0
                    hlen += 1
                self.hashkey = f"d{random_varname(hlen)}"

    def __repr__(self):
        return '<FeffitDataSet Group: %s>' % self.__name__

    def __copy__(self):
        return FeffitDataSet(data=copy(self.data),
                             paths=self.paths,
                             transform=self.transform,
                             refine_bkg=self.refine_bkg,
                             epsilon_k=self.data.epsilon_k,
                             model=self.model,
                             _larch=self._larch)

    def __deepcopy__(self, memo):
        return FeffitDataSet(data=deepcopy(self.data),
                             paths=self.paths,
                             transform=self.transform,
                             refine_bkg=self.refine_bkg,
                             epsilon_k=self.data.epsilon_k,
                             model=self.model,
                             _larch=self._larch)

    def prepare_fit(self, params, other_hashkeys=None):
        """prepare for fit with this dataset"""
        trans = self.transform
        trans.make_karrays()
        ikmax = int(1.01 + max(self.data.k)/trans.kstep)

        # ikmax = index_of(trans.k_, max(self.data.k))
        self.model.k = trans.k_[:ikmax]
        self.model.chi = np.zeros(len(self.model.k), dtype='float64')
        self._chi = interp(self.model.k, self.data.k, self.data.chi)
        self.n_idp = 1 + 2*(trans.rmax-trans.rmin)*(trans.kmax-trans.kmin)/pi

        if getattr(self.data, 'epsilon_k', None) is not None:
            eps_k = self.data.epsilon_k
            if isinstance(eps_k, np.ndarray):
                eps_k = interp(self.model.k, self.data.k, self.data.epsilon_k)
            self.set_epsilon_k(eps_k)
        else:
            self.estimate_noise(chi=self._chi, rmin=15.0, rmax=30.0)

            # if delta_chi (uncertainty in chi(k) from autobk or other source)
            # exists, add it in quadrature to high-k noise estimate, and
            # update epsilon_k to be this value
            autobk_delta_chi(self.data)
            if hasattr(self.data, 'delta_chi'):
                cur_eps_k = getattr(self, 'epsilon_k', 0.0)
                if isinstance(cur_eps_k, (list, tuple)):
                    eps_ave = 0.
                    for eps in cur_eps_k:
                        eps_ave += eps
                    cur_eps_k = eps_ave/len(cur_eps_k)

                _dchi = self.data.delta_chi
                if _dchi is not None:
                    if isinstance(_dchi, np.ndarray):
                        nchi = len(self.data.k)
                        if len(_dchi) != nchi:
                            _dchi = np.concatenate((_dchi, np.zeros(nchi)))[:nchi]
                        _dchi = interp(self.model.k, self.data.k, _dchi)
                    self.set_epsilon_k(np.sqrt(_dchi**2 + cur_eps_k**2))

        self.__generate_hashkey(other_hashkeys=other_hashkeys)
        # for each path in the list of paths, setup the Path Parameters
        # to use the current Parameters namespace
        if isinstance(params, Group):
            params = group2params(params)
        for label, path in self.paths.items():
            path.create_path_params(params=params, dataset=self.hashkey)
            if path.spline_coefs is None:
                path.create_spline_coefs()

        self.bkg_spline = {}
        if self.refine_bkg:
            trans.rbkg = max(trans.rbkg, trans.rmin)
            trans.rmin = trans.rstep
            self.n_idp = 1 + 2*(trans.rmax)*(trans.kmax-trans.kmin)/pi
            nspline = 1 + round(2*(trans.rbkg)*(trans.kmax-trans.kmin)/pi)
            knots_k = np.linspace(trans.kmin, trans.kmax, nspline)
            # np.linspace(trans.kmax, trans.kmax+trans.kstep/10.0, 3)))
            knots_y = np.linspace(-1e-4, 1.e-4, nspline)
            knots, coefs, order = splrep(knots_k, knots_y, k=3)
            self.bkg_spline = {'knots': knots, 'coefs': coefs,
                               'nspline': nspline, 'order':order}
            for i in range(nspline):
                params.add(f'bkg{i:02d}_{self.hashkey}', value=0, vary=True)
        self._prepared = True


    def estimate_noise(self, chi=None, rmin=15.0, rmax=30.0, all_kweights=True):
        """estimage noise in a chi spectrum from its high r components"""
        trans = self.transform
        trans.make_karrays()
        if chi is None:
            chi = self.data.chi

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
        eps_k = remove_nans(eps_k, 0.001)
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

        # check for nans
        self.epsilon_k = remove_nans(self.epsilon_k, eps_k, default=0.0001)
        self.epsilon_r = remove_nans(self.epsilon_r, eps_r, default=0.0001)



    def _residual(self, params, data_only=False, **kws):
        """return the residual for this data set
        residual = self.transform.apply(data_chi - model_chi)
        where model_chi is the result of ff2chi(paths)
        """
        if not isNamedClass(self.transform, TransformGroup):
            return
        if not self._prepared:
            self.prepare_fit(params)

        ff2chi(self.paths, params=params, k=self.model.k,
                _larch=self._larch, group=self.model)

        self._bkg = 0.0
        if self.refine_bkg:
            knots = self.bkg_spline['knots']
            order = self.bkg_spline['order']
            nspline = self.bkg_spline['nspline']
            coefs = []
            for i in range(nspline):
                parname = f'bkg{i:02d}_{self.hashkey}'
                par = params[parname]
                coefs.append(par.value)
            self._bkg = splev(self.model.k, [knots, coefs, order])

        eps_k = self.epsilon_k
        if isinstance(eps_k, np.ndarray):
            eps_k[np.where(eps_k<1.e-12)[0]] = 1.e-12

        diff  = self._chi - self._bkg
        if not data_only:  # data_only for extracting transformed data
            diff -= self.model.chi
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

    def save_outputs(self, rmax_out=10, path_outputs=True):
        "save fft outputs, and may also map a refined _bkg to the data chi(k) arrays"
        def xft(dgroup):
            self.transform._xafsft(dgroup.chi, group=dgroup, rmax_out=rmax_out)
        xft(self.data)
        xft(self.model)
        if self.refine_bkg:
            self.data.bkgk = IUSpline(self.model.k, self._bkg)(self.data.k)
            gname = getattr(self.data, 'groupname', repr(self.data))
            fname = getattr(self.data, 'filename', repr(self.data))
            label = f"defined background data for '{gname}'"
            self.data_rebkg = Group(__name__=label, groupname=gname,
                                    filename=fname, k=self.data.k[:],
                                    chi=self.data.chi-self.data.bkgk)
            xft(self.data_rebkg)

        if path_outputs:
            for path in self.paths.values():
                xft(path)

def feffit_dataset(data=None, paths=None, transform=None, refine_bkg=False,
                   epsilon_k=None, pathlist=None, _larch=None):
    """create a Feffit Dataset group.

     Parameters:
     ------------
      data:      group containing experimental EXAFS (needs arrays 'k' and 'chi').
      paths:     dict of {label: FeffPathGroup}, using FeffPathGroup created by feffpath()
      transform: Feffit Transform group.
      epsilon_k: Uncertainty in data (either single value or array of
                 same length as data.k)

     Returns:
     ----------
      a Feffit Dataset group.

    """
    return FeffitDataSet(data=data, paths=paths, transform=transform, epsilon_k=epsilon_k,
                         refine_bkg=refine_bkg, pathlist=pathlist, _larch=_larch)

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

def _feffit_resid(params, datasets=None, **kwargs):
    """ this is the residual function for feffit"""
    return concatenate([d._residual(params) for d in datasets])

def feffit(paramgroup, datasets, rmax_out=10, path_outputs=True,
           fix_unused_variables=True,  _larch=None, **kws):
    """execute a Feffit fit: a fit of feff paths to a list of datasets

    Parameters:
    ------------
      paramgroup:   group containing parameters for fit
      datasets:     Feffit Dataset group or list of Feffit Dataset group.
      rmax_out:     maximum R value to calculate output arrays.
      path_output:  Flag to set whether all Path outputs should be written.
      fix_unused_variables: Flag for whether to set `vary=False` for unused
                    variable parameters.  Otherwise, a warning will be printed.
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
    fit_kws = dict(gtol=1.e-6, ftol=1.e-6, xtol=1.e-6, epsfcn=1.e-10)
    if 'tol' in kws:
        tol = kws.pop('tol')
        fit_kws['gtol'] = fit_kws['ftol'] = fit_kws['xtol'] = tol

    fit_kws.update(kws)

    work_paramgroup = deepcopy(paramgroup)
    for pname in dir(paramgroup):  # explicitly copy 'skip'!
        wpar = getattr(work_paramgroup, pname)
        opar = getattr(paramgroup, pname)
        if isinstance(wpar, Parameter):
            setattr(wpar, 'skip', getattr(opar, 'skip', False))

    params = group2params(work_paramgroup)

    if isNamedClass(datasets, FeffitDataSet):
        datasets = [datasets]

    # we need unique dataset hashes if refine_bkg is used
    dset_hashkeys = []
    for ds in datasets:
        if not isNamedClass(ds, FeffitDataSet):
            print( "feffit needs a list of FeffitDataSets")
            return
        ds.prepare_fit(params=params, other_hashkeys=dset_hashkeys)
        dset_hashkeys.append(ds.hashkey)
    # try to identify variable Parameters that are not actually used
    vars, exprs = [], []
    for p in params.values():
        if p.vary:
            nam = p.name
            if not any([nam.startswith('bkg') and
                        nam.endswith(ds.hashkey) for ds in datasets]):
                vars.append(nam)
        elif p.expr is not None:
            exprs.append(p.expr)

    for expr in exprs:
         for node in ast.walk(ast.parse(expr)):
                if isinstance(node, ast.Name):
                    if node.id in vars:
                        vars.remove(node.id)
    if len(vars) > 0:
        if fix_unused_variables:
            for v in vars:
                params[v].vary = False
        else:
            vlist = ', '.join(vars)
            print(f"Feffit Warning: unused variables: {vlist}")

    # run fit
    fit = Minimizer(_feffit_resid, params, fcn_kws=dict(datasets=datasets),
                    scale_covar=False, **fit_kws)

    result = fit.leastsq()
    dat = concatenate([d._residual(result.params, data_only=True)
                       for d in datasets])

    n_idp = 0
    for ds in datasets:
        n_idp += ds.n_idp

    # here we rescale chi-square and reduced chi-square to n_idp
    npts =  len(result.residual)
    chi_square  = result.chisqr * n_idp*1.0 / npts
    chi2_reduced = chi_square/(n_idp*1.0 - result.nvarys)
    rfactor = (result.residual**2).sum() / (dat**2).sum()
    # calculate 'aic', 'bic' rescaled to n_idp
    # note that neg2_loglikel is -2*log(likelihood)
    neg2_loglikel = n_idp * np.log(chi_square / n_idp)
    aic = neg2_loglikel + 2 * result.nvarys
    bic = neg2_loglikel + np.log(n_idp) * result.nvarys

    # We used scale_covar=False, so we rescale the uncertainties
    # by reduced chi-square * (ndata - nvarys)/(nidp - nvarys)
    covar = getattr(result, 'covar', None)
    if covar is not None:
        err_scale = result.redchi*(result.nfree/(n_idp - result.nvarys))
        for name, par in result.params.items():
            if isParameter(par) and getattr(par, 'stderr', None) is not None:
                par.stderr *= sqrt(err_scale)

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

        # 3. evaluate path_ params, save stderr
        for ds in datasets:
            for label, path in ds.paths.items():
                path.store_feffdat()
                for pname in ('degen', 's02', 'e0', 'ei',
                              'deltar', 'sigma2', 'third', 'fourth'):
                    obj = path.params[path.pathpar_name(pname)]
                    eval_stderr(obj, uvars,  result.var_names, result.params)
        # restore saved parameters again
        for vname in result.var_names:
            # setattr(params, vname, vsave[vname])
            params[vname] = vsave[vname]

        # clear any errors evaluting uncertainties
        if _larch is not None and (len(_larch.error) > 0):
            _larch.error = []

    # reset the parameters group with the newly updated uncertainties
    params2group(result.params, work_paramgroup)

    # here we create outputs arrays for chi(k), chi(r):
    for ds in datasets:
        ds.save_outputs(rmax_out=rmax_out, path_outputs=path_outputs)

    out = Group(name='feffit results', params=result.params,
                paramgroup=work_paramgroup, fit_kws=fit_kws, datasets=datasets,
                fit_details=result, chi_square=chi_square, n_independent=n_idp,
                chi2_reduced=chi2_reduced, rfactor=rfactor, aic=aic, bic=bic,
                covar=covar)

    for attr in ('params', 'nvarys', 'nfree', 'ndata', 'var_names', 'nfev',
                 'success', 'errorbars', 'message', 'lmdif_message'):
        setattr(out, attr, getattr(result, attr, None))
    return out

def feffit_conf_map(result, xpar, ypar, nsamples=41, nsigma=3.5):
    """
    return 2d map of confidence interval (sigma values) for a pair of variables from feffit

    """
    def show_progress(i, imax):
        if i > (imax-1):
            print('done.')
        elif i % round(imax//10) == 0:
            print(f"{i}/{imax}", flush=True, end=', ')

    fitter = Minimizer(_feffit_resid, result.params,
                       fcn_kws=dict(datasets=result.datasets),
                       scale_covar=False, **result.fit_kws)

    xvals, yvals, chi2_map = conf_interval2d(fitter, result.fit_details, xpar, ypar,
                                             nsamples, nsamples, nsigma=nsigma, chi2_out=True)

    chi2_map = chi2_map * result.n_independent / result.fit_details.ndata
    chisqr0 = min(result.chi_square, chi2_map.min())
    sigma_map = np.sqrt((chi2_map-chisqr0)/result.chi2_reduced)
    return xvals, yvals, sigma_map



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

    path_hashkeys = []
    for ds in datasets:
        path_hashkeys.extend([p.hashkey for p in ds.paths.values()])
    topline = '=================== FEFFIT RESULTS ===================='
    header = '[[%s]]'
    varformat  = '   %12s = %s +/-%s   (init= %s)'
    fixformat  = '   %12s = %s (fixed)'
    exprformat = '   %12s = %s +/-%s  = \'%s\''
    out = [topline, header % 'Statistics']

    def getval(attr):
        return getfloat_attr(result, attr)

    def add_string(label, value, llen=20):
        if len(label) < llen:
            label = (label + ' '*llen)[:llen]
        out.append(f"  {label} = {value}")

    add_string('n_function_calls', getval('nfev'))
    add_string('n_variables', getval('nvarys'))
    add_string('n_data_points', getval('ndata'))
    add_string('n_independent', getval('n_independent'))
    add_string('chi_square', getval('chi_square'))
    add_string('reduced chi_square', getval('chi2_reduced'))
    add_string('r-factor',  getval('rfactor'))
    add_string('Akaike info crit', getval('aic'))
    add_string('Bayesian info crit', getval('bic'))

    out.append(' ')
    out.append(header % 'Variables')
    for name, par in params.items():
        if any([name.endswith('_%s' % phash) for phash in path_hashkeys]):
            continue
        if isParameter(par):
            if par.vary:
                stderr = 'unknown'
                if par.stderr is not None:
                    stderr = gfmt(par.stderr)
                add_string(name, f"{gfmt(par.value)} +/-{stderr}  (init={gfmt(par.init_value)})")

            elif par.expr is not None:
                stderr = 'unknown'
                if par.stderr is not None:
                    stderr = gfmt(par.stderr)
                add_string(name, f"{gfmt(par.value)} +/-{stderr}  = '{par.expr}'")
            else:
                add_string(name, f"{gfmt(par.value)} (fixed)")

    covar_vars = result.var_names
    if len(covar_vars) > 0:
        out.append(' ')
        out.append(header % 'Correlations' +
                   ' (unreported correlations are < % .3f)' % min_correl)
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
            if abs(val) > min_correl:
                vv = f"{val:+.3f}".replace('+', ' ')
                add_string(name, vv)

    out.append(' ')
    for i, ds in enumerate(datasets):
        if not hasattr(ds, 'epsilon_k'):
            ds.prepare_fit(params)
        tr = ds.transform
        if isinstance(tr.kweight, Iterable):
            if isinstance(ds.epsilon_k[0], np.ndarray):
                msg = []
                for eps in ds.epsilon_k:
                    msg.append('Array(mean=%s, std=%s)' % (gfmt(eps.mean()).strip(),
                                                           gfmt(eps.std()).strip()))
                eps_k = ', '.join(msg)
            else:
                eps_k = ', '.join([gfmt(eps).strip() for eps in ds.epsilon_k])
            eps_r = ', '.join([gfmt(eps).strip() for eps in ds.epsilon_r])
            kweigh = ', '.join(['%i' % kwe for kwe in tr.kweight])
            eps_k = eps_k.strip()
            eps_r = eps_r.strip()
            kweigh = kweigh.strip()
        else:
            if isinstance(ds.epsilon_k, np.ndarray):
                eps_k = 'Array(mean=%s, std=%s)' % (gfmt(ds.epsilon_k.mean()).strip(),
                                                    gfmt(ds.epsilon_k.std()).strip())
            else:
                eps_k = gfmt(ds.epsilon_k).strip()
            eps_r = gfmt(ds.epsilon_r).strip()
            kweigh = '%i' % tr.kweight
        extra = f" {i+1} of {len(datasets)}" if len(datasets) > 1 else ""

        out.append(f"[[Dataset{extra}]]")
        add_string('unique_id', f"'{ds.hashkey}'")
        add_string('fit space', f"'{tr.fitspace}'")
        if ds.refine_bkg:
            add_string('r_bkg (refine bkg)', f"{tr.rbkg:.3f}")
        add_string('r-range', f"{tr.rmin:.3f}, {tr.rmax:.3f}")
        add_string('k-range', f"{tr.kmin:.3f}, {tr.kmax:.3f}")
        kwin = f"'{tr.window}', {tr.dk:.3f}"
        if tr.dk2 is not None:
            kwin += f", {tr.dk2:.3f}"
        add_string('k window, dk', kwin)
        pathfiles = repr([p.filename for p in ds.paths.values()])
        add_string('paths used in fit', pathfiles)
        add_string('k-weight', kweigh)
        add_string('epsilon_k', eps_k)
        add_string('epsilon_r', eps_r)
        add_string('n_independent', f"{ds.n_idp:.3f}")
        #

        if with_paths:
            out.append(' ')
            out.append(header % 'Paths')
            for label, path in ds.paths.items():
                out.append('%s\n' % path.report())
    out.append('='*len(topline))
    return '\n'.join(out)
