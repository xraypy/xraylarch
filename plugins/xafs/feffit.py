#!/usr/bin/env python
"""
   feffit sums Feff paths to match xafs data
"""

import sys, os
from collections import Iterable
import numpy as np
from numpy import array, arange, interp, pi, zeros, sqrt, concatenate

from scipy.optimize import leastsq as scipy_leastsq

from larch import Group, Parameter, isParameter, Minimizer, plugin_path

sys.path.insert(0, plugin_path('std'))
sys.path.insert(0, plugin_path('xafs'))
## sys.path.insert(0, plugin_path('fitter'))

from mathutils import index_of, realimag, complex_phase

# from minimizer import Minimizer
from xafsft import xafsft, xafsift, xafsft_fast, xafsift_fast, ftwindow

from feffdat import FeffPathGroup, _ff2chi

class TransformGroup(Group):
    """A Group of transform parameters.
    The apply() method will return the result of applying the transform,
    ready to use in a Fit.   This caches the FT windows (k and r windows)
    and assumes that once created (not None), these do not need to be
    recalculated....

    That is: don't change the parameters are expect the different things.
    If you do change parameters, reset kwin / rwin to None.

    """
    def __init__(self, kmin=0, kmax=20, kweight=2, dk=4, dk2=None,
                 window='bessel', nfft=2048, kstep=0.05,
                 rmin = 0, rmax=10, dr=0, rwindow='kaiser',
                 fitspace='r', _larch=None, **kws):
        Group.__init__(self)
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
        self.xafsft = self._xafsft
        self.estimate_noise = self._estimate_noise
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

    def _estimate_noise(self, chi, rmin=15.0, rmax=25.0, all_kweights=True):
        """estimage noice from high r"""
        # print 'Estimate Noise!! ', rmin, self.transform.rmin
        self.make_karrays()

        save = self.rmin, self.rmax, self.fitspace

        all_kweights = all_kweights and isinstance(self.kweight, Iterable)
        if all_kweights:
            chir = [self.fftf(chi, kweight=kw) for kw in self.kweight]
        else:
            chir = [self.fftf(chi)]
        irmin = int(0.01 + rmin/self.rstep)
        irmax = min(self.nfft/2,  int(1.01 + rmax/self.rstep))
        highr = [realimag(chir_[irmin:irmax]) for chir_ in chir]
        # get average of window function value, we will scale eps_r scale by this
        ikmin = index_of(self.k_, self.kmin)
        ikmax = index_of(self.k_, self.kmax)
        kwin_ave = self.kwin[ikmin:ikmax].sum()/(ikmax-ikmin)

        eps_r = [(sqrt((chi*chi).sum() / len(chi)) / kwin_ave) for chi in highr]
        eps_k = []
        # use Parseval's theorem to convert epsilon_r to epsilon_k,
        # compensating for kweight
        if all_kweights:
            kweights = self.kweight[:]
        else:
            kweights = [self.kweight]
        for i, kw in enumerate(kweights):
            w = 2 * kw + 1
            scale = sqrt((2*pi*w)/(self.kstep*(self.kmax**w - self.kmin**w)))
            eps_k.append(scale*eps_r[i])


        self.rmin, self.rmax, self.fitspace = save

        self.n_idp  = 2*(self.rmax-self.rmin)*(self.kmax-self.kmin)/pi
        self.epsilon_k = eps_k
        self.epsilon_r = eps_r
        if len(eps_r) == 1:
            self.epsilon_k = eps_k[0]
            self.epsilon_r = eps_r[0]

    def set_epsilon_k(self, eps_k):
        """set epsilon_k and epsilon_r -- ucertainties in chi(k) and chi(R)"""
        w = 2 * self.get_kweight() + 1
        scale = 2*sqrt((pi*w)/(self.kstep*(self.kmax**w - self.kmin**w)))
        eps_r = eps_k / scale
        self.epsilon_k = eps_k
        self.epsilon_r = eps_r

    def _xafsft(self, chi, group=None, rmax_out=10, **kws):
        "returns "
        for key, val in kws:
            if key == 'kw':
                key = 'kweight'
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
            group.chir_pha =  complex_phase(out[:irmax])
            group.chir_re  =  out.real[:irmax]
            group.chir_im  =  out.imag[:irmax]
        else:
            return out[:irmax]

    def get_kweight(self):
        "if kweight is a list/tuple, use only the first one here"
        if isinstance(self.kweight, Iterable):
            return self.kweight[0]
        return self.kweight

    def fftf(self, chi, kweight=None):
        """ forward FT -- meant to be used internally.
        chi must be on self.k_ grid"""
        self.make_karrays()
        if self.kwin is None:
            self.kwin = ftwindow(self.k_, xmin=self.kmin, xmax=self.kmax,
                                 dx=self.dk, dx2=self.dk2, window=self.window)
        if kweight is None:
            kweight = self.get_kweight()
        cx = chi * self.kwin[:len(chi)] * self.k_[:len(chi)]**kweight
        return xafsft_fast(cx, kstep=self.kstep, nfft=self.nfft)

    def ffti(self, chir):
        " reverse FT -- meant to be used internally"
        self.make_karrays()
        if self.rwin is None:
            self.rwin = ftwindow(self.r_, xmin=self.rmin, xmax=self.rmax,
                                 dx=self.dr, dx2=self.dr2, window=self.rwindow)

        cx = chir * self.rwin[:len(chir)] * self.r_[:len(chir)]**self.rw,
        return xafsift_fast(cx, kstep=self.kstep, nfft=self.nfft)

    def apply(self, chi, eps_scale=False, all_kweights=True, **kws):
        """apply transform, returns real/imag components
        eps_scale: scale by appropriaat epsilon_k or epsilon_r
        """
        # print 'this  is transform apply ', len(chi), chi[5:10], kws
        for key, val in kws.items():
            if key == 'kw': key = 'kweight'
            setattr(self, key, val)

        all_kweights = all_kweights and isinstance(self.kweight, Iterable)
        # print 'fit space = ', self.fitspace
        if self.fitspace == 'k':
            if all_kweights:
                return np.concatenate([chi * self.k_[:len(chi)]**kw for kw in self.kweight])
            else:
                return chi * self.k_[:len(chi)]**self.kweight
        elif self.fitspace in ('r', 'q'):
            self.make_karrays()
            out = []
            if all_kweights:
                # print 'Apply -- use all kweights ', self.kweight
                chir = [self.fftf(chi, kweight=kw) for kw in self.kweight]
                eps_r = self.epsilon_r
            else:
                chir = [self.fftf(chi)]
                eps_r = [self.epsilon_r]
            if self.fitspace == 'r':
                irmin = int(0.01 + self.rmin/self.rstep)
                irmax = min(self.nfft/2,  int(1.01 + self.rmax/self.rstep))
                for i, chir_ in enumerate(chir):
                    if eps_scale:
                        chir_ = chir_ /(eps_r[i])
                    out.append( realimag(chir_[irmin:irmax]))
            else:
                chiq = [self.ffti(self.r_, c) for c in chir]
                iqmin = int(0.01 + self.kmin/self.kstep)
                iqmax = min(self.nfft/2,  int(1.01 + self.kmax/self.kstep))
                for chiq_ in chiq:
                    out.append( realimag(chiq[iqmin:iqmax]))
            return np.concatenate(out)

class FeffitDataSet(Group):
    def __init__(self, data=None, pathlist=None, transform=None, _larch=None, **kws):

        self._larch = _larch
        Group.__init__(self,  residual=self.residual, **kws)

        self.pathlist = pathlist

        self.data = data
        if transform is None:
            transform = TransformGroup()
        self.transform = transform
        self.model = Group()
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
        # print 'feffit dataset prepare_fit ', dir(self.data)
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

        _ff2chi(self.pathlist, k=self.model.k,
                _larch=self._larch, group=self.model)
        return self.transform.apply(self.datachi-self.model.chi, eps_scale=True)

    def save_ffts(self, rmax_out=10, path_outputs=True):
        "save fft outputs"
        xft = self.transform.xafsft
        xft(self.datachi,   group=self.data,  rmax_out=rmax_out)
        xft(self.model.chi, group=self.model, rmax_out=rmax_out)
        if path_outputs:
            for p in self.pathlist:
                xft(p.chi, group=p, rmax_out=rmax_out)


def feffit_dataset(data=None, pathlist=None, transform=None, _larch=None):
    return FeffitDataSet(data=data, pathlist=pathlist,
                         transform=transform, _larch=_larch)

def feffit_transform(_larch=None, **kws):
    return TransformGroup(_larch=_larch, **kws)

def feffit(params, datasets, _larch=None, rmax_out=10, path_outputs=True, **kws):
    """run feff-fit"""
    def _resid(params, datasets=None, _larch=None, **kws):
        """ this is the residual function """
        return concatenate([d.residual() for d in datasets])
        #         s = ' : '
        #         for i in dir(params):
        #             obj = getattr(params, i)
        #             if isParameter(obj):
        #                 s = s + '  %.6f' % obj.value
        #         print '---feffit residual ', datasets, s

    if isinstance(datasets, FeffitDataSet):
        datasets = [datasets]
    for ds in datasets:
        if not isinstance(ds, FeffitDataSet):
            print "feffit needs a list of FeffitDataSets"
            return
    fitkws = dict(datasets=datasets)
    fit = Minimizer(_resid, params, fcn_kws=fitkws,
                    scale_covar=True,  _larch=_larch)
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
        ds.save_ffts(rmax_out=rmax_out, path_outputs=path_outputs)

    return Group(name='feffit fit results',
                 fit = fit,
                 params = params,
                 datasets = datasets)

def feffit_report(result, min_correl=0.1, with_paths=True,
                  _larch=None, **kws):
    """print report of fit for feffit"""
    good_to_go = False
    try:
        fit    = result.fit
        params = result.params
        datasets = result.datasets
        good_to_go = True
    except:
        pass
    if not good_to_go:
        print 'must pass output of feffit()!'
        return
    topline = '=================== FEFFIT RESULTS ===================='
    header = '[[%s]]'
    varformat = '   %12s = % f +/- %f   (init= % f)'
    exprformat = '   %12s = % f   = \'%s\''
    out = [topline, header % 'Statistics']
    #     print 'Params ', dir(params)
    #     print 'Fit    ', dir(fit)
    #     for ds in datasets:
    #         print dir(ds)
    #         print dir(ds.transform)

    npts = len(params.residual)

    out.append('   npts, nvarys       = %i, %i' % (npts, params.nvarys))
    out.append('   nfree, nfcn_calls  = %i, %i' % (params.nfree, params.nfcn_calls))
    out.append('   chi_square         = %f' % (params.chi_square))
    out.append('   reduced chi_square = %f' % (params.chi_reduced))
    out.append(' ')
    if len(datasets) == 1:
        out.append(header % 'Data')
    else:
        out.append(header % 'Datasets (%i)' % len(datasets))
    for i, ds in enumerate(datasets):
        trans = ds.transform
        if len(datasets) > 1:
            out.append(' dataset %i:' % (i+1))
        out.append('   n_independent      = %.3f ' % (trans.n_idp))
        out.append('   eps_k, eps_r       = %f, %f' % (ds.transform.epsilon_k, ds.transform.epsilon_r))
        out.append('   fit space          = %s  ' % (trans.fitspace))
        out.append('   r-range            = %.3f, %.3f' % (trans.rmin, trans.rmax))
        out.append('   k-range            = %.3f, %.3f' % (trans.kmin, trans.kmax))
        kwin = '   k window, dk       = %s, %.3f' % (trans.window, trans.dk)
        if trans.dk2 is not None:
            kwin = "%s, %.3f" % (kwin, trans.dk2)
        out.append(kwin)
        out.append('   k-weight           = %s' % (repr(trans.kweight)))
        out.append('   paths used in fit  = %s' % (repr([p.filename for p in ds.pathlist])))


    out.append(' ')
    out.append(header % 'Variables')

    exprs = []
    for name in dir(params):
        var = getattr(params, name)
        if len(name) < 14:
            name = (name + ' '*14)[:14]
        if isParameter(var):
            if var.vary:
                out.append(varformat % (name, var.value,
                                        var.stderr, var._initval))

            elif var.expr is not None:
                exprs.append(exprformat % (name, var.value, var.expr))
    if len(exprs) > 0:
        out.append(header % 'Constraint Expressions')
        out.extend(exprs)

    covar_vars = getattr(params, 'covar_vars', [])
    if len(covar_vars) > 0:
        out.append(' ')
        out.append(header % 'Correlations' +
                   '    (unreported correlations are < % .3f)' % min_correl)
        correls = {}
        for i, name in enumerate(covar_vars):
            par = getattr(params, name)
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
            out.append('   %s = % .3f ' % (name, val))

    if with_paths:
        out.append(' ')
        out.append(header % 'Paths')
        for ds in datasets:
            for p in ds.pathlist:
                out.append('%s\n' % p.report())

    out.append('='*len(topline))
    return '\n'.join(out)

def registerLarchPlugin():
    return ('_xafs', {'feffit': feffit,
                      'feffit_dataset': feffit_dataset,
                      'feffit_transform': feffit_transform,
                      'feffit_report': feffit_report})


