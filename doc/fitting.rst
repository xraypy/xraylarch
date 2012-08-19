===========================================
Fitting and Modeling Data with Larch
===========================================

A key motivation for Larch is to provide easy and robust ways to model data
and perform complex fits of data to models.  Data modeling and fitting can
be messy and challenging tasks, so a major factor in Larch's design was to
make this as simple as possible.  This chapter discusses the basic concepts
for building models, setting up and performing fits, and inspecting the
results.


.. module:: _math


The concepts presented here focus on modeling and fitting of general
spectra.  Of course, Larch can provides other, specific functions for doing
fits, such as the EXAFS procedures :func:`_xafs.autobk` and
:func:`_xafs.feffit`.  Many of these concepts (and the underlying fitting
algorithms) are used for those other functions as well.


Fitting Overview
==================

Modeling and fitting of experimental data is a key need for the analysis of
most scientific data.  There is an extensive literature on these topics,
with a wealth written on both the theoretical and practical aspects of
modeling data.  One of the more common and general approaches is to use a
least-squares analysis, in which a model is adjusted until it matches
experimental data such that the sum of squares of the difference between
data and model is as small as possible.  Mathematically, this is expressed
as

.. math::

    S = \sum_{i=1}^{N} \big[{y_i - f(x_i, \bf{\beta}) } \big]^2

where the experimental data is expressed as :math:`\bf{y}(\bf{x})` that is
discretely sampled at :math:`N` points, :math:`f(\bf{x}, \bf{\beta})` is a
model function, and :math:`\bf{\beta}` is a set of adjustable parameters in
the model.  For a simple linear model of data, for example, :math:`f =
\beta_0 + \beta_1 \bf{x}`, but the model can be arbitrary complex.  There
is good statistical justification for using this approach, and many
existing tools for helping to find the minimal values of :math:`S`.  These
justifcations are not without criticism or caveats, but we'll leave that
aside for now.

It is common to include a multiplicative factor to each component in in the
least-squares equation above, so that the different data points might be
given more or less weight.  Again, there are several approaches to this,
with one of the most common approaches to weight by the inverse of the
estimated uncertainty in the data value.  This then what is generally
called the chi-square goodness-of-fit parameter


.. math::

    \chi^2 = \sum_{i=1}^{N} \big[\frac{y_i - f(x_i, \bf{\beta})}{\epsilon_i} \big]^2

Here, :math:`\epsilon_i` represents the uncertainty in the value of :math:`y_i`.

As mentioned, the model function can be fairly complex. There is a large
literature on the cases where the model function :math:`f(\bf{x},
\bf{\beta})` depends linearly on its parameters :math:`\bf{\beta}`.  More
generally, the model function will not depend linearly on its parameters,
and the minimization is generally referred to a ''non-linear least-squares
optimization'' in the literature.  All the discussion here will assume that
the models can be non-linear.


It is convenient to define the **residual function**  as

.. math::

     r = \frac{y - f(x, \bf{\beta})}{\epsilon}


so that the sum to be minimized is a simple sum of this function, :math:`s
= \sum_i^{N} r_i^2`.   The fitting process can then be made very general
with a few key components required.  Specifically, for Larch, the
requirements are

  1. A set of Parameters, :math:`{\bf{\beta}}`, that are used in the model,
  and are to be adjusted to find the least-square value of the sum of
  squares of the residual.  These must be **parameters** (discussed below)
  that are held in a single **parameter group**.  That group can contain
  other data.

  2. An **objective function** to calculate the residual function.  This
  will be a Larch function that takes the **parameter group** described
  above as its first argument, and an unlimited set of optional arguments.
  The arrays for the data should passed in by these optional arguments.
  This function should return the residual array, :math:`r` that will be
  minimized in the least-squares sense.

After the fit has completed, several statistical results describing the fit
quality and the values and uncertainties found for the parameters will be
available.  Though the description so far as been somewhat formal, the
process is not as hard as it sounds, and all the topics will be discussed
in more detail below.

As mentioned above, the objective function needs to follow fairly strict
guidelines.  The first argument must be a Larch group, and the return value

Parameters
===============

The parameters used in the fitting model are all meant to be continuous
variables -- floating point numbers.  In general, the fitting procedure may
assign any value to any parameter.  In an actual fit, you may want to place
some restrictions on the value a parameter can take.  For example, if
you're fitting data to a line, you may want to ensure that the slope of the
line is positive.  For more complex cases, you might want to write a a
general model describing the data, but keep some of the parameters in the
model fixed.

In Larch, a **Parameter** is a fundamental data type.  It is an object with
many attributes, the most important of which is a ``value``.  A Parameter's
value can change of course -- this is what will happen during a fit or
refinement process.  A Parameter can have many other attributes as well, as
we'll discuss throughout this section.  In most cases, a Parameter can be
used as a floating point number, and its value will be used.

To create a Parameter, use the :func:`param` function, which takes a value
as its first argument, and a few optional keyword arguments to control
whether the value should be varied in a fit or kept fixed, and setting
optional upper and lower bounds for the Parameter value.  In addition, an
algebraic expression can be specified to create a **constrained Parameter**.

..  function:: param(value, vary=False, min=None, max=None, expr=None)

    define a Parameter, setting some of it principle attributes

    :param value:  floating point value.  This value may be adjusted during a fit.
    :param vary:   flag telling whether Parameter is to be varied during a  fit (``True``, ``False``) [``False``]
    :param min:    minimum value the Parameter can take.
    :param max:    maximum value the Parameter can take.
    :param expr:   algebraic expression for a constrained Parameter.  See :ref:`param-constraints-label`  for details.

..  function:: guess(value, min=None, max=None, expr=None)

    define a variable Parameter, setting some of it principle attributes.
    The arguments here are identical to :func:`param`, except that
    ``vary=True`` is set.

A simple example for creating


setting bounds
~~~~~~~~~~~~~~~

..  _param-constraints-label:

algebraic constraints
~~~~~~~~~~~~~~~~~~~~~~



Objective Function and minimize
================================

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

Here ``params`` is a Larch group containing two Parameters (as defined by
:func:`_math.param`, which we'll discuss in more detail in the next
section).  The objective function ``residual`` will take


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

Fit Results and Outputs
============================

After the fit has completed, several statistics are output and available to
describe the quality of the fit and the estimated values for the Parameter
values and uncertainties.  The main statistics are written to *paramgroup*.

The estimated values, uncertainties, and correlations for each varied
Parameter are written as attributes of that Parameter.  Thus, after a fit,
each variable Parameter ``par`` will be updated so that ``par.value`` will
hold the estimated best-fit value, ``par.stderr`` will hold the estimated
uncertainty (1-:math:`\sigma` standard error), and ``par.correl`` will hold
a dictionary of correlation values with the other variable Parameters.

General Fit statistics describing the quality of the fit and details about
how the fit proceeded will be put into components of *paramgroup*, with
variable names and meanings as outlines in :ref:`Table of Fit Statistics <minimize-stats_table>`.
For advanced users, the full residual vector, covarance matrix, and
jacobian matrix from the fit, as well as several more esoteric outputs from
MINPACK's lmdif function are put in *paramgroup.lmdif*.

.. _minimize-stats_table:

   Table of Fit Statistics.
   Listed are the name of the variable added to the fit *paramgroup*, and
   the statistical quantity it holds.

    ==================== ===================================
     *attribute*             *statistical quantity*
    ==================== ===================================
     chi_square             :math:`\chi^2`
     reduced_chi_square     :math:`\chi_\nu^2`
    ==================== ===================================



Some Builtin Line-shape Functions
==================================

Larch provides a number of convenience functions for common line-shapes
used in fitting of experimental data.  This list is not exhaustive, but can
be amended easily.

.. function:: gaussian(x, cen=0, sigma=1)

   a Gaussian or normal distribution function:

.. math::

  f(x, \mu, \sigma) = \frac{1}{\sigma\sqrt{2\pi}} e^{[{-{(x-\mu)^2}/{{2\sigma}^2}}]}

where *cen* is used for :math:`\mu`.

.. function:: lorentzian(x, cen=0, sigma=1)

   a Lorentzian or Cauchy-Lorentz distribution function:

.. math::

  f(x, \mu, \sigma) = \frac{1}{\pi} \big[\frac{\sigma}{(x - \mu)^2 + \sigma^2}\big]

where *cen* is used for :math:`\mu`.

.. function:: voigt(x, cen=0, sigma=1, gamma=None)

   a Voigt distribution function.   There seem to be many variant
   definitions -- the one used here is given as

.. math::

    f(x, \mu, \sigma, \gamma) = \frac{\textrm{Re}[w(z)]}{\sigma\sqrt{2 \pi}}

where

.. math::
   :nowrap:

   \begin{eqnarray*}
     z &=& \frac{x-\mu +i\gamma}{\sigma\sqrt{2}} \\
     w(z) &=& e^{-z^2}{\operatorname{erfc}}(-iz)
   \end{eqnarray*}

and :func:`erfc` is the complimentary error function.
As above,  *cen* is used for :math:`\mu` here.
If *gamma* is left as ``None``, it is set equal to *sigma*.


.. function:: pvoigt(x, cen=0, sigma=1, frac=0.5)

   a pseudo-Voigt distribution function, which is a weighted sum of a
   Gaussian and Lorentzian function with the same values for *cen*
   (:math:`\mu`) and *sigma* (:math:`\sigma`), and *frac* setting the
   Lorentzian fraction::

    pvoigt(x, cen, sigma, frac) = (1-frac)*gaussian(x, cen, sigma) + frac*lorentzian(x, cen, sigma)


.. function:: pearson7(x, cen=0, sigma=1, expon=0.5)

   a Pearson-7 lineshape.  This is another Voigt-like distribution
   function, defined as

.. math::

    f(x, \mu, \sigma, p) = \frac{s}{\big\{[1 + (\frac{x-\mu}{\sigma})^2] (2^{1/p} -1)  \big\}^p}


where for *cen* (:math:`\mu`) and *sigma* (:math:`\sigma`) are as for the
above lineshapes, and *expon* is :math:`p`, and

.. math::

    s = \frac{\gamma(p) \sqrt{2^{1/p} -1}}{ \sigma\sqrt{\pi}\,\gamma(p-1/2)}

where :math:`\gamma(x)` is the gamma function.


Several builtin special functions can also be used to create lineshapes
useful in fitting spectra and other x-ray data.  Some of these are detailed
in the :ref:`Table of Useful Line shapes <fit-funcs_table>`.

.. _fit-funcs_table:

    Table of Useful Line shapes.

    ================================= ======================================
     *function*                         *description*
    ================================= ======================================
    gaussian(x, cen, sigma)           Gaussian, normal distribution.
    lorentzian(x, cen, sigma)         Lorentzian distribution
    voigt(x, cen, sigma, gamma)       Voigt function
    pvoigt(x, cen, sigma, frac)       pseudo-Voigt function
    pearson7(x, cen, sigma, expon)    Pearson-7 function
    arctan(x)                         Arc-tangent function
    erf(x)                            Error function
    erfc(x)                           Complemented Error function (1-erf(x)
    gammaln(x)                        log of absolute value of gamma(x)
    ================================= ======================================


Other standard special functions (Bessel functions, Legendre polynomials,
etc) can be accessed from scipy.special::

    from scipy.special import j0 # Bessel function of order 0,
    from scipy.special import y1 # Bessel function of second kind of order 1

A host of functions to generate other distribution functions (Pareto,
Student's T, etc) can be accessed from scipy.stats.


Example 1: Fitting a Simple Gaussian
======================================


Here we make a simple mock data set and fit a Gaussian function to it.
Though a fairly simple example, it touches on all the concepts discussed
above, and is a reasonable representation of the sort of analysis actually
done when modeling many kinds of data.  The script to do the fit looks like
this::

    # create mock data
    mdat = group()
    mdat.x = linspace(-10, 10, 201)
    mdat.y = 1.0 + 12.0 * gaussian(mdat.x, 1.5, 2.0) + \
             random.normal(size=len(mdat.x), scale=0.050)

    # create a group of fit parameters
    params = group(off = guess(0),
                   amp = guess(5, min=0),
		   cen = guess(2),
		   wid = guess(1, min=0))

    init = params.off + params.amp * \
                gaussian(mdat.x, params.cen, params.wid)

    # define objective function for fit residual
    def resid(p, data):
        return data.y - (p.off + p.amp * gaussian(data.x, p.cen, p.wid))
    enddef

    # preform fit
    minimize(resid, params, args=(mdat,))

    final = params.off + params.amp * \
                gaussian(mdat.x, params.cen, params.wid)

    # plot results
    newplot(mdat.x, mdat.y, label='data', show_legend=True)
    plot(mdat.x, init, label='initial', color='black', style='--')
    plot(mdat.x, final, label='final', color='red')

    # print report of parameters, uncertainties
    print fit_report(params)


This fitting script consists  of several components, which we'll go over in
some detail.

  1 **create mock data**:  Here we use the builtin :func:`_math.gaussian`
  function to create the model function.  We also add simulated noise to
  the model data with the :func:`random.normal` function from numpy.

  2. **create a group of fit parameters**:  Here we create a group with
  several components, all defined by the :func:`_math.guess` function to
  create variable Parameters.  Two of the variables here have a lower bound
  set.   We also calculate the initial value for the model using the
  initial guesses for the parameter values.

  3. **define objective function for fit residual**: As above, this
  function will receive the group of fit parameters as the first argument,
  and may also receive other arguments as specficied in the call to
  :func:`_math.minimize`.  This function returns the residual of the fit
  (data - model).

  4. **perform fit**.  Here we call :func:`_math.minimize`  with
  arguments of the objective function, the parameter group, and any
  additional positional arguments to the objective function (keyword/value
  arguments can also be supplied).   When this has completed, we calculate
  to model function with the final values of the parameters.

  5. **plot results**.   Here we plot the data, initial, and final fits.

  6. **print report of parameters, uncertainties**.  Here we print out a
  report of the fit statistics, best fit values, uncertainties and
  correlations between variables.

The printed output from ``fit_report(params)`` will look like this::

    ===================== FIT RESULTS =====================
    [[Statistics]]
       npts, nvarys       = 201, 4
       nfree, nfcn_calls  = 197, 26
       chi_square         = 0.545081
       reduced chi_square = 0.002767

    [[Variables]]
       amp            =  11.973425 +/- 0.067265   (init=  5.000000)
       cen            =  1.511988 +/- 0.008168   (init=  2.000000)
       off            =  1.002578 +/- 0.004996   (init=  0.000000)
       wid            =  1.996553 +/- 0.010843   (init=  1.000000)

    [[Correlations]]    (unreported correlations are <  0.100)
       amp, wid             =  0.690
       amp, off             = -0.670
       off, wid             = -0.462
    =======================================================


And the plot of data and fit will look like this::

<include graphic here>


Example 3: Fitting XANES Pre-edge Peaks
=========================================

This

Example 2: Fitting XANES Spectra as a Linear Combination of Other Spectra
==========================================================================

In this example, which is much simpler than the previous one, we fit a
XANES spectra as a linear combination of two other spectra. It is often
used to compare an unknown spectra with a large selection of candidate
model spectra, taking the result with lowest misfit statistics as the most
likely results.  Though it should be used with some caution, this
represents a standard and very simple approach to XANES analysis. In the
example here we only do the fit with a single pair of candidate spectra.
Extending to more model spectra is left as an exercise for the reader.
Other possible variations include fiting the derivatives or other spectral
decompositions of the spectra.

For the analysis here, we have unknown spectra X and two model spectra A
and B.  first put all the data onto the same ordinate (energy) array.  This
does not necessarily need to be a uniform energy grid.  We then use a
Parameter group with two parameters.  The first of these is the amplitude
for model spectra A, which is set to vary and have a minimum value of 0 and
a maximum of 1.  The second parameter is the amplitude for model spectra B,
which is constrained to be '1 - ampA'.







