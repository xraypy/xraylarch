#!/usr/bin/env python
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


   Copyright (c) 2012 Matthew Newville, The University of Chicago
   <newville@cars.uchicago.edu>
"""

from numpy import dot, eye, ndarray, ones_like, sqrt, take, transpose, triu
from numpy.dual import inv
from numpy.linalg import LinAlgError
from scipy.optimize import leastsq as scipy_leastsq

# check for scipy.optimize.minimize
HAS_SCALAR_MIN = False
try:
    from scipy.optimize import minimize as scipy_minimize
    HAS_SCALAR_MIN = True
except ImportError:
    pass

# check for uncertainties package
HAS_UNCERTAIN = False
try:
    import uncertainties
    HAS_UNCERTAIN = True
except ImportError:
    pass

from .parameter import isParameter

try:
    from larch import Group
except:
    Group = None

class MinimizerException(Exception):
    """General Purpose Exception"""
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return "\n%s" % (self.msg)

class Minimizer(object):
    """general minimizer"""
    err_maxfev   = """Too many function calls (max set to  %i)!  Use:
    minimize(func, params, ...., maxfev=NNN)
or set  leastsq_kws['maxfev']  to increase this maximum."""

    def __init__(self, fcn, params, fcn_args=None, fcn_kws=None,
                 scale_covar=True, toler=1.e-7, _larch=None, jacfcn=None, **kws):
        self.userfcn = fcn
        self.paramgroup = params
        self.userargs = fcn_args
        if self.userargs is None:
            self.userargs = []

        self.userkws = fcn_kws
        if self.userkws is None:
            self.userkws = {}
        self._larch = _larch
        self.toler = toler
        self.scale_covar = scale_covar
        self.kws = kws

        self.jacfcn = jacfcn
        self.__prepared = False

    def __update_params(self, fvars):
        """
        set parameter values from values of fitted variables
        """
        if not self.__prepared:
            print('fit not prepared!')
        group = self.paramgroup
        for name, val in zip(self.var_names, fvars):
            par = getattr(group, name)
            par._val  = par._from_internal(val)

    def __residual(self, fvars):
        """
        residual function used for least-squares fit.
        With the new, candidate values of fvars (the fitting variables),
        this evaluates all parameters, including setting bounds and
        evaluating constraints, and then passes those to the
        user-supplied function to calculate the residual.
        """
        self.__update_params(fvars)
        return self.userfcn(self.paramgroup, *self.userargs, **self.userkws)

    def __jacobian(self, fvars):
        """
        analytical jacobian to be used with the Levenberg-Marquardt
        """
        # computing the jacobian
        self.__update_params(fvars)
        return self.jacfcn(self.paramgroup, *self.userargs, **self.userkws)


    def prepare_fit(self, force=False):
        """prepare parameters for fit
        determine which parameters are actually variables
        and which are defined expressions.
        """

        if self.__prepared and not force:
            return

        # set larch's paramGroup to this group of parameters
        if self._larch.symtable.isgroup(self.paramgroup):
            self._larch.symtable._sys.paramGroup = self.paramgroup
        else:
            self._larch.write.write('Minimize Error: invalid parameter group!')
            return

        self.var_names = []
        self.defvars = []
        self.vars = []
        self.nvarys = 0
        for name in dir(self.paramgroup):
            par = getattr(self.paramgroup, name)
            if isParameter(par):
                val0 = par.setup_bounds()
                if par.expr is not None:
                    par._getval()
                elif par.vary:
                    self.var_names.append(name)
                    self.vars.append(val0)
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
        self.prepare_fit(force=True)
        toler = self.toler
        lskws = dict(full_output=1, xtol=toler, ftol=toler,
                     gtol=toler, maxfev=1000*(self.nvarys+1), Dfun=None)

        lskws.update(self.kws)
        lskws.update(kws)

        if lskws['Dfun'] is not None:
            self.jacfcn = lskws['Dfun']
            lskws['Dfun'] = self.__jacobian

        lsout = scipy_leastsq(self.__residual, self.vars, **lskws)
        _best, cov, infodict, errmsg, ier = lsout
        resid = infodict['fvec']
        group = self.paramgroup

        # need to map _best values to params, then calculate the
        # grad for the variable parameters
        grad = ones_like(_best)   # holds scaled gradient for variables
        vbest = ones_like(_best)  # holds best values for variables
        named_params = {}         # var names : parameter object
        for ivar, name in enumerate(self.var_names):
            named_params[name] = par = getattr(group, name)
            grad[ivar] = par.scale_gradient(_best[ivar])
            vbest[ivar] =  par.value

        # modified from JJ Helmus' leastsqbound.py
        # compute covariance matrix here explicitly...
        infodict['fjac'] = transpose(transpose(infodict['fjac']) /
                                     take(grad, infodict['ipvt'] - 1))

        rvec = dot(triu(transpose(infodict['fjac'])[:self.nvarys,:]),
                take(eye(self.nvarys),infodict['ipvt'] - 1,0))
        try:
            cov = inv(dot(transpose(rvec),rvec))
        except LinAlgError:
            cov = None

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

        ofit = group
        if Group is not None:
            ofit = group.fit = Group()

        ofit.method = 'leastsq'
        ofit.fjac = infodict['fjac']
        ofit.fvec = infodict['fvec']
        ofit.qtf  = infodict['qtf']
        ofit.ipvt = infodict['ipvt']
        ofit.status =  ier
        ofit.message =  errmsg
        ofit.success =  ier in [1, 2, 3, 4]
        ofit.nfev =   infodict['nfev']
        ofit.toler =   self.toler

        group.residual =    resid
        group.message =     message
        group.chi_square =  chisqr
        group.chi_reduced =  redchi
        group.nvarys =  self.nvarys
        group.nfree =  nfree
        group.errorbars =  cov is not None

        for par in named_params.values():
            par.stderr, par.correl = 0, None

        if cov is not None:
            if self.scale_covar:
                cov = cov * chisqr / nfree
            for iv, name in enumerate(self.var_names):
                p = named_params[name]
                p.stderr = sqrt(cov[iv, iv])
                p.correl = {}
                for jv, name2 in enumerate(self.var_names):
                    if jv != iv:
                        p.correl[name2] = (cov[iv, jv]/
                                           (p.stderr * sqrt(cov[jv, jv])))
            group.covar_vars = self.var_names
            group.covar = cov

        if HAS_UNCERTAIN and cov is not None:
            # uncertainties for constrained parameters:
            #   get values with uncertainties (including correlations),
            #   temporarily set Parameter values to these,
            #   re-evaluate contrained parameters to extract stderr
            #   and then set Parameters back to best-fit value
            uvars = uncertainties.correlated_values(vbest, cov)
            for val, nam in zip(uvars, self.var_names):
                named_params[nam]._val = val
            for nam in dir(self.paramgroup):
                obj = getattr(self.paramgroup, nam)
                if isParameter(obj):
                    try:
                        if obj._ast is not None: # only constrained params
                            obj.stderr = obj.value.std_dev()
                    except:
                        pass
            for val, nam in zip(uvars, self.var_names):
                named_params[nam]._val = val.nominal_value
        return ier

    def scalar_minimize(self, method='Nelder-Mead', **kws):
        """
        use one of the scaler minimization methods from scipy.
        Available methods include:
          Nelder-Mead
          Powell
          CG  (conjugate gradient)
          BFGS
          Newton-CG
          Anneal
          L-BFGS-B
          TNC
          COBYLA
          SLSQP

        If the objective function returns a numpy array instead
        of the expected scalar, the sum of squares of the array
        will be used.

        Note that bounds and constraints can be set on Parameters
        for any of these methods, so are not supported separately
        for those designed to use bounds.

        """
        if not HAS_SCALAR_MIN :
            raise NotImplementedError

        self.prepare_fit()

        maxfev = 1000*(self.nvarys + 1)
        opts = {'maxiter': maxfev}
        if method not in ('L-BFGS-B','TNC'):
            opts['maxfev'] = maxfev

        fmin_kws = dict(method=method, tol=self.toler, options=opts)

        fmin_kws.update(self.kws)
        fmin_kws.update(kws)
        def penalty(parvals):
            "local penalty function -- eval sum-squares residual"
            r = self.__residual(parvals)
            if isinstance(r, ndarray):
                r = (r*r).sum()
            return r

        ret = scipy_minimize(penalty, self.vars, **fmin_kws)

        resid  = self.__residual(ret.x)
        ndata  = len(resid)
        chisqr = (resid**2).sum()
        nfree  = (ndata - self.nvarys)
        redchi = chisqr / nfree

        ofit = group = self.paramgroup
        if Group is not None:
            ofit = group.fit = Group()

        ofit.method    = method
        ofit.nfev      = ret.nfev
        ofit.success   = ret.success
        ofit.status    = ret.status
        group.nvarys   = self.nvarys
        group.nfree    = nfree
        group.residual = resid
        group.message  = ret.message
        group.chi_square  = chisqr
        group.chi_reduced = redchi
        group.errorbars   = False


def minimize(fcn, group,  args=None, kws=None, method='leastsq',
             _larch=None, **fit_kws):
    """simple minimization function,
    finding the values for the params which give the
    minimal sum-of-squares of the array return by fcn
    """
    if not _larch.symtable.isgroup(group):
        return 'param group is not a Larch Group'

    fit = Minimizer(fcn, group, fcn_args=args, fcn_kws=kws,
                    scale_covar=True, _larch=_larch,  **fit_kws)

    _scalar_methods = {'nelder': 'Nelder-Mead',
                       'powell': 'Powell',
                       'cg': 'CG',
                       'bfgs': 'BFGS',
                       'newton': 'Newton-CG',
                       # 'anneal': 'Anneal',
                       'lbfgs': 'L-BFGS-B',
                       'l-bfgs': 'L-BFGS-B',
                       'tnc': 'TNC',
                       'cobyla': 'COBYLA',
                       'slsqp': 'SLSQP'}

    meth = method.lower()
    meth_found = False
    if HAS_SCALAR_MIN:
        for name, method in _scalar_methods.items():
            if meth.startswith(name):
                meth_found = True
                fit.scalar_minimize(method=method)
    if not meth_found:
        fit.leastsq()
    return fit

def fit_report(group, show_correl=True, min_correl=0.1, _larch=None, **kws):
    """print report of fit statistics given 'fit parameter group'
    """
    if not _larch.symtable.isgroup(group):
        print('must pass Group to fit_report()')
        return
    topline = '===================== FIT RESULTS ====================='
    header = '[[%s]] %s'
    varformat  = '   %12s = %s (init= % f)'
    exprformat = '   %12s = %s = \'%s\''
    out = [topline]

    npts = len(group.residual)
    ofit = getattr(group, 'fit', None)
    if ofit is None:  ofit = group
    methodname = getattr(ofit, 'method', 'leastsq')
    success = getattr(ofit, 'success', False)

    if success:
        subtitle = '   Fit succeeded, '
    else:
        subtitle = '   Fit Failed, '
    subtitle = "%s method = '%s'." % (subtitle, methodname)
    out.append(header % ('Statistics', subtitle))

    if hasattr(group, 'message'):
        out.append('   Message from fit    = %s' % (group.message))

    out.append('   npts, nvarys, nfree = %i, %i, %i' % (npts, group.nvarys, group.nfree))

    if hasattr(ofit, 'nfev'):
        out.append('   nfev (func calls)   = %i' % (ofit.nfev))
    if hasattr(group, 'chi_square'):
        out.append('   chi_square          = %f' % (group.chi_square))
    if hasattr(group, 'chi_reduced'):
        out.append('   reduced chi_square  = %f' % (group.chi_reduced))
    out.append(' ')
    out.append(header % ('Variables',''))
    exprs = []
    for name in dir(group):
        var = getattr(group, name)
        if len(name) < 14:
            name = (name + ' '*14)[:14]
        if isParameter(var):
            sval = "% f" % var.value
            if var.stderr is not None:
                sval = "% f +/- %f" % (var.value, var.stderr)
            if var.vary:
                out.append(varformat % (name, sval, var._initval))
            elif var.expr is not None:
                exprs.append(exprformat % (name, sval, var.expr))
    if len(exprs) > 0:
        out.append(header % 'Constraint Expressions')
        out.extend(exprs)

    covar_vars = getattr(group, 'covar_vars', [])
    if show_correl and len(covar_vars) > 0:
        subtitle = '    (unreported correlations are < % .3f)' % min_correl
        out.append(' ')
        out.append(header % ('Correlations', subtitle))
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

# def registerLarchPlugin():
#     return ('_math', {'minimize': minimize,
#                       'guess': guess,
#                       'fit_report': fit_report})

