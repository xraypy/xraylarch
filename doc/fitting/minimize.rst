==================================
Minimize and Objective Functions
==================================

As mentioned above, the objective function is meant to calculate the fit
residual vector (data - model) given a group of parameters, and optional
inputs.  You'll note that we didn't explicitly mention the data here.  This
is because, in general, the data to be modeled may be quite complex.  It
might, for example, be contained in two or more arrays -- perhaps what you
want to model is the difference of two image arrays, or the fourier
filtered average of ten spectra.  All these are best handled through
optional arguments.  The objective function really only needs to have as
its first argument a group containing all the parameters used in the model.

A simple model for a linear fit might look like this::

    params = group(offset = param(0), slope = param(1))

    def residual(pars, xdata=None, ydata=None):
        model = pars.offset + pars.slope * xdata
        diff  = ydata - model
        return diff
    enddef

Here ``params`` is a Larch group containing two Parameters as defined by
:func:`_math.param`, discussed above.


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
