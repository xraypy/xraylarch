
.. _fitting-minimize-sec:

==============================================
:func:`minimize` and objective Functions
==============================================


As mentioned above, the objective function returns an array calculated from
given a group of parameters.  This array will be minimized in the
least-squares sense in the fitting process.  For most fits, the objective
function should return the residual array (data - model), given a group of
parameters and optional inputs.  You'll note that we didn't explicitly
mention any *data* in describing the objective function.  This is because,
formally, the minimization process may be looking for a solution to a
purely mathematical problem, not just fitting to data.  Even when the
objective function does return the difference of data and model, the data
to be modeled may be quite complex.  It might, for example, be contained in
two or more arrays -- perhaps what you want to model is the difference of
two image arrays, or the fourier filtered average of ten spectra.  Because
of such complexities, the reliance of optional arguments appears to be the
best approach.

.. index:: objective function

A simple objective function that models data as a line might look like this::

    params = param_group(offset = param(0., vary=True),
                 	 slope = param(200, min=0, vary=True))

    def residual(pars, xdata=None, ydata=None):
        model = pars.offset + pars.slope * xdata
        diff  = ydata - model
        return diff
    enddef

Here ``params`` is a Group containing two Parameters as defined by
:func:`_math.param`, discussed earlier.

To actually perform the fit, the :func:`minimize` function must be
called.  This takes the objective function as its first argument, and
the group containing all the Parameters as its second argument,
keyword arguments for the optional arguments for the objective
function, and several keyword arguments to alter the fitting process
itself.  Here is the function call using the objective function
defined above, assuming you have a group called ``data`` containing
the data you are trying to fit::

    result = minimize(residual, params, kws={'xdata': data.x, 'ydata':data.y})

As the fit proceeds, the values the Parameter values will be updated, and
the objective function will be called to recalculate the residual array.
Thus the objective function may be called many times before the fitting
procedure decides it has found the best solution that it can.

.. versionchanged:: 0.9.34
   :func:`minimize` returns a result group containing fit statistics.

.. function:: minimize(fcn, paramgroup, args=None, kws=None, method='leastsq', **extra_kws)

    find the best-fit values for the Parameters in ``paramgroup`` such that the
    output array from the objective function :func:`fcn` has minimal sum-of-squares.

    :param fcn: objective function, which must have signature and output as described below.
    :param paramgroup: a Group containing the Parameters used by the
         objective function. This will be passed as the first argument to the
         objective function.  The Group can contain other components in
         addition to the set of Parameters for the model.
    :param args: a tuple of positional arguments to pass to the
                 objective function.  Note that a single argument tuple
                 is constructed by following a value with a comma (it
                 is not sufficient to enclose a single value in
                 parentheses)
    :param kws:  a dictionary of keyword/value arguments to pass to the objective function.
    :param method:  name (case insensitive) of minimization method to use (default='leastsq')
    :param extra_kws:  additional keywords to pass to fitting method.
    :returns:   a Group containing several fitting statisics and best-fit parameters.

    The ``method`` argument gives the name of the fitting method to be
    used.  Several methods are available, as described below in
    :ref:`Table of Fitting Methods <minimize-methods_table>`.

.. _minimize-methods_table:

   Table of Fitting Methods.

   Listed are the names and description of fitting methods available to the
   :func:`minimize` function.  The *leastsq* method is the default, and the
   only method for which uncertainties and correlations are automatically
   calculated.

    ============= ==================================================================
     method name    Description
    ============= ==================================================================
     Leastsq        Levenberg-Marquardt.
     Nelder-Mead    Nelder-Mead downhill simplex.
     Powell         Powell's method.
     BFGS           quasi-Newton method of Broyden, Fletcher, Goldfarb, and Shanno.
     CG             Conjugate Gradient.

     LBFGSB         Limited-Memory BFGS Method with Constraints.
     TNC            Truncated Newton method.
     COBYLA         Constrained Optimization BY Linear Approximation.
     SLSQP          Sequential Least SQuares Programming.
    ============= ==================================================================

Further information on these methods, including full lists of extra
parameters that can be passed to them, can be found at
:lmfitdoc:`fitting`.


It should be noted that the Levenberg-Marquardt algorithm is almost always
the fastest of the methods listed (often by 10x), and is generally fairly
robust.  It is sometimes criticized as being sensitive to initial guesses
and prone to finding local minima.  The other fitting methods use very
different algorithms, and so can be used to explore these effects. Many of
them are much slower -- using more than ten times as many evaluations of
the objective function is not unusual. This does not guarantee a more
robust answer, but it does allow one to try out and compare the results of
the different methods.

While the TNC, COBYLA, SLSQP, and LBFGSB methods are supported, their
principle justification is that the underlying algorithms support
constraints.  For Larch, this advantage is not particularly important, as
all fitting methods can have constraints applied through Parameters, and
the mechanism used by the native methods is not actually even supported
with Larch.  That said, all these methods are still interesting to explore.


Extra keywords for the *leastsq* method include:

    +----------------------+----------------+------------------------------------------------------------+
    | ``extra_kw`` arg for |  Default Value | Description                                                |
    | ``method='leastsq'`` |                |                                                            |
    +======================+================+============================================================+
    |   xtol               |  1.e-7         | Relative error in the approximate solution                 |
    +----------------------+----------------+------------------------------------------------------------+
    |   ftol               |  1.e-7         | Relative error in the desired sum of squares               |
    +----------------------+----------------+------------------------------------------------------------+
    |   maxfev             | 2000*(nvar+1)  | maximum number of function calls (nvar= # of variables)    |
    +----------------------+----------------+------------------------------------------------------------+
    |   Dfun               | ``None``       | function to call for Jacobian calculation                  |
    +----------------------+----------------+------------------------------------------------------------+

By default, numerical derivatives are used, and the following arguments are
used.
