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
from xafsft import xftf_fast, xftr_fast, ftwindow

from feffdat import FeffPathGroup, _ff2chi

# check for uncertainties package
HAS_UNCERTAIN = False
try:
    from uncertainties import ufloat, correlated_values
    HAS_UNCERTAIN = True
except ImportError:
    pass


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
        # self.xafsft = self._xafsft
        # self.estimate_noise = self._estimate_noise
        self.make_karrays()

    def __repr__(self):
        return '<FeffitTransform Group: %s>' % self.__name__

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
        """estimage noise in a chi spectrum from its high r components"""
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
        kwin_ave = self.kwin.sum()*self.kstep/(self.kmax-self.kmin)
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
        return xftf_fast(cx, kstep=self.kstep, nfft=self.nfft)

    def fftr(self, chir):
        " reverse FT -- meant to be used internally"
        self.make_karrays()
        if self.rwin is None:
            self.rwin = ftwindow(self.r_, xmin=self.rmin, xmax=self.rmax,
                                 dx=self.dr, dx2=self.dr2, window=self.rwindow)

        cx = chir * self.rwin[:len(chir)] * self.r_[:len(chir)]**self.rw,
        return xftr_fast(cx, kstep=self.kstep, nfft=self.nfft)

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
                chiq = [self.fftr(self.r_, c) for c in chir]
                iqmin = int(0.01 + self.kmin/self.kstep)
                iqmax = min(self.nfft/2,  int(1.01 + self.kmax/self.kstep))
                for chiq_ in chiq:
                    out.append( realimag(chiq[iqmin:iqmax]))
            return np.concatenate(out)

class FeffitDataSet(Group):
    def __init__(self, data=None, pathlist=None, transform=None, _larch=None, **kws):

        self._larch = _larch
        Group.__init__(self, **kws)

        self.pathlist = pathlist

        self.data = data
        if transform is None:
            transform = TransformGroup()
        self.transform = transform
        self.model = Group()
        self.model.k = None
        self.__chi = None
        self.__prepared = False

    def __repr__(self):
        return '<FeffitDataSet Group: %s>' % self.__name__

    def prepare_fit(self):
        trans = self.transform

        trans.make_karrays()
        ikmax = int(1.01 + max(self.data.k)/trans.kstep)
        # ikmax = index_of(trans.k_, max(self.data.k))
        self.model.k = trans.k_[:ikmax]
        self.__chi = interp(self.model.k, self.data.k, self.data.chi)
        # print 'feffit dataset prepare_fit ', dir(self.data)
        if hasattr(self.data, 'epsilon_k'):
            eps_k = self.data.epsilon_k
            if isinstance(self.eps_k, numpy.ndarray):
                eps_k = interp(self.model.k, self.data.k, self.data.epsilon_k)
                trans.set_epsilon_k(eps_k)
        else:
            trans._estimate_noise(self.__chi, rmin=15.0, rmax=25.0)

        self.__prepared = True

    def estimate_noise(self, rmin=15, rmax=25):
        self.prepare_fit()
        if rmin != 15 and rmax != 25:
            self.transform._estimate_noise(self.__chi, rmin=rmax, rmax=max)
        return self.transform.epsilon_k

    def _residual(self, paramgroup=None):
        """return the residual for this data set
        residual = self.transform.apply(data_chi - model_chi)
        where model_chi is the result of ff2chi(pathlist)
        """
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
        return self.transform.apply(self.__chi-self.model.chi, eps_scale=True)

    def save_ffts(self, rmax_out=10, path_outputs=True):
        "save fft outputs"
        xft = self.transform._xafsft
        xft(self.__chi,   group=self.data,  rmax_out=rmax_out)
        xft(self.model.chi, group=self.model, rmax_out=rmax_out)
        if path_outputs:
            for p in self.pathlist:
                xft(p.chi, group=p, rmax_out=rmax_out)

def feffit_dataset(data=None, pathlist=None, transform=None, _larch=None):
    """create a Feffit Dataset group.

     Parameters:
     ------------
      data:     group containing experimental EXAFS (needs arrays 'k' and 'chi').
      pathlis:  list of FeffPath groups, as created from feffpath()
      transform: Feffit Transform group.

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

def feffit(params, datasets, _larch=None, rmax_out=10, path_outputs=True, **kws):
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
    def _resid(params, datasets=None, _larch=None, **kws):
        """ this is the residual function """
        return concatenate([d._residual() for d in datasets])

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

    # remove temporary parameters for _feffdat and reff
    # that had been placed by _pathparams()
    #for pname in ('_feffdat', 'reff'):
    #    if hasattr(params, pname):
    #        delattr(params, pname)

    # scale uncertainties to sqrt(reduce chi-square)
    n_idp = 0
    for ds in datasets:
        n_idp += ds.transform.n_idp
    err_scale = sqrt(params.chi_reduced)
    for name in dir(params):
        p = getattr(params, name)
        if isParameter(p) and p.vary:
            p.stderr *= err_scale
    # next, propagate uncertainties to constraints and path parameters.
    covar = getattr(params, 'covar', None)
    if HAS_UNCERTAIN and covar is not None:
        vsave, vbest = {}, []
        # 1. save current params
        for vname in params.covar_vars:
            par = getattr(params, vname)
            vsave[vname] = par
            vbest.append(par.value)

        # 2. get correlated uncertainties, set params accordingly
        uvars = correlated_values(vbest, params.covar)
        for val, nam in zip(uvars, params.covar_vars):
            setattr(params, nam, ufloat((val.nominal_value,
                                         err_scale * val.std_dev())))
        # 3. evaluate constrained params, save stderr
        for nam, par in params.__dict__.items():
            if isParameter(par) and par._ast is not None:
                par.stderr = 0
                try:
                    tmp = par._getval()
                    par.stderr = tmp.std_dev()
                except:
                    print 'error with derived uncertainty ', par, par.name, par._ast
                    pass
        # 3. evaluate path params, save stderr
        for ds in datasets:
            for p in ds.pathlist:
                _larch.symtable._sys.paramGroup._feffdat = p._feffdat
                _larch.symtable._sys.paramGroup.reff = p._feffdat.reff

                for param in ('degen', 's02', 'e0', 'ei',
                              'deltar', 'sigma2', 'third', 'fourth'):
                    obj = getattr(p, param)
                    stderr  = 0
                    if isParameter(obj):
                        if hasattr(obj.value, 'std_dev'):
                            stderr = obj.value.std_dev()
                        setattr(obj, 'stderr', stderr)


        # 4. restore saved parameters
        for vname in params.covar_vars:
            setattr(params, vname, vsave[vname])

        # clear any errors evaluting uncertainties
        if len(_larch.error) > 0:
            _larch.error = []

    # here we create outputs arrays for chi(k), chi(r):
    for ds in datasets:
        ds.save_ffts(rmax_out=rmax_out, path_outputs=path_outputs)
    return Group(name='feffit fit results', fit=fit, params=params,
                 datasets=datasets)

def feffit_report(result, min_correl=0.1, with_paths=True,
                  _larch=None, **kws):
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
        fit    = result.fit
        params = result.params
        datasets = result.datasets
        input_ok = True
    except:
        pass
    if not input_ok:
        print 'must pass output of feffit()!'
        return
    topline = '=================== FEFFIT RESULTS ===================='
    header = '[[%s]]'
    varformat  = '   %12s = % f +/- %f   (init= % f)'
    exprformat = '   %12s = % f +/- %f  = \'%s\''
    out = [topline, header % 'Statistics']

    npts = len(params.residual)

    out.append('   npts, nvarys       = %i, %i' % (npts, params.nvarys))
    out.append('   nfree, nfcn_calls  = %i, %i' % (params.nfree,
                                                   params.fit_details.nfev))
    out.append('   chi_square         = %f'     % (params.chi_square))
    out.append('   reduced chi_square = %f'     % (params.chi_reduced))
    out.append(' ')
    if len(datasets) == 1:
        out.append(header % 'Data')
    else:
        out.append(header % 'Datasets (%i)' % len(datasets))
    for i, ds in enumerate(datasets):
        tr = ds.transform
        if len(datasets) > 1:
            out.append(' dataset %i:' % (i+1))
        out.append('   n_independent      = %.3f '  % (tr.n_idp))
        out.append('   eps_k, eps_r       = %f, %f' % (tr.epsilon_k,
                                                       tr.epsilon_r))
        out.append('   fit space          = %s  '   % (tr.fitspace))
        out.append('   r-range            = %.3f, %.3f' % (tr.rmin, tr.rmax))
        out.append('   k-range            = %.3f, %.3f' % (tr.kmin, tr.kmax))
        kwin = '   k window, dk       = %s, %.3f'   % (tr.window, tr.dk)
        if tr.dk2 is not None:
            kwin = "%s, %.3f" % (kwin, tr.dk2)
        out.append(kwin)
        out.append('   k-weight           = %s' % (repr(tr.kweight)))
        pathfiles = [p.filename for p in ds.pathlist]
        out.append('   paths used in fit  = %s' % (repr(pathfiles)))
    #
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
                exprs.append(exprformat % (name, var.value,
                                           var.stderr, var.expr))
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


