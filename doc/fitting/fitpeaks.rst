================================================
Simplified Peak Fitting with :func:`fit_peak`
================================================

.. module:: _math

As shown in the previous sections, it is pretty simple to use Larch's
fitting mechanism to set up and perform fits to data.  In fact, it is
pretty commom to need to fit data to simple line-shapes, as when setting up
an experiment.  In an effort to make life easier, in addition to providing
a fairly easy general-purpose fitting function, Larch provides a
:func:`fit_peak` function to fit one dimensional data to one of several
lineshapes.


.. function:: fit_peak(x, y, model, dy=None, background=None, step=None)

    fit the data y at points x with a function described by model,
    optionally including uncertainties in y, a background polynomial, and a
    choice of step functions.

    :param x:      array of values at which to calculate model
    :param y:      array of values for model to try to match
    :param model:  name of model for functional form to use.  See
                   :ref:`Table of fit_peak models <fit_peak_models_table>`.
    :param dy:         optional array of values for uncertainty in y data to be matched.
    :param background:  name of background model to use. One of (case insensitive)
                        None (no background), 'constant', 'linear', or 'quadratic'.
                        This is ignored when model is 'linear' or 'quadratic'
    :param step:        name of step model to use for 'step' and 'rectangle' models.
                        One of (case insensitive): 'linear', 'erf', or 'atan'

    :returns:      a Group containing fit parameters, best-fit and
                   background functions, as detailed in
                   :ref:`Table of fit_peak group members <fit_peak_output_table>`.

The optional background function

.. _fit_peak_models_table:

   Table of :func:`fit_peak` models.

    The following functional models are supported for fitting with
    :func:`fit_peak`.

    ============= =========================== =========================================
     model          Description                parameter names
    ============= =========================== =========================================
     linear         :math:`y = mx + b`         offset, slope
     quadratic      :math:`y = a + bx + cx^2`  offset, slope, quad
     step           step function              height, center, width
     rectangle      step up, step down         height, center1, width1, center2, width2
     exponential    :math:`y = Ae^{-x/b}`      amplitude, decay
     gaussian       Gaussian                   amplitude, center, sigma
     lorentzian     Lorenztian                 amplitude, center, sigma
     voigt          Voigt (with gamma=sigma)   amplitude, center, sigma
    ============= =========================== =========================================

The *sigma* and *width* parameters will have a minimum value of 0.  For all
models except *linear* and *quadratic*, an optional background can be
included, which (depending on the form chosen) will add parameters named
*bkg_offset*, *bkg_slope*, and *bkg_quad*.


.. _fit_peak_output_table:

   Table of members of group returned by :func:`fit_peak`.


    ============= =================================================================
     member         Description
    ============= =================================================================
     x              copied from input x data
     y              copied from input y data
     model          name of model used
     background     name of background models used
     step           name of step model used
     params         Group of fit parameters, as sent to and from :func:`minimize`
     fit            final best fit to y data, including background if used.
     fit_init       initial guess of fit to y data,  including background if used.
     bkg            final background function, if used.
     bkg_init       initial background function, if used.
    ============= =================================================================



Example: Fitting a Gaussian + background with :func:`fit_peak`
=================================================================

As in the earlier example, here we make a simple mock data set and fit a
Gaussian function to it, only do it in many fewer steps:

.. literalinclude:: ../../examples/fitting/doc_example_fitpeak1.lar

Here we simply create mock data that's fairly noisy, and ask it to be fit
to Gaussian, including a linear background, with a single command.  We then
plot the results and print the report of parameters.  Note that the fit is
pretty good at finding the peak center and shape, even though the model is
not strictly correct.

The printed output from ``fit_report(params)`` will look like this::

    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 51, 5, 46
       nfev (func calls)   = 138
       chi_square          =  0.764614
       reduced chi_square  =  0.016622

    [[Variables]]
       amplitude      =  97.066621 +/- 2.091332 (init=  26.864630)
       bkg_offset     =  8.188188 +/- 0.040926 (init=  5.484111)
       bkg_slope      = -0.025568 +/- 0.000631 (init=  0.000000)
       center         =  44.307329 +/- 0.145076 (init=  44.000000)
       sigma          =  5.238662 +/- 0.111549 (init=  15.000000)
    [[Constraint Expressions]]
       fwhm           =  12.336107 +/- 0.262679 = '2.354820*sigma'

    [[Correlations]]     (unreported correlations are <  0.500)
       bkg_offset, bkg_slope = -0.826
       amplitude, sigma     =  0.675
    =======================================================

And the plot of data and fit will look like this:

.. _fitting_fig1:

  .. image:: ../images/fit_peakfit1.png
     :target: ../_images/fit_peakfit1.png
     :width: 65 %

  Figure 1.  Simple fit to mock data using :func:`fit_peak`

The main point here is not just that the fit is good, but that it was
accomplished so simply, with a single line of code.

Example: Fitting a Rectangular function with :func:`fit_peak`
================================================================

Here, we simulate data that might represent a line-up scan at a beamline.
The fit is to a function that takes a step up and a step down.

.. literalinclude:: ../../examples/fitting/doc_example_fitpeak2.lar

