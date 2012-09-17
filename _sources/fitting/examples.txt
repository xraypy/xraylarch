==============
Fit Examples
==============

This section contains a few illustrative fitting examples.  As mentioned
earlier, the important pieces to have for a fit are:

1. a *Parameter Group*: a group that contains all the parameters (both
truly variable parameters as well as any constrained parameters) for the
fit.

2. an *Objective Function* that takes the Parameter Group as the first
argument, and returns an array to be minimized in the least-squares sense.


Example 1: Fitting a Simple Gaussian
======================================


Here we make a simple mock data set and fit a Gaussian function to it.
Though a fairly simple example, and one that is guaranteed to work well, it
touches on all the concepts discussed above, and is a reasonable
representation of the sort of analysis actually done when modeling many
kinds of data.  The script to do the fit looks like this:

.. literalinclude:: ../../examples/fitting/doc_example1.lar


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
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 201, 4, 197
       nfev (func calls)   = 26
       chi_square          = 0.498818
       reduced chi_square  = 0.002532
     
    [[Variables]] 
       amp            =  12.102080 +/- 0.122022 (init=  5.000000)
       cen            =  1.476801 +/- 0.016932 (init=  2.000000)
       off            =  0.996424 +/- 0.006977 (init=  0.000000)
       wid            =  2.022030 +/- 0.016608 (init=  1.000000)
     
    [[Correlations]]     (unreported correlations are <  0.100)
       amp, off             = -0.861 
       amp, wid             =  0.808 
       off, wid             = -0.692 
    =======================================================


And the plot of data and fit will look like this:


.. image:: ../images/fit_example1.png
   :width: 80 %


Example 2: Fitting XANES Pre-edge Peaks
=========================================

This example extends the previous one by a) using data read in from a text
file, b) using many more lineshapes, c) setting bounds on parameters, and
d) using a simple algebraic constraint.   The basic format of the above
exmple is followed, but the script is a bit longer.




Example 3: Fitting XANES Spectra as a Linear Combination of Other Spectra
==========================================================================

This example is simpler than the previous one, though still worth an
explicit example.  Here, we fit a XANES spectra as a linear combination of
two other spectra. It is often used to compare an unknown spectra with a
large selection of candidate model spectra, taking the result with lowest
misfit statistics as the most likely results.  Though it should be used
with some caution, this represents a standard and very simple approach to
XANES analysis. In the example here we only do the fit with a single pair
of candidate spectra.  Extending to more model spectra is left as an
exercise for the reader.  Other possible variations include fiting the
derivatives or other spectral decompositions of the spectra.

For the analysis here, we have unknown spectra X and two model spectra A
and B.  first put all the data onto the same ordinate (energy) array.  This
does not necessarily need to be a uniform energy grid.  We then use a
Parameter group with two parameters.  The first of these is the amplitude
for model spectra A, which is set to vary and have a minimum value of 0 and
a maximum of 1.  The second parameter is the amplitude for model spectra B,
which is constrained to be '1 - ampA'.







