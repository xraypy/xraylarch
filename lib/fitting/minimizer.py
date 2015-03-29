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

from numpy import (abs, array, asarray, dot, eye, ndarray, ones_like,
                   sqrt, take, transpose, triu)

from numpy.dual import inv
from numpy.linalg import LinAlgError
from scipy.optimize import _minpack
from scipy.optimize.minpack import _check_func
# check for scipy.optimize.minimize
HAS_SCALAR_MIN = False
try:
    from scipy.optimize import minimize as scipy_minimize
    HAS_SCALAR_MIN = True
except ImportError:
    pass

# use local version of uncertainties package
from . import uncertainties

from .parameter import isParameter

try:
    from ..symboltable import Group
except:
    Group = None

class MinimizerException(Exception):
    """General Purpose Exception"""
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return "\n%s" % (self.msg)


def larcheval_with_uncertainties(*vals,  **kwargs):
    """
    given values for variables, calculate object value.
    This is used by the uncertainties package to calculate
    the uncertainty in an object even with a complicated
    expression.
    """
    _obj   = kwargs.get('_obj', None)
    _pars  = kwargs.get('_pars', None)
    _names = kwargs.get('_names', None)
    _larch = kwargs.get('_larch', None)
    if (_obj is None or _pars is None or
        _names is None or _larch is None or
        _obj._ast is None):
        return 0
    for val, name in zip(vals, _names):
        _pars[name]._val = val
    result =  _larch.eval(_obj._ast)
    if isParameter(result):
        result = result.value
    return result

wrap_ueval = uncertainties.wrap(larcheval_with_uncertainties)

def eval_stderr(obj, uvars, _names, _pars, _larch):
    """evaluate uncertainty and set .stderr for a parameter `obj`
    given the uncertain values `uvars` (a list of uncertainties.ufloats),
    a list of parameter names that matches uvars, and a dict of param
    objects, keyed by name.

    This uses the uncertainties package wrapped function to evaluate
    the uncertainty for an arbitrary expression (in obj._ast) of parameters.
    """
    if not isParameter(obj):
        return
    if obj._ast is None:
        return
    uval = wrap_ueval(*uvars, _obj=obj, _names=_names,
                      _pars=_pars, _larch=_larch)
    try:
        obj.stderr = uval.std_dev()
        obj._uval  = uval
    except:
        obj.stderr = 0
        obj._uval  = None



def leastsq(func, x0, args=(), Dfun=None, ftol=1.e-7, xtol=1.e-7,
            gtol=1.e-7, maxfev=0, epsfcn=None, factor=100, diag=None):
    """
    Minimize the sum of squares of a set of equations.
    Adopted from scipy.optimize.leastsq

    ::

        x = arg min(sum(func(y)**2,axis=0))
                 y

    Parameters
    ----------
    func : callable
        should take at least one (possibly length N vector) argument and
        returns M floating point numbers.
    x0 : ndarray
        The starting estimate for the minimization.
    args : tuple
        Any extra arguments to func are placed in this tuple.
    Dfun : callable
        A function or method to compute the Jacobian of func with derivatives
        across the rows. If this is None, the Jacobian will be estimated.
    ftol : float
        Relative error desired in the sum of squares.
    xtol : float
        Relative error desired in the approximate solution.
    gtol : float
        Orthogonality desired between the function vector and the columns of
        the Jacobian.
    maxfev : int
        The maximum number of calls to the function. If zero, then 100*(N+1) is
        the maximum where N is the number of elements in x0.
    epsfcn : float
        A suitable step length for the forward-difference approximation of the
        Jacobian (for Dfun=None). If epsfcn is less than the machine precision,
        it is assumed that the relative errors in the functions are of the
        order of the machine precision.
    factor : float
        A parameter determining the initial step bound
        (``factor * || diag * x||``). Should be in interval ``(0.1, 100)``.
    diag : sequence
        N positive entries that serve as a scale factors for the variables.

    Returns
    -------
    x : ndarray
        The solution (or the result of the last iteration for an unsuccessful
        call).
    cov_x : ndarray
        Uses the fjac and ipvt optional outputs to construct an
        estimate of the jacobian around the solution.  ``None`` if a
        singular matrix encountered (indicates very flat curvature in
        some direction).  This matrix must be multiplied by the
        residual variance to get the covariance of the
        parameter estimates -- see curve_fit.
    infodict : dict
        a dictionary of optional outputs with the key s::

            - 'nfev' : the number of function calls
            - 'fvec' : the function evaluated at the output
            - 'fjac' : A permutation of the R matrix of a QR
                     factorization of the final approximate
                     Jacobian matrix, stored column wise.
                     Together with ipvt, the covariance of the
                     estimate can be approximated.
            - 'ipvt' : an integer array of length N which defines
                     a permutation matrix, p, such that
                     fjac*p = q*r, where r is upper triangular
                     with diagonal elements of nonincreasing
                     magnitude. Column j of p is column ipvt(j)
                     of the identity matrix.
            - 'qtf'  : the vector (transpose(q) * fvec).

    mesg : str
        A string message giving information about the cause of failure.
    ier : int
        An integer flag.  If it is equal to 1, 2, 3 or 4, the solution was
        found.  Otherwise, the solution was not found. In either case, the
        optional output variable 'mesg' gives more information.

    Notes
    -----
    "leastsq" is a wrapper around MINPACK's lmdif and lmder algorithms.

    cov_x is a Jacobian approximation to the Hessian of the least squares
    objective function.
    This approximation assumes that the objective function is based on the
    difference between some observed target data (ydata) and a (non-linear)
    function of the parameters `f(xdata, params)` ::

           func(params) = ydata - f(xdata, params)

    so that the objective function is ::

           min   sum((ydata - f(xdata, params))**2, axis=0)
         params

    """
    x0 = asarray(x0).flatten()
    n = len(x0)
    if not isinstance(args, tuple):
        args = (args,)
    shape = _check_func('leastsq', 'func', func, x0, args, n)
    if isinstance(shape, tuple) and len(shape) > 1:
        # older versions returned only shape
        # newer versions return (shape, dtype)
        shape = shape[0]
    m = shape[0]
    if n > m:
        raise TypeError('Improper input: N=%s must not exceed M=%s' % (n, m))
    if maxfev == 0:
        maxfev = 200*(n + 1)
    if epsfcn is None:
        epsfcn = 2.e-5  # a relatively large value!!
    if Dfun is None:
        retval = _minpack._lmdif(func, x0, args, 1, ftol, xtol,
                                 gtol, maxfev, epsfcn, factor, diag)
    else:
        _check_func('leastsq', 'Dfun', Dfun, x0, args, n, (m, n))
        retval = _minpack._lmder(func, Dfun, x0, args, 1, 0, ftol, xtol,
                                 gtol, maxfev, factor, diag)

    errors = {0:["Improper input parameters.", TypeError],
              1:["Both actual and predicted relative reductions "
                 "in the sum of squares\n  are at most %f" % ftol, None],
              2:["The relative error between two consecutive "
                 "iterates is at most %f" % xtol, None],
              3:["Both actual and predicted relative reductions in "
                 "the sum of squares\n  are at most %f and the "
                 "relative error between two consecutive "
                 "iterates is at \n  most %f" % (ftol,xtol), None],
              4:["The cosine of the angle between func(x) and any "
                 "column of the\n  Jacobian is at most %f in "
                 "absolute value" % gtol, None],
              5:["Number of calls to function has reached "
                 "maxfev = %d." % maxfev, ValueError],
              6:["ftol=%f is too small, no further reduction "
                 "in the sum of squares\n  is possible.""" % ftol, ValueError],
              7:["xtol=%f is too small, no further improvement in "
                 "the approximate\n  solution is possible." % xtol, ValueError],
              8:["gtol=%f is too small, func(x) is orthogonal to the "
                 "columns of\n  the Jacobian to machine "
                 "precision." % gtol, ValueError],
              'unknown':["Unknown error.", TypeError]}

    info = retval[-1]    # The FORTRAN return value
    mesg = errors[info][0]
    cov_x = None
    if info in [1,2,3,4]:
        perm = take(eye(n),retval[1]['ipvt']-1,0)
        r = triu(transpose(retval[1]['fjac'])[:n,:])
        R = dot(r, perm)
        try:
            cov_x = inv(dot(transpose(R),R))
        except (LinAlgError, ValueError):
            pass
    return (retval[0], cov_x) + retval[1:-1] + (mesg, info)

class Minimizer(object):
    """general minimizer"""
    err_maxfev   = """Too many function calls (max set to  %i)!  Use:
    minimize(func, params, ...., maxfev=NNN)
or set  leastsq_kws['maxfev']  to increase this maximum."""

    def __init__(self, fcn, params, fcn_args=None, fcn_kws=None,
                 scale_covar=True, toler=1.e-7,
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
        self.toler = toler
        self.scale_covar = scale_covar
        self.kws = kws

        self.jacfcn = jacfcn
        self.__prepared = False
        self.prepare_fit()

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
        self.vars = []
        self.nvarys = 0
        for name in dir(self.paramgroup):
            par = getattr(self.paramgroup, name)
            if isParameter(par):
                val0 = par.setup_bounds()
                if par.vary:
                    self.var_names.append(name)
                    self.vars.append(val0)
                elif par.expr is not None:
                    par._getval()
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
        lskws = dict(xtol=toler, ftol=toler,
                     gtol=toler, maxfev=1000*(self.nvarys+1), Dfun=None)
        lskws.update(self.kws)
        lskws.update(kws)

        if lskws['Dfun'] is not None:
            self.jacfcn = lskws['Dfun']
            lskws['Dfun'] = self.__jacobian

        lsout = leastsq(self.__residual, self.vars, **lskws)
        del self.vars

        _best, cov, infodict, errmsg, ier = lsout
        resid  = infodict['fvec']
        ndata  = len(resid)
        chisqr = (resid**2).sum()
        nfree  = ndata - self.nvarys
        redchi = chisqr / nfree

        group = self.paramgroup
        # need to map _best values to params, then calculate the
        # grad for the variable parameters
        grad  = ones_like(_best)  # holds scaled gradient for variables
        vbest = ones_like(_best)  # holds best values for variables
        named_params = {}         # var names : parameter object
        for ivar, name in enumerate(self.var_names):
            named_params[name] = par = getattr(group, name)
            grad[ivar]  = par.scale_gradient(_best[ivar])
            vbest[ivar] = par.value
            par.stderr  = 0
            par.correl  = {}
            par._uval   = None
        # modified from JJ Helmus' leastsqbound.py
        # compute covariance matrix here explicitly...
        infodict['fjac'] = transpose(transpose(infodict['fjac']) /
                                     take(grad, infodict['ipvt'] - 1))

        rvec = dot(triu(transpose(infodict['fjac'])[:self.nvarys,:]),
                take(eye(self.nvarys),infodict['ipvt'] - 1,0))
        try:
            cov = inv(dot(transpose(rvec),rvec))
        except (LinAlgError, ValueError):
            cov = None

        # map covariance matrix to parameter uncertainties
        # and correlations
        if cov is not None:
            if self.scale_covar:
                cov = cov * chisqr / nfree

            # uncertainties for constrained parameters:
            #   get values with uncertainties (including correlations),
            #   temporarily set Parameter values to these,
            #   re-evaluate contrained parameters to extract stderr
            #   and then set Parameters back to best-fit value
            try:
                uvars = uncertainties.correlated_values(vbest, cov)
            except (LinAlgError, ValueError):
                cov, uvars = None, None
            group.covar_vars = self.var_names
            group.covar = cov

            if uvars is not None:
                # set stderr and correlations for variable, named parameters:
                for iv, name in enumerate(self.var_names):
                    p = named_params[name]
                    p.stderr = uvars[iv].std_dev()
                    p._uval  = uvars[iv]
                    p.correl = {}
                    for jv, name2 in enumerate(self.var_names):
                        if jv != iv:
                            p.correl[name2] = (cov[iv, jv]/
                                               (p.stderr * sqrt(cov[jv, jv])))
                for nam in dir(self.paramgroup):
                    obj = getattr(self.paramgroup, nam)
                    eval_stderr(obj, uvars, self.var_names,
                                named_params, self._larch)

                # restore nominal values that may have been tweaked to
                # calculate other stderrs
                for uval, nam in zip(uvars, self.var_names):
                    named_params[nam]._val  = uval.nominal_value

            # clear any errors evaluting uncertainties
            if self._larch.error:
                self._larch.error = []

        # collect results for output group
        message = 'Fit succeeded.'

        if ier == 0:
            message = 'Invalid Input Parameters.'
        elif ier == 5:
            message = self.err_maxfev % lskws['maxfev']
        elif ier > 5:
            message = 'See lmdif_message.'
        if cov is None:
            message = '%s Could not estimate error-bars' % message

        ofit = group
        if Group is not None:
            ofit = group.fit_details = Group()

        ofit.method = 'leastsq'
        ofit.fjac  = infodict['fjac']
        ofit.fvec  = infodict['fvec']
        ofit.qtf   = infodict['qtf']
        ofit.ipvt  = infodict['ipvt']
        ofit.nfev  = infodict['nfev']
        ofit.status  = ier
        ofit.message = errmsg
        ofit.success = ier in [1, 2, 3, 4]
        ofit.toler   = self.toler

        group.residual   = resid
        group.message    = message
        group.chi_square = chisqr
        group.chi_reduced = redchi
        group.nvarys     = self.nvarys
        group.nfree      = nfree
        group.errorbars  = cov is not None
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
        if method not in ('L-BFGS-B','TNC', 'SLSQP'):
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
        del self.vars
        resid  = self.__residual(ret.x)
        ndata  = len(resid)
        chisqr = (resid**2).sum()
        nfree  = (ndata - self.nvarys)
        redchi = chisqr / nfree

        ofit = group = self.paramgroup
        if Group is not None:
            ofit = group.fit_details = Group()

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

def fit_report(group, show_correl=True, min_correl=0.1, precision=None,
               _larch=None, **kws):
    """print report of fit statistics given 'fit parameter group'
    """
    if not _larch.symtable.isgroup(group):
        print('must pass Group to fit_report()')
        return
    _larch.symtable._sys.paramGroup = group

    topline = '===================== FIT RESULTS ====================='
    header = '[[%s]] %s'
    exprformat = '   %12s = %s = \'%s\''
    out = [topline]

    varformat  = '   %12s = %s (init= % f)'
    fmt_sca = "% f"
    fmt_err = "% f +/- %f"
    if precision is not None:
        varformat  = '   %%12s = %%s (init= %% .%if)' % precision
        fmt_sca = "%% .%if" % precision
        fmt_err = "%% .%if +/- %%.%if" % (precision, precision)

    npts = len(group.residual)
    ofit = getattr(group, 'fit_details', None)
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

    out.append('   npts, nvarys, nfree = %i, %i, %i' % (npts,
                                                        group.nvarys,
                                                        group.nfree))

    if hasattr(ofit, 'nfev'):
        out.append('   nfev (func calls)   = %i' % (ofit.nfev))
    if hasattr(group, 'chi_square'):
        out.append(('   chi_square          = %s' % fmt_sca) %
                   (group.chi_square))
    if hasattr(group, 'chi_reduced'):
        out.append(('   reduced chi_square  = %s' % fmt_sca) %
                   (group.chi_reduced))
    out.append(' ')
    out.append(header % ('Variables',''))
    exprs = []
    for name in dir(group):
        var = getattr(group, name)
        if len(name) < 14:
            name = (name + ' '*14)[:14]
        if isParameter(var):
            sval = fmt_sca % var.value
            if var.stderr is not None:
                sval = fmt_err % (var.value, var.stderr)
            if var.vary:
                out.append(varformat % (name, sval, var._initval))
            elif var.expr is not None:
                exprs.append(exprformat % (name, sval, var.expr))

    if len(exprs) > 0:
        out.append(header % ('Constraint Expressions', ''))
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
