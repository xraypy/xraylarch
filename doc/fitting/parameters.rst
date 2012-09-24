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

     ============== ===================== ============= =============================
      attribute      meaning               default       set by which functions:
     ============== ===================== ============= =============================
      value          value                               :func:`param`
      vary           can change in fit    ``False``      :func:`param`
      min            lower bound          ``None``       :func:`param`
      max            upper bound          ``None``       :func:`param`
      name           optional name        ``None``       :func:`param`
      expr           algebraic constraint ``None``       :func:`param`
      stderr         uncertainty           --            :func:`minimize`
      correl         correlations          --            :func:`minimize`
     ============== ===================== ============= =============================

..  function:: guess(value, min=None, max=None, expr=None)

    define a variable Parameter, setting some of it principle attributes.
    The arguments here are identical to :func:`param`, except that
    ``vary=True`` is set.

Simple examples for creating a parameter and creating an group of
parameters would be::

    # create some Parameters
    p1 = param(5.0)
    p2 = params(10, min=0, max=100, vary=True)
    p3 = param(expr='1 - sqrt(p2**2)')

    # create a Group of parameters
    fit_params = group(p1 = p1, p2 = p2, p3 = p3,
                       centroid = param(99, vary=False),
                       amp = guess(3, min=0))

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

algebraic constraints
~~~~~~~~~~~~~~~~~~~~~~

It is often useful to be able to build a fitting model in which Parameters
in the model are related to one another.  As a simple example, it might be
useful to fit a spectrum with a sum of two lineshapes that have different
centroids, but the same width.  As a second example, it might be useful to
fit a spectrum to a sum of two model spectra where the relative weight of
the model spectra must add to 1.  For each of these cases, one could write
a model function that implemented such constraints.

Rather than trying to capture and encourage such special cases, Larch takes
a more general approach, allowing Parameters to get their value from an
algebraic expression.  Thus, one might define an objective function for a
sum of two Gaussian functions (discussed in more detail in
:ref:`lineshape-functions-label`), as::

    def fit_2gauss(params, data):
        model = params.amp1 * gaussian(data.x, params.cen1, params.wid1) + \
                params.amp2 * gaussian(data.x, params.cen2, params.wid2)
        return (data.y - model)
    enddef

This is general and does not put any relations between the parameter values
within the objective function.  But one can place such relations in the
definitions of the parameters and have them obeyed within the fit.  That
is, one could constrain the two widths of the Gaussians to be the same
value with::

    params.wid1 = guess(1, min=0)
    params.wid2 = param(expr='wid1')

and the value of `params.wid2` will have the same value as `params.wid1`
every time the objective is called, but won't be an independent variable in
the fit.  As a second  example, one could constrain the two amplitude
parameters to add to 1 and each be between 0 and 1 as::

    params.amp1 = guess(0.5, min=0, max=1)
    params.amp2 = param(expr='1 - amp1')

of course, one can use more complex expressions -- any valid Larch
expression is allowed.


**Namespaces for algebraic expressions**

It's worth asking what variables and functions are available for writing
algebraic constraints.  The discussion on :ref:`tut-namespaces-label`
gives a partial explanation, but we'll be a bit more explicit here.
During a fit, the *paramgroup* given to :func:`minimize` will be assigned
to `_sys.paramGroup` and will be the first place variables are looked for.
The variables defined inside the objective function will be in
`_sys.localGroup`, and which will also be searched for variables.  After
that, names are looked up with the normal procedures.  In essence, this
means that the variables and functions available for algebraic expressions
during a fit include

1. First, all the other Parameters (and any other variables) defined in the
*parameter group* for a fit.

2. All the variables defined in the objective function, including those
passed in via the argument list.

3. All the normal functions and variable names available in Larch,
including all the mathematical functions.

As we said, `_sys.paramGroup` is set during a fit, by :func:`minimize`.  It
is left set at the end of the fit -- it is not cleared or reset.  However,
note that `_sys.paramGroup` may be unset or set to the wrong group (say,
from a previous fit) when setting up a new fit (before you call
:func:`minimize`).  Of course, you can explicitly assign a group to
`_sys.paramGroup` when setting up a fit, so that you might be able to
sensibly call the objective function yourself, prior to doing a
minimization.


