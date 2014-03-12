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


The files for the examples shown here are all can be found in the
*examples/fitting* folder of the main Larch distribution.

.. _fit_example1_sec:

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
  create variable Parameters.  Two of the parameters have a lower bound
  set.   We also calculate the initial value for the model using the
  initial guesses for the parameter values.

  3. **define objective function for fit residual**: As above, this
  function will receive the group of fit parameters as the first argument,
  and may also receive other arguments as specified in the call to
  :func:`_math.minimize`.  This function returns the residual of the fit
  (data - model).

  4. **perform fit**.  Here we call :func:`_math.minimize`  with
  arguments of the objective function, the parameter group, and any
  additional positional arguments to the objective function (keyword/value
  arguments can also be supplied).   When this has completed, we calculate
  to model function with the final values of the parameters.

  5. **plot results**.   Here we plot the data, starting values, and the final
  fit.

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

.. _fig_fit1:

.. figure::  ../_images/fit_example1.png
    :target: ../_images/fit_example1.png
    :width: 65%
    :align: center

    Simple fit to mock data


Example 2: Fitting XANES Pre-edge Peaks
=========================================

This example extends on the previous one of fitting peaks.  Though
following the same basic approach (write an objective function, define
parameters, perform fit), we add several steps that you might use when
modeling real data:

   a) using data read in from a text file,

   b) using more lineshapes, here 3 peak-like functions and an
      error-function.


Consequently, the script is a bit longer:

.. literalinclude:: ../../examples/fitting/doc_example2a.lar

First, we read in the data and do some XAFS-specific preprocessing step.
Also note that we limit the range of the data from the full data set using
the ``index_of`` function.  The objective function ``resid()`` is very
simple, calling ``make_models()`` which creates the model of two Gaussian
peaks, an error function, and an offset.  There are 10 parameters for the
fit.  We're fitting the spectra with two Gaussian functions and an error
function.  It is often observed that if the centroids of peak functions such
as Gaussians are left to vary completely freely they tend to wander around
and give lousy fits, so here we place fairly tight controls on the
centroids.  We also place bounds on the amplitudes and widths of the peaks,
so they can't go too far astray.

The fit gives a report (ignoring correlations) like this::

    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 51, 10, 41
       nfev (func calls)   = 214
       chi_square          = 0.001194
       reduced chi_square  = 0.000029

    [[Variables]]
       amp1           =  0.078636 +/- 0.015419 (init=  0.250000)
       amp2           =  0.406155 +/- 0.044061 (init=  0.250000)
       cen1           =  7113.212401 +/- 0.074142 (init=  7113.250000)
       cen2           =  7115.571111 +/- 0.297302 (init=  7116.000000)
       erf_amp        =  0.375339 +/- 0.008897 (init=  0.500000)
       erf_cen        =  7122.242846 +/- 0.075486 (init=  7123.500000)
       erf_wid        =  0.289039 +/- 0.012431 (init=  0.500000)
       off            =  0.386845 +/- 0.009081 (init=  0.500000)
       wid1           =  0.489783 +/- 0.068186 (init=  0.600000)
       wid2           =  1.877520 +/- 0.166384 (init=  1.200000)
    =======================================================


and the plots of the resulting best-fit and components look like these:

.. subfigstart::

.. _fig-fit2a:

.. figure::  ../_images/fit_example2a1.png
    :target: ../_images/fit_example2a1.png
    :width: 100%
    :align: center
  
    fit with residual.

.. _fig-fit2b:

.. figure::  ../_images/fit_example2a2.png
    :target: ../_images/fit_example2a2.png
    :width: 100%
    :align: center

    fit with individual components.

.. subfigend::
    :width: 0.45
    :alt: a fig
    :label: fig-fit2
    
    Fit to Fe K-edge pre-edge and edge with 2 Gaussian functions 
    and an Error function.

and we see the fit is pretty good.  

Looking more closely, however, there is a hint in the data and the residual
that we may have missed a third peak at around E = 7122 eV.  We can add
this by simply adding another peak function to the ``make_models()``
function::

    def make_model(pars, data, components=False):
        """make model of spectra: 2 peak functions, 1 erf function, offset"""
        p1 = pars.amp1 * gaussian(data.e, pars.cen1, pars.wid1)
        p2 = pars.amp2 * gaussian(data.e, pars.cen2, pars.wid2)
        p3 = pars.amp3 * gaussian(data.e, pars.cen3, pars.wid3)

        e1 = pars.off + pars.erf_amp * erf( pars.erf_wid*(data.e - pars.erf_cen))
        sum = p1 + p2 + p3 + e1
        if components:
            return sum, p1, p2, p3, e1
        endif
        return sum
    enddef


and 3 more fitting parameters to the parameter group:

.. code-block:: python

    params = group(
        ...
        cen3 = param(7122.0, vary=True, min=7120, max=7124),
        amp3 = param(0.5,    vary=True, min=0),
        wid3 = param(1.2,    vary=True, min=0.05),
        ...)

The fit now has 13 variables, and gives a report like this::


    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 51, 13, 38
       nfev (func calls)   = 775
       chi_square          = 0.000103
       reduced chi_square  = 0.000003

    [[Variables]]
       amp1           =  0.080092 +/- 0.005012 (init=  0.250000)
       amp2           =  0.384458 +/- 0.017113 (init=  0.250000)
       amp3           =  0.111112 +/- 0.016366 (init=  0.500000)
       cen1           =  7113.234596 +/- 0.023044 (init=  7113.250000)
       cen2           =  7115.416637 +/- 0.136760 (init=  7116.000000)
       cen3           =  7122.300480 +/- 0.039187 (init=  7122.000000)
       erf_amp        =  0.476421 +/- 0.022186 (init=  0.500000)
       erf_cen        =  7123.374345 +/- 0.215044 (init=  7123.500000)
       erf_wid        =  0.230234 +/- 0.009485 (init=  0.500000)
       off            =  0.487636 +/- 0.022221 (init=  0.500000)
       wid1           =  0.496794 +/- 0.021434 (init=  0.600000)
       wid2           =  1.896698 +/- 0.064887 (init=  1.200000)
       wid3           =  0.614099 +/- 0.040220 (init=  1.200000)
    =======================================================


Adding the third peak here reduced :math:`\chi^2` by a factor of 10, from
0.0001194 to 0.0000103, and so seems to be a significant improvement.  The
values for the energy center and amplitude for the error function have both
moved significantly, as can be seen in the plots for this fit:

.. subfigstart::

.. _fig-fit3a:

.. figure::  ../_images/fit_example2b1.png
    :target: ../_images/fit_example2b1.png
    :width: 100%
    :align: center
  
    fit with residual.

.. _fig-fit3b:

.. figure::  ../_images/fit_example2b2.png
    :target: ../_images/fit_example2b2.png
    :width: 100%
    :align: center

    fit with individual components.

.. subfigend::
    :width: 0.45
    :label: fig-fit3
    
    Fit to Fe K-edge pre-edge and edge with 3 Gaussian functions 
    and an Error function.


Finally for this example, we can replace the Gaussian peak shapes with
other functional forms.   To use the Voigt function shown in the previous
section, we simply change ``make_models()`` to use::

    p1 = pars.amp1 * voigt(data.e, pars.cen1, pars.wid1)
    p2 = pars.amp2 * voigt(data.e, pars.cen2, pars.wid2)
    p3 = pars.amp3 * voigt(data.e, pars.cen3, pars.wid3)


The fit report now reads::

    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 51, 13, 38
       nfev (func calls)   = 441
       chi_square          = 0.000093
       reduced chi_square  = 0.000002

    [[Variables]]
       amp1           =  0.146617 +/- 0.012757 (init=  0.250000)
       amp2           =  0.445953 +/- 0.035927 (init=  0.250000)
       amp3           =  0.193669 +/- 0.032386 (init=  0.500000)
       cen1           =  7113.237795 +/- 0.020992 (init=  7113.250000)
       cen2           =  7115.912912 +/- 0.134734 (init=  7116.000000)
       cen3           =  7122.320641 +/- 0.037579 (init=  7122.000000)
       erf_amp        =  0.490162 +/- 0.023101 (init=  0.500000)
       erf_cen        =  7123.580458 +/- 0.227496 (init=  7123.500000)
       erf_wid        =  0.228310 +/- 0.008306 (init=  0.500000)
       off            =  0.497919 +/- 0.023158 (init=  0.500000)
       wid1           =  0.528196 +/- 0.027222 (init=  0.600000)
       wid2           =  1.676269 +/- 0.093116 (init=  1.200000)
       wid3           =  0.642993 +/- 0.047203 (init=  1.200000)
    =======================================================

and we see that the already very low
:math:`\chi^2` reduces by another 10%, which suggests a real improvement.
For completeness,  the plots from this fit look like this:


.. subfigstart::

.. _fig-fit4a:

.. figure::  ../_images/fit_example2c1.png
    :target: ../_images/fit_example2c1.png
    :width: 100%
    :align: center
  
    fit with residual.

.. _fig-fit4b:

.. figure::  ../_images/fit_example2c2.png
    :target: ../_images/fit_example2c2.png
    :width: 100%
    :align: center

    fit with individual components.

.. subfigend::
    :width: 0.45
    :label: fig-fit4
    
    Fit to Fe K-edge pre-edge and edge with 3 Voigt functions 
    and an Error function.


It's difficult to see a dramatic difference in fit quality for this data,
but the ability to explore fitting with different lineshapes like this is
still a useful test of the robustness of the fit.


Example 3: Fitting XANES Spectra as a Linear Combination of Other Spectra
==========================================================================

This example is quite a bit simpler than the previous one, though worth an
explicit example.  Here, we fit a XANES spectra as a linear combination of
two other spectra.  This approach is often used to compare an unknown
spectra with a large selection of candidate model spectra, taking the
result with lowest misfit statistics as the most likely results.  Though
this method should be used with some caution, it is a standard and very
simple approach to XANES analysis.


The example here is borrowed from Bruce Ravel's data and tutorials, and
based on the work published by :cite:ts:`Lengke2006`, The goal here is not
to repeat the whole of that analysis, but to present the mechanics of the
fitting approach.  Essentially, we're asserting that a particular measured
spectrum is made of a linear combination of 2 or more other spectra.  We
have a set of candidate model spectra, and we're going to try to determine
both which of those model spectra combine to match the measured one.  Here
we will simply assert that all the spectra are aligned in the ordinate and
that they are normalized in some reproducible way so that there are
essentially no artefacts or systematic problems in the 'x' or 'y' values of
the data.

For the example here, the spectra are held in individual ASCII data files,
which we'll call *unknown.dat* for the unknown spectrum and *s1.dat*,
*s2.dat*, ..., *s6.dat* for the spectra on 6 different standards. It is
not important for the discussion here what these spectra represent, but
they are XANES data taken at the Au L3 edge on various Au compounds.

A visual inspection of the spectra (see Figure :num:`fig-fit5`)
suggests that *s2* is probably a major component of the unknown, though the
peak around 11950 eV is a feature that only *s1* has, so it too may be an
important component.


.. subfigstart::

.. _fig-fit5a:

.. figure::  ../_images/fit_example3a.png
    :target: ../_images/fit_example3a.png
    :width: 100%
    :align: center
  
    components used for linear combinations.

.. _fig-fit5b:

.. figure::  ../_images/fit_example3b.png
    :target: ../_images/fit_example3b.png
    :width: 100%
    :align: center

    fit and residual with components *s1* and *s2*.

.. subfigend::
    :width: 0.45
    :label: fig-fit5
    
    Linear Combination Fit of gold XANES in cyanobacteria, after
    :cite:ts:`Lengke2006`.


To quantitatively fit these spectra, we read in all the data, and then
create a single group *dat* that will contain all the data we need.  It
turns out (and a common issue for XAFS data), the scans here do not have
identical energy values, so we both select a limited energy range, and
interpolate the standards onto the energy array of the unknown, and put all
these spectra into a single group:

.. literalinclude:: ../../examples/fitting/doc_example3/ReadData.lar


The initial fit to the unknown spectrum with spectra *s1* and *s2* looks
like this:

.. literalinclude:: ../../examples/fitting/doc_example3/fit1.lar


Here, we actually define a weight for all 6 spectra, but force 4 of them to
be 0.  For a two component fit, this would not be necessary, but we'll be
expanding this shortly.  We place bounds of [0, 1] on all the parameters,
and we use a constraint to ensure that the parameters add to 1.0.   Also
note that we define an uncertainty in the data that we use to scale the
``data - model`` returned by the fit.   This is somewhat arbitrarily chosen
to be 0.001, that is 0.1% of the typical data value.  The
results of this fit are::

    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 160, 1, 159
       nfev (func calls)   = 5
       chi_square          = 9339.070954
       reduced chi_square  = 58.736295

    [[Variables]]
       amp1           =  0.470660 +/- 0.004709 (init=  0.500000)
    [[Constraint Expressions]]
       amp2           =  0.529340 +/- 0.004709 = '1 - amp1'

    =======================================================


and the result for this fit is shown in Figure :num:`fig-fit5`.
This demonstrates the use of simple constraints for Parameters in fits:
we've used an algebraic expression to ensure that the weights for the two
components in the fit add to 1.

The fit here is not perfect, and we suspect there may be another standard
as a component to the fit.  But at this point, we have several candidate
spectra, and a pretty good starting fit, so the main questions are

  1. How do we know when one fit is better than another?
  2. Which combination gives the best results?

To answer the first question, we'll assert that "improved reduced
chi-square" is the best way to decide which of a series of fits is best.
To answer the second question, we'll work through all the possibilities.
Now, we set up a more complicated script to do 5 separate fits so that we
can compare the results.   This makes use of some of the more advanced
scripting features of larch:

.. literalinclude:: ../../examples/fitting/doc_example3/fit2.lar
   :language: python

There are several points worth noting here:

 a) We make a new copy of the Parameter Group for each fit -- this way we
    can (with some care) switch back and forth between fitting models.  Note
    that we add the non-Parameter ``note`` member to this group that give a
    brief description of the fit.  Of course, we could add anything else we
    wanted.

 b) We set ``amp1.vary`` and ``amp2.vary`` to ``True`` and set one of the
    other amplitude parameter's expression to ``1 - amp1 - amp2`` to impose
    the desired constraint.

 c) The loop over Parameter groups runs the fit for each set of
    Parameters, and checks for the lowest value of ``chi_reduced``.


The output of running this gives::

    chi_reduced         fit notes
    -------------------------------------
      58.7363   2 component fit:  s1, s2
      40.1796   3 component fit:  s1, s2, s3
      37.1932   3 component fit:  s1, s2, s4
      32.1411   3 component fit:  s1, s2, s5
      37.2007   3 component fit:  s1, s2, s6
    Best Fit:   3 component fit:  s1, s2, s5
    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 160, 2, 158
       nfev (func calls)   = 10
       chi_square          = 5078.292601
       reduced chi_square  = 32.141092

    [[Variables]]
       amp1           =  0.278665 +/- 0.017035 (init=  0.400000)
       amp2           =  0.532070 +/- 0.003491 (init=  0.400000)
    [[Constraint Expressions]]
       amp5           =  0.189264 +/- 0.016438 = '1 - amp1 - amp2'

    [[Correlations]]     (unreported correlations are <  0.100)
       amp1, amp2           = -0.270
    =======================================================


and the output plots for the best model look like this:

.. subfigstart::

.. _fig-fit6a:

.. figure::  ../_images/fit_example3c1.png
    :target: ../_images/fit_example3c1.png
    :width: 100%
    :align: center
  
    linear combination fit and residual.

.. _fig-fit6b:

.. figure::  ../_images/fit_example3c2.png
    :target: ../_images/fit_example3c2.png
    :width: 100%
    :align: center

    weighted contribution from individual components.

.. subfigend::
    :width: 0.45
    :label: fig-fit6
    
    Linear Combination XANES Fit of gold components in cyanobacteria with
    species *s1*, *s2*, and *s5*.



Of course, we aren't necessarily done here as we haven't exhausted all
possible combinations of components.  Included in the examples
(*examples/fitting/doc_examples3/fit3.lar*), but not reprinted here, is a
script that runs through all possible combinations of 3 and 4 components,
though still assuming that *s1* and *s2* are components.


The output gives this::

    chi_reduced         fit notes
    -------------------------------------
      58.7363   2 component fit:  s1, s2
      40.1796   3 component fit:  s1, s2, s3
      37.1932   3 component fit:  s1, s2, s4
      32.1411   3 component fit:  s1, s2, s5
      37.2007   3 component fit:  s1, s2, s6
      59.2220   4 component fit:  s1, s2, s3, s4
      14.7269   4 component fit:  s1, s2, s3, s5
      13.3452   4 component fit:  s1, s2, s3, s6
      30.1274   4 component fit:  s1, s2, s4, s5
      32.3537   4 component fit:  s1, s2, s5, s6
      34.3471   4 component fit:  s1, s2, s4, s6
    Best Fit:   4 component fit:  s1, s2, s3, s6
    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 160, 3, 157
       nfev (func calls)   = 22
       chi_square          = 2095.190450
       reduced chi_square  = 13.345162

    [[Variables]]
       amp1           =  0.327883 +/- 0.009491 (init=  0.400000)
       amp2           =  0.465013 +/- 0.005625 (init=  0.400000)
       amp3           =  0.063834 +/- 0.003834 (init=  0.000000)
    [[Constraint Expressions]]
       amp6           =  0.143270 +/- 0.008020 = '1 - amp1 - amp2 - amp3'

    [[Correlations]]     (unreported correlations are <  0.100)
       amp2, amp3           = -0.890
       amp1, amp2           = -0.340
    =======================================================

You might notice that, whereas the 3 component fit favored adding *s5*, the
four component fit favors *s3* and *s6*.  You might further notice that the
four component fit with *s3* and *s5* has reduced chi-square of 14.7, only
slightly worse than the best value.  For completeness, the parameters for
that are::

    larch> print fit_report(pars[6])
    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 160, 3, 157
       nfev (func calls)   = 18
       chi_square          = 2312.121664
       reduced chi_square  = 14.726890

    [[Variables]]
       amp1           =  0.303043 +/- 0.011665 (init=  0.400000)
       amp2           =  0.458358 +/- 0.005875 (init=  0.400000)
       amp3           =  0.054293 +/- 0.003941 (init=  0.000000)
    [[Constraint Expressions]]
       amp5           =  0.184307 +/- 0.011130 = '1 - amp1 - amp2 - amp3'

    [[Correlations]]     (unreported correlations are <  0.100)
       amp2, amp3           = -0.916
       amp1, amp2           = -0.247
       amp1, amp3           =  0.152
    =======================================================


The plots resulting from both sets of Parameters are shown:


.. subfigstart::

.. _fig-fit7a:

.. figure::  ../_images/fit_example3d1.png
    :target: ../_images/fit_example3d1.png
    :width: 100%
    :align: center
  
    linear combination fit and residual.

.. _fig-fit7b:

.. figure::  ../_images/fit_example3d2.png
    :target: ../_images/fit_example3d2.png
    :width: 100%
    :align: center

    weighted contribution from individual components.

.. subfigend::
    :width: 0.45
    :label: fig-fit7
    
    Linear Combination XANES Fit of gold components in cyanobacteria
    with species *s1*, *s2*, *s3*, and *s6*.


.. subfigstart::

.. _fig-fit8a:

.. figure::  ../_images/fit_example3e1.png
    :target: ../_images/fit_example3e1.png
    :width: 100%
    :align: center
  
    linear combination fit and residual.

.. _fig-fit8b:

.. figure::  ../_images/fit_example3e2.png
    :target: ../_images/fit_example3e2.png
    :width: 100%
    :align: center

    weighted contribution from individual components.

.. subfigend::
    :width: 0.45
    :label: fig-fit8
    
    Linear Combination XANES Fit of gold components in cyanobacteria
    with species *s1*, *s2*, *s3*, and *s5*.


From the plots alone, it is difficult to tell which of these fits is
better, and it is probably best to say that these are both good fits.  This
implies that component *s3* is important even if at a very small fraction,
and that either component *s5* or *s6* (which aren't that different
spectroscopically or chemically (see Figure :num:`fig-fit5`) is present.
Of course, the analysis here is not meant to be definitive, and there are
many more checks that could be done.  To be clear, :cite:ts:`Lengke2006`
looked at many more unknown spectra, and also adjusted the energy ranges of
the fits, and concludedd that *s1*, *s2*, *s3*, and *s5* were the best
components, with concentrations of the components very similar to the ones
found here.
