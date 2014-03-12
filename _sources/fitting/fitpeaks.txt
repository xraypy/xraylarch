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


.. function:: fit_peak(x, y, model, dy=None, background=None, step=None, negative=False, use_gamma=False)

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
    :param negative:    boolean for whether peak or steps are expected to
                        go down (default ``False``)
    :param use_gamma:   boolean for whether to use separate gamma parameter for
                       'voigt' model (default ``False``).

    :returns:      a Group containing fit parameters, best-fit and
                   background functions, as detailed in
                   :ref:`Table of fit_peak group members <fit_peak_output_table>`.

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

The *sigma* and *width* parameters will have a minimum value of 0.

For all models except *linear* and *quadratic*, an optional background can
be included, which (depending on the form chosen) will add parameters named
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

As in the :ref:`Example in the previous section <fit_example1_sec>`, we
make a simple mock data set and fit a Gaussian function to it. Here we also
add a linear background, and do the whole fit with a single function,
instead of a dozen or so lines of code used before:

.. literalinclude:: ../../examples/fitting/doc_example_fitpeak1.lar

Here we first create mock data that's fairly noisy, and ask it to be fit
to Gaussian, including a linear background, with a single command.  We then
plot the results and print the report of parameters.  Note that the fit is
pretty good at finding the peak center and shape, even though the model is
not strictly correct.

The printed output from ``fit_report(params)`` will look like this::

    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 51, 5, 46
       nfev (func calls)   = 160
       chi_square          =  0.741381
       reduced chi_square  =  0.016117

    [[Variables]]
       amplitude      =  110.316958 +/- 1.724332 (init=  35.002462)
       bkg_offset     =  8.128759 +/- 0.038694 (init=  5.450067)
       bkg_slope      = -0.026001 +/- 0.000614 (init=  0.000000)
       center         =  44.303784 +/- 0.088638 (init=  44.000000)
       sigma          =  4.173981 +/- 0.066834 (init=  15.000000)
    [[Constraint Expressions]]
       fwhm           =  9.828974 +/- 0.157382 = '2.354820*sigma'

    [[Correlations]]     (unreported correlations are <  0.300)
       bkg_offset, bkg_slope = -0.834
       amplitude, sigma     =  0.651
       amplitude, bkg_offset = -0.412
    =======================================================

And the plot of data and fit will look like this:

.. _fig-fitpeak1:

.. figure::  ../_images/fit_peakfit1.png
    :target: ../_images/fit_peakfit1.png
    :width: 65%

    Simple fit to mock data using a Gaussian model and a linear background
    with the :func:`fit_peak` function.

Although the fit is quite good, the model is probably imperfect, and using
a Voigt function to fit to this data would give better results.  The main
point here is not just that the fit is good, but that it was accomplished
with a single line of code.

Example: Fitting a Rectangular function with :func:`fit_peak`
================================================================

Here, we simulate data that might represent a line-up scan at a beamline.
The fit is to a function that takes a step up and a step down.

.. literalinclude:: ../../examples/fitting/doc_example_fitpeak2.lar

Again, we first create mock data that's fairly noisy.  The data is clearly
not exactly rectangular, but we ask it to be fit to a rectangular function
plus a linear background.  The printed output from ``fit_report(params)``
will look like this::

    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 81, 7, 74
       nfev (func calls)   = 99
       chi_square          =  11.867568
       reduced chi_square  =  0.160373

    [[Variables]]
       bkg_offset     =  5.923729 +/- 0.152985 (init=  5.072026)
       bkg_slope      = -0.000659 +/- 0.001301 (init=  0.000000)
       center1        =  27.751278 +/- 0.392722 (init=  40.000000)
       center2        =  83.203400 +/- 0.190616 (init=  120.000000)
       height         =  10.224378 +/- 0.137845 (init=  12.021120)
       width1         =  11.596238 +/- 0.698650 (init=  19.200000)
       width2         =  4.262621 +/- 0.378333 (init=  19.200000)
    [[Constraint Expressions]]
       midpoint       =  55.477339 +/- 0.207626 = '(center1+center2)/2.0'

    [[Correlations]]     (unreported correlations are <  0.300)
       bkg_offset, bkg_slope = -0.915
       bkg_offset, height   = -0.654
       bkg_offset, center1  =  0.542
       height, width1       =  0.508
       bkg_slope, center1   = -0.502
       bkg_slope, height    =  0.500
       bkg_offset, width1   = -0.403
       bkg_slope, width1    =  0.345
    =======================================================

.. _fig-fitpeak2:

.. figure::  ../_images/fit_peakfit2.png
    :target: ../_images/fit_peakfit2.png
    :width: 65%

    Simple fit to mock data to a rectangular function and a linear
    background using the :func:`fit_peak` function.

Again, the principle point here is not how well the rectangular model
matches the actual data here, but how simply one can model data to a
selection of simple shapes.  Such fits can be very useful for preliminary
data visualization and analysis. Of course, one should be cautious about
treating the results of such an automated approach as a final and best
analysis of any data.
