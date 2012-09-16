==============================================
:func:`minimize` and Objective Functions
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

A simple objective function that models data as a line might look like this::

    params = group(offset = param(0., vary=True),
                   slope = param(200, min=0, vary=True))

    def residual(pars, xdata=None, ydata=None):
        model = pars.offset + pars.slope * xdata
        diff  = ydata - model
        return diff
    enddef

Here ``params`` is a Group containing two Parameters as defined by
:func:`_math.param`, discussed earlier.


To actually perform the fit, the :func:`minimize` function must be called.  This
takes the objective function as its first argument, and the group containing all
the Parameters as its second argument.  As the fit proceeds, the values  the Parameters
will be updated and passed into the objective function.  Optional arguments for the
objective function can be specified as well.  In addition, there are several optional
arguments which are passed on to the underlying fitting function (:func:`scipy.optimize.leastsq`).

.. function:: minimize(fcn, paramgroup, args=None, kws=None, ...)

    find the best-fit values for the Parameters in ``paramgroup`` such that the
    output array from the objective function :func:`fcn` has minimal sum-of-squares.

    :param fcn: objective function, which must have signature and output as described below.
    :param paramgroup: a Group containing the Parameters used by the
         objective function. This will be passed as the first argument to the
         objective function.  The Group can contain other components in
         addition to the set of Parameters for the model.

    returns fit object that can be used to modify or re-run fit.  Most results
    of interest are written to the *paramgroup*.
