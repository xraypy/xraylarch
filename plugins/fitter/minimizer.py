"""
minimizer for Larch, similar to lmfit-py.

Minimizer is a wrapper around scipy.leastsq, allowing a user to build
a fitting model as a function of general purpose fit parameters which
can be fixed or floated, bounded, or written as larch expressions.

The user sets up a model with a Group which contains all the fitting
parameters, and writes a larch procedure to calculate the residual to
be minimized in terms of the parameters of this Group.

The procedure to calculate the residual will take the parameter Group
as the first argument, and can take additional optional arguments.
    params = Group()
    params.slope  = Param(0, vary=True, min=0)
    params.offset = Param(10, vary=True)

    def residual(pgroup, xdata=None, ydata=None):
        line = pgroup.offset + xdata * pgroup.slope
        pgroup.this_line = line
        return (ydata - line)
    end def

    minimize(residual, params, kws={'xdata': x, 'ydata': y})

After this, each of the parameters in the params group will contain
best fit values, uncertainties and correlations, and the params group
will contain fit statistics chisquare, etc.
"""

from numpy import sqrt
from scipy.optimize import leastsq as scipy_leastsq
import re
from larch.utils import OrderedDict
from larch.larchlib import Parameter, isParameter
from larch.symboltable import isgroup

class MinimizerException(Exception):
    """General Purpose Exception"""
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return "\n%s" % (self.msg)

class Minimizer(object):
    """general minimizer"""
    err_nonparam = "params must be a minimizer.Parameters() instance or list of Parameters()"
    err_maxfev   = """Too many function calls (max set to  %i)!  Use:
    minimize(func, params, ...., maxfev=NNN)
or set  leastsq_kws['maxfev']  to increase this maximum."""

    def __init__(self, fcn, params, fcn_args=None, fcn_kws=None,
                 iter_cb=None, scale_covar=True, toler=1.e-7,
                 _larch=None, jacfcn=None, **kws):
        self.userfcn = fcn
        self.paramgroup = params
        self.userargs = fcn_args
        if self.userargs is None:
            self.userargs = []

        self.userkws = fcn_kws
        if self.userkws is None:
            self.userkws = {}
        self._larch = _larch
        self.iter_cb = iter_cb
        self.toler = toler
        self.scale_covar = scale_covar
        self.kws = kws

        self.nfev_calls = 0
        self.jacfcn = jacfcn
        self.__prepared = False

    def __update_params(self, fvars):
        """
        set parameter values from values of fitted variables
        """
        if not self.__prepared:
            print 'fit not prepared!'
        group = self.paramgroup
        for name, val in zip(self.var_names, fvars):
            par = getattr(group, name)
            if par.min is not None:   val = max(val, par.min)
            if par.max is not None:   val = min(val, par.max)
            par.value = val

    def __residual(self, fvars):
        """
        residual function used for least-squares fit.
        With the new, candidate values of fvars (the fitting variables),
        this evaluates all parameters, including setting bounds and
        evaluating constraints, and then passes those to the
        user-supplied function to calculate the residual.
        """
        self.nfev_calls = self.nfev_calls + 1
        self.__update_params(fvars)

        out = self.userfcn(self.paramgroup, *self.userargs, **self.userkws)
        if hasattr(self.iter_cb, '__call__'):
            self.iter_cb(self.params, self.nfev_calls, out,
                         *self.userargs, **self.userkws)
        return out

    def __jacobian(self, fvars):
        """
        analytical jacobian to be used with the Levenberg-Marquardt
        """
        # computing the jacobian
        self.__update_params(fvars)
        return self.jacfcn(self.paramgroup, *self.userargs, **self.userkws)


    def prepare_fit(self):
        """prepare parameters for fit
        determine which parameters are actually variables
        and which are defined expressions.
        """

        if self.__prepared:
            return
        #if self.paramgroup.__name__ is None:
        #    self.paramgroup.__name__ = '_fit_params_%s' % id(self)
        #symtable = self._larch.symtable
        #symtable._sys.searchGroups.insert(0, self.paramgroup.__name__)
        #if not symtable.isgroup(self.paramgroup):#
        #    print 'param group is not a Larch Group'
        #    return
        
        self.nfev_calls = 0
        self.var_names = []
        self.defvars = []
        self.vars = []
        self.nvarys = 0
        for name in dir(self.paramgroup):
            par = getattr(self.paramgroup, name)
            if isParameter(par):
                if par.expr is not None:
                    par._getval()
                elif par.vary:
                    self.var_names.append(name)
                    self.vars.append(par.value)
                if not hasattr(par, 'name') or par.name is None:
                   par.name = name
        self.nvarys = len(self.vars)
        # now evaluate make sure initial values are set
        # are used to set values of the defined expressions.
        # this also acts as a check of expression syntax.
        self.__prepared = True

    def leastsq(self, **kws):
        """
        use Levenberg-Marquardt minimization to perform fit.
        This assumes that ModelParameters have been stored,
        and a function to minimize has been properly set up.

        This wraps scipy.optimize.leastsq, and keyward arguments are passed
        directly as options to scipy.optimize.leastsq

        When possible, this calculates the estimated uncertainties and
        variable correlations from the covariance matrix.

        writes outputs to many internal attributes, and
        returns True if fit was successful, False if not.
        """
        self.prepare_fit()
        toler = self.toler
        lskws = dict(full_output=1, xtol=toler, ftol=toler,
                     gtol=toler, maxfev=1000*(self.nvarys+1), Dfun=None)

        lskws.update(self.kws)
        lskws.update(kws)

        if lskws['Dfun'] is not None:
            self.jacfcn = lskws['Dfun']
            lskws['Dfun'] = self.__jacobian

        lsout = scipy_leastsq(self.__residual, self.vars, **lskws)
        vbest, cov, infodict, errmsg, ier = lsout
        resid = infodict['fvec']
        group = self.paramgroup

        #symtable = self._larch.symtable
        #if self.paramgroup.__name__ in symtable._sys.searchGroups:
        #    symtable._sys.searchGroups.remove(self.paramgroup.__name__)
            
        message = 'Fit succeeded.'
        if ier == 0:
            message = 'Invalid Input Parameters.'
        elif ier == 5:
            message = self.err_maxfev % lskws['maxfev']
        elif ier > 5:
            message = 'See lmdif_message.'
        if cov is None:
            message = '%s Could not estimate error-bars' % message

        ndata = len(resid)
        chisqr = (resid**2).sum()
        nfree  = (ndata - self.nvarys)
        redchi = chisqr / nfree

        setattr(group, 'lmdif_status', ier)
        setattr(group, 'lmdif_message', errmsg)
        setattr(group, 'lmdif_success', ier in [1, 2, 3, 4])
        setattr(group, 'toler',  self.toler)
        setattr(group, 'nfcn_calls',  infodict['nfev'])
        setattr(group, 'residual',   resid)
        setattr(group, 'message',    message)
        setattr(group, 'chi_square', chisqr)
        setattr(group, 'chi_reduced', redchi)
        setattr(group, 'nvarys', self.nvarys)
        setattr(group, 'nfree', nfree)
        setattr(group, 'errorbars', cov is not None)

        for name in self.var_names:
            par = getattr(group, name)
            par.stderr = 0
            par.correl = None

        if cov is not None:
            covar = cov
            if self.scale_covar:
                cov = cov * chisqr / nfree
            for ivar, name in enumerate(self.var_names):
                par = getattr(group, name)
                par.stderr = sqrt(cov[ivar, ivar])
                par.correl = {}
                for jvar, name2 in enumerate(self.var_names):
                    if jvar != ivar:
                        par.correl[name2] = (cov[ivar, jvar]/
                                             (par.stderr * sqrt(cov[jvar, jvar])))
            setattr(group, 'covar_vars', self.var_names)
            setattr(group, 'covar',      cov)
        return ier

def minimize(fcn, group,  args=None, kws=None,
             scale_covar=True, iter_cb=None, _larch=None, **fit_kws):
    """simple minimization function,
    finding the values for the params which give the
    minimal sum-of-squares of the array return by fcn
    """
    if not _larch.symtable.isgroup(group):
        return 'param group is not a Larch Group'

    fitter = Minimizer(fcn, group, fcn_args=args, fcn_kws=kws,
                       iter_cb=iter_cb, scale_covar=scale_covar,
                       _larch=_larch,  **fit_kws)
    fitter.leastsq()


def guess(value, _larch=None, **kws):
    """create a fitting Parameter as a Variable.
    A minimum or maximum value for the variable value can be given:
       x = guess(10, min=0)
       y = guess(1.2, min=1, max=2)
    """
    kws.update({'vary':True})
    return Parameter(value, _larch=_larch, **kws)

def fit_report(group, min_correl=0.1, _larch=None, **kws):
    """print report of fit statistics given 'fit parameter group'
    """
    if not _larch.symtable.isgroup(group):
        print 'must pass Group to fit_report()'
        return
    topline = '===================== FIT RESULTS ====================='
    header = '[[%s]]'
    varformat = '   %12s = % f +/- %f   (init= % f)'
    exprformat = '   %12s = % f   = \'%s\''
    out = [topline, header % 'Statistics']

    npts = len(group.residual)
    out.append('   npts, nvarys       = %i, %i' % (npts, group.nvarys))
    out.append('   nfree, nfcn_calls  = %i, %i' % (group.nfree, group.nfcn_calls))
    out.append('   chi_square         = %f' % (group.chi_square))
    out.append('   reduced chi_square = %f' % (group.chi_reduced))
    out.append(' ')
    out.append(header % 'Variables')
    exprs = []
    for name in dir(group):
        var = getattr(group, name)
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
                    
    covar_vars = getattr(group, 'covar_vars', [])
    if len(covar_vars) > 0:
        out.append(' ')
        out.append(header % 'Correlations' +
                   '    (unreported correlations are < % .3f)' % min_correl)
        correls = {}
        for i, name in enumerate(covar_vars):
            par = getattr(group, name)
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
    out.append('='*len(topline))
    return '\n'.join(out)


def registerLarchPlugin():
    return ('_math', {'minimize': minimize,
                      'guess': guess,
                      'fit_report': fit_report  })
