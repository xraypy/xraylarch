

.. _lmfit: https://lmfit.github.io/lmfit-py/
.. _asteval: https://lmfit.github.io/asteval

.. _fitting-parameters_sec:

===============
Parameters
===============

The parameters used in the fitting model are all meant to be continuous
variables -- floating point numbers.  In general, the fitting procedure may
assign any value to any parameter.  In many cases, however, you may want to
place some restrictions on the value a parameter can take.  For example, if
you're fitting data to a line, you may want to ensure that the slope of the
line is positive.  For more complex cases, you might want to write a a
general model describing the data, but keep some of the parameters in the
model fixed.

In Larch, a **Parameter** is a fundamental data type designed to hold
variables for fits that can be restricted in the values it can take.  A
Parameter has several attributes, the most important of which is a
``value`` -- the current value.  A Parameter's value can be changed of
course -- this is what will happen during a fit -- but other attributes can
be set to help determine its value too.  In most cases, a Parameter can be
used as a floating point number, and its value attribute will be used.
Thus::

    larch> x = param(10)
    larch> print x
    param(10, vary=False)
    larch> print x+2
    12

To create a Parameter, use the :func:`param` function, which takes a value
as its first argument, and a few optional keyword arguments to control
whether the value is to be varied in a fit or kept fixed, to set optional
upper and lower bounds for the Parameter value, or to set an algebraic
expression to use to evaluate its value as a **constrained Parameter**.

..  function:: param(value, vary=False, min=None, max=None, expr=None)

    define a Parameter, setting some of it principle attributes

    :param value:  floating point value.  This value may be adjusted during a fit.
    :param vary:   flag telling whether Parameter is to be varied during a  fit (``True``, ``False``) [``False``]
    :param min:    minimum value the Parameter can take.
    :param max:    maximum value the Parameter can take.
    :param expr:   algebraic expression for a constrained Parameter.  See :ref:`param-constraints-label`  for details.
    :returns:      a new Parameter defined according to input.

A Parameter may have the following attributes to either control its value
or give additional information about its value:

     ============== ========================== ============= =============================
      attribute      meaning                    default       set by which functions:
     ============== ========================== ============= =============================
      value          value                                     :func:`param`
      vary           value can change in fit    ``False``      :func:`param`
      min            lower bound                ``None``       :func:`param`
      max            upper bound                ``None``       :func:`param`
      name           optional name              ``None``       :func:`param`
      expr           algebraic constraint       ``None``       :func:`param`
      stderr         standard error                            :func:`minimize`
      correl         correlations                              :func:`minimize`
      uvalue         value with uncertainty                    :func:`minimize`
     ============== ========================== ============= =============================

..  function:: guess(value, min=None, max=None, expr=None)

    define a variable Parameter, setting some of it principle attributes.
    The arguments here are identical to :func:`param`, except that
    ``vary=True`` is set.

An example of creating some parameters,  and creating a group of parameters would be::

    # create some Parameters
    c1 = param(0.75)              # a constant (non-varying) parameter
    a1 = param(1.0, min=0, max=5, vary=True)     # a bounded variable parameter
    a2 = guess(10., min=0)        # a semi-bounded variable parameter

    # create a group of parameters, either from existing parameters
    # or ones created right here
    params = group(a1 = a1, a2 = a2,
                   centroid = param(99, vary=False) )

    # add more parameters to the group:
    params.c1 = c1

    # add a constrained parameter: dependent on other parameters in the group
    params.e1 = param(expr='a1 - c1*sqrt(a2)')


setting bounds
~~~~~~~~~~~~~~~

Upper and lower bounds can be set on a Parameters value using the *min* and
*max* arguments to :func:`param` or by setting the *min* and *max*
attribute of an existing Parameter.  To remove a bound, set the
corresponding attribute to ``None``.

During a fit, a Parameter's value may approach or even equal one of the
bounds, but will never violate the boundary.  It should be kept in mind that a
Parameter with a best-fit value at or very close to a boundary may not have
an accurate estimate of its uncertainty.  In some cases, it may even be
that a best-fit value at a boundary will prevent a reasonable estimate of
the uncertainty in any of the other Parameters in the fit.

..  _param-constraints-label:

using algebraic constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is often useful to be able to build a fitting model in which Parameters
in the model are related to one another.  As a simple example, it might be
useful to fit a spectrum with a sum of two lineshapes that have different
centroids, but the same width.  As a second example, it might be useful to
fit a spectrum to a sum of two model spectra where the relative weight of
the model spectra must add to 1.

For each of these cases, one could write a model function that implemented
such constraints.  Rather than trying to capture and encourage such special
cases, Larch takes a more general approach, allowing Parameters to get
their value from an algebraic expression.  Thus, one might define an
objective function for a sum of two Gaussian functions (discussed in more
detail in :ref:`lineshape-functions-label`), as::

    def fit_2gauss(params, data):
        model = params.amp1 * gaussian(data.x, params.cen1, params.wid1) + \
                params.amp2 * gaussian(data.x, params.cen2, params.wid2)
        return (data.y - model)
    enddef

This is general and does not impose any relations between the parameter values
within the objective function.  But one can place such relations in the
definitions of the parameters and have them obeyed within the fit.  That
is, one could constrain the two widths of the Gaussians to be the same
value with::

    params.wid1 = guess(1, min=0)
    params.wid2 = param(expr='wid1')

and the value of `params.wid2` will have the same value as `params.wid1`
every time the objective is called, and will not be an independent variable
in the fit.  For the second example, one could constrain the two amplitude
parameters to add to 1 and each be between 0 and 1 as::

    params.amp1 = guess(0.5, min=0, max=1)
    params.amp2 = param(expr='1 - amp1')

.. index:: _sys.fiteval

One can use more complex expressions, and also access built-in values and
common mathematical functions, like `pi`, `sin`, and `log`.  Essentially
any valid Python/Larch expression is allowed, including slicing of arrays
and array methods. Some additional details are discussed below
(:ref:`fitting-fiteval_sec`),

.. versionchanged:: 0.9.34
   `_sys.paramGroup` is no longer used, and `_sys.fiteval` is used instead.

..  _param-param_group-label:

:func:`param_group`: creating a Parameter Group for fitting constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While the examples of constraint expressions above will work during a fit,
the constraint values will not be updated immediately in the main Larch
interpreter.  That is, doing::

    larch> params = group(amp1=guess(0.6, min=0, max=1),
                          amp2=param(expr='1 - amp1'))
    larch> print(params.amp1, params.amp2)
    (<Parameter 0.6, bounds=[0:1]>, <Parameter -inf, bounds=[-inf:inf], expr='1-amp1'>)

That is, the value of constrained parameter `amp2` is not properly set yet.
To be clear, a fit with this group of parameters will work, but it's
sometimes useful to see the values for the constrained parameters.

The function :func:`param_group` will create a "live, working" group of
parameters::

    larch> params = param_group(amp1=guess(0.6, min=0, max=1),
                                amp2=param(expr='1 - amp1'))
    larch> print(params.amp1, params.amp2)
    (<Parameter 'amp1', 0.6, bounds=[0:1]>, <Parameter 'amp2', 0.4, bounds=[-inf:inf], expr='1-amp1'>)

In addition, you can change the value of `params.amp1`, with the value of
`params.amp2` being automatically updated:

    larch> params.amp1.value = 0.2
    larch> print(params.amp1, params.amp2)
    (<Parameter 'amp1', 0.2, bounds=[0:1]>, <Parameter 'amp2', 0.8, bounds=[-inf:inf], expr='1-amp1'>)

.. function:: param_group(**kws)

    create and return a *Parameter Group* that uses `_sys.fiteval` for
    constraint expression.

    :param kws:  optional keyword/argument values for parameters
    :returns:    a new Parameter Group with working constraint expressions.

A Parameter Group can contain non-Parameter values as well as fitting
Parameters.  For backward compatibility, a simple group containing
parameters will work with fitting, but a :func:`param_group` is recommended
for many cases.


.. _fitting-fiteval_sec:

`fiteval` and details about algebraic constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beginning with version 0.9.34, Larch uses the `lmfit`_ python library to do
all the fitting.  This project is related to and very similar to Larch
itself, but is maintained and developed separately.  Lmfit supports
algebraic constraints like those discussed in the previous section, using
an isolated, embedded mini-interpreter (very similar to Larch itself, based
on `asteval`_).  Within Larch, this embedded expression interpreter for
fitting constraints is held in the Larch system variable `_sys.fiteval`.
The set of available functions and variables is in its symbol table,
`_sys.fiteval.symtable`, which has more than 400 named functions and
variables available, most of them from numpy.


During a fit, all the components of the *paramgroup* given to
:func:`minimize` will be put put into the `_sys.fiteval` symbol table.  Any
of these variables can be used in the constraint expressions.  In addition,
all the true parameters in the *paramgroup* will be converted into
`lmfit.Parameters`.  After the fit is complete, the updated parameter
values will be put back into the

The :func:`param_group` function discussed above keeps an internal link to
`_sys.fiteval` and uses that for evaluating constraint expressions.  That
is, following the above example, one can see the current values for
`params.amp1` and `params.amp2` within the `_sys.fiteval` symbol table::


    larch> params = param_group(amp1=guess(0.6, min=0, max=1),
                                amp2=param(expr='1 - amp1'))
    larch> print(params.amp1, params.amp2)
    (<Parameter 'amp1', 0.6, bounds=[0:1]>, <Parameter 'amp2', 0.4, bounds=[-inf:inf], expr='1-amp1'>)
    larch> print(_sys.fiteval.symtable.amp2)
    0.4
    larch> params1.amp.value = 0.1
    larch> print(params.amp1, params.amp2)
    (<Parameter 'amp1', 0.1, bounds=[0:1]>, <Parameter 'amp2', 0.9, bounds=[-inf:inf], expr='1-amp1'>)
    larch> print(_sys.fiteval.symtable.amp2)
    0.9


Because `_sys.fiteval` is used for all fits with :func:`minimize` (and for
XAFS, with :func:`feffit`), you may find yourself wanting to clear or reset
the fitting symbol table for a new fit.  This should not be necessary, but
it is available with the function :func:`reset_fiteval`:


.. function:: reset_fiteval()

     clear and reset `_sys.fiteval` for a new fit.   This function takes no
     arguments.


.. _fitting-uncertainties_sec:


working with uncertainties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _uncertainties: http://packages.python.org/uncertainties/

After a fit, each Parameter that was actually varied in the fit should be
assigned information about the uncertainty in the fitted value as well as
its best fit value.  On rare occasions (such as when a best-fit value is
very close to a bound) the setting of uncertainties is not possible.  The
primary way the uncertainty for a Parameter is expressed is with the
``stderr`` attribute, which holds the estimated standard error for the
Parameter's value.  The correlation with all other Parameters is held in
the ``correl`` attribute -- a dictionary with keys of variable names and
values of correlation with that variable.  In addition, the two-dimensional
covariance matrix will be held in the ``covar`` attribute of the parameter
group for each fit.

Note that the uncertainties calculated for constrained parameters involving
more than one variable will encapsulate not only the simple propogation of
errors for the independent variables, but also their correlation.  This can
have a significant impact on the uncertainties for constrained parameters.

Finally, each Parameter will have a ``uvalue`` attribute which is a special
object from the `uncertainties`_ package that holds both the best-fit value
and standard error.  A key feature of these ``uvalue`` attributes is that
they can be used in simple mathematical expressions (addition, subtraction,
multiplication, division, exponentiation) and propogate the uncertainties
to the result (ignoring correlations).
