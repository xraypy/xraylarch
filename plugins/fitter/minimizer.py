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
from scipy.optimize import leastsq
import re
from larch.utils import OrderedDict
from larch.larchlib import Parameter
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
                 iter_cb=None, scale_covar=True,
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

        for name in self.defvars:
            par = getattr(group, name)
            par.value = par.defvar.evaluate()

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
        if not self._larch.symtable.isgroup(self.paramgroup):#         if not isgroup(self.paramgroup):
            print 'param group is not a Larch Group'
            return
        self.nfev_calls = 0
        self.var_names = []
        self.defvars = []
        self.vars = []
        self.nvarys = 0
        for name in dir(self.paramgroup):
            # print 'param? ', name
            par = getattr(self.paramgroup, name)
            if not isinstance(par, Parameter):
                continue
            if par.expr is not None:
                par.defvar = Parameter(par.expr, _larch=self._larch)
                par.vary = False
                self.defvars.append(name)
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

    def leastsq(self, scale_covar=True, **kws):
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
        lskws = dict(full_output=1, xtol=1.e-7, ftol=1.e-7,
                     gtol=1.e-7, maxfev=1000*(self.nvarys+1), Dfun=None)

        lskws.update(self.kws)
        lskws.update(kws)

        if lskws['Dfun'] is not None:
            self.jacfcn = lskws['Dfun']
            lskws['Dfun'] = self.__jacobian

        lsout = leastsq(self.__residual, self.vars, **lskws)
        vbest, cov, infodict, errmsg, ier = lsout
        resid = infodict['fvec']

        group = self.paramgroup

        lmdif_messag = errmsg
        success = ier in [1, 2, 3, 4]
        message = 'Fit succeeded.'

        if ier == 0:
            message = 'Invalid Input Parameters.'
        elif ier == 5:
            message = self.err_maxfev % lskws['maxfev']
        else:
            message = 'Fit tolerance may to be too small.'
        if cov is None:
            message = '%s Could not estimate error-bars' % message

        lmdif_out = dict(message=message, lmdif_message=errmsg,  ier=ier, success=success)
        lmdif_out.update(infodict)

        ndata = len(resid)

        chisqr = (resid**2).sum()
        nfree  = (ndata - self.nvarys)
        redchi = chisqr / nfree

        for name in self.var_names:
            par = getattr(group, name)
            par.stderr = 0
            par.correl = None

        if cov is not None:
            errorbars = True
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

        setattr(group, 'errorbars',  errorbars)
        setattr(group, 'covar_vars', self.var_names)
        setattr(group, 'covar',      cov)
        setattr(group, 'lmdif_status', ier)
        setattr(group, 'nfcn_calls',  infodict['nfev'])
        setattr(group, 'residual',   resid)
        setattr(group, 'message',    message)
        setattr(group, 'chi_square', chisqr)
        setattr(group, 'chi_reduced', redchi)
        setattr(group, 'nvarys', self.nvarys)
        setattr(group, 'nfree', nfree)
        # print infodict.keys()
        return success

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

    return fitter.leastsq()

def guess(value, _larch=None, **kws):
    """create a fitting Parameter as a Variable.
    A minimum or maximum value for the variable value can be given:
       x = guess(10, min=0)
       y = guess(1.2, min=1, max=2)
    """
    return Parameter(value, vary=True,  _larch=_larch, **kws)

def fit_report(group, _larch=None, **kws):
    """print fit report
    """
    if not _larch.symtable.isgroup(group):
        print 'must pass Group to fit_report()'
        return
    out = ['=================', '   Fit results',
           '=================']


    npts = len(group.residual)
    out.append('  npoints, nvarys, nfree = %i, %i, %i' % (npts,
                                                          group.nvarys,
                                                          group.nfree))
    out.append('  n_function calls = %i' % (group.nfcn_calls))
    out.append('  chi_square = %f' % (group.chi_square))
    out.append('  reduced chi_square = %f' % (group.chi_reduced))
    out.append(' ') # =================')
    for name in dir(group):
        var = getattr(group, name)
        iname = len(name)
        if iname < 16:
            name = name + ' '*(17-iname)[:16]
        if isinstance(var, Parameter):
            if var.vary:
                out.append(' %s  %f +/- %f    (init = %f)'  % (name, var.value,
                                                               var.stderr,
                                                               var._initval))

    return '\n'.join(out)

def registerLarchPlugin():
    return ('_math', {'minimize': minimize,
                      'guess': guess,
                      'fit_report': fit_report  })
