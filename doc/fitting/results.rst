.. _lmfit: https://lmfit.github.io/lmfit-py/

.. _fitting-results-sec:

============================
Fit Results and Outputs
============================

.. versionchanged:: 0.9.34
   :func:`minimize` returns a result group containing fit statistics.

After the fit has completed, several statistics are output and available to
describe the quality of the fit and the estimated values for the Parameter
values and uncertainties.  The main statistics are written to group
returned by :func:`minimize`, while the parameter values in *paramgroup*
are updated to their best-fit values.

The estimated values, uncertainties, and correlations for each varied
Parameter are written as attributes of that Parameter.  Thus, after a fit,
each variable Parameter ``par`` will be updated so that ``par.value`` will
hold the estimated best-fit value, ``par.stderr`` will hold the estimated
uncertainty (1-:math:`\sigma` standard error), and ``par.correl`` will hold
a dictionary of correlation values with the other variable Parameters.

General Fit statistics describing the quality of the fit and details about
how the fit proceeded will be put into the result group with
variable names and meanings as outlines in
:ref:`Table of Fit Statistics <minimize-stats_table>`.  For advanced users,
the fitting class instance and result from `lmfit` are available.

.. _minimize-stats_table:

   Table of Fit Statistics and Results contained in the return value of :func:`minimize`.

   Listed are the names and description of items in the fit result group
   returned by the :func:`minimize` function.  Many of these items are
   directly from `lmfit`_.


    ============== ======================================================================
     name           Description of Statistical Quantity or Output
    ============== ======================================================================
    nvarys          number of variable parameters in the fit
    ndata           number of data points
    nfree           ndata - nfree
    chi_square      chi-square: :math:`\chi^2 = \sum_i^N [{\rm Resid}_i]^2`
    chi_reduced     reduced chi-square: :math:`\chi^2_{\nu}= {\chi^2} / {(N - N_{\rm varys})}` |
    rfactor         R factor: :math:`\cal R = \sum_i^N [{\rm Resid}_i]^2 /\sum_i^N [{\rm Data}_i]^2`
    aic             :lmfitx:`Akaike Information Criteria <fitting.html#akaike-and-bayesian-information-criteria>`
    bic             :lmfitx:`Bayesian Information Criteria <fitting.html#akaike-and-bayesian-information-criteria>`
    residual        final residual array
    covar           covariance matrix (ordered according to `var_names`).
    var_names       list of variable parameter names
    params          lmfit :lmfitx:`Parameters <parameters.html#lmfit.parameter.Parameters>`
    fitter          lmfit :lmfitx:`Minimizer <fitting.html#lmfit.minimizer.Minimizer>`
    fit_details     lmfit :lmfitx:`MinimizerResult <fitting.html#lmfit.minimizer.MinimizerResult>`
    nfev            number of evaluations of the fit residual function.
    success         bool (`True` or `False`) for whether fit appeared to succeed.
    errorbars       bool (`True` or `False`) for whether uncertainties were estimated.
    message         text message from fit
    lmdif_message   text message from Fortran least-squares function
    ============== ======================================================================


.. versionchanged:: 0.9.34
   :func:`fit_report` uses a result group returned by :func:`minimize`

.. function:: fit_report(result, show_correl=True, min_correl=0.1)

   returns a fit report for a fit given a parameter group.

   :param result:      fit result group, returned by :func:`minimize`.
   :param show_correl: flag (``True``/``False``) to show parameter correlations.
   :param min_correl:  smallest absolute value of correlation to show.
   :returns:   string of fit report.   This can be printed or stored.


A typical result from :func:`fit_report` would look like this::

    larch> print fit_report(result)
    ===================== FIT RESULTS =====================
    [[Statistics]]    Fit succeeded,  method = 'leastsq'.
       Message from fit    = Fit succeeded.
       npts, nvarys, nfree = 501, 4, 497
       nfev (func calls)   = 26
       chi_square          = 30.650777
       reduced chi_square  = 0.061672

    [[Variables]]
       amp            =  12.053707 +/- 0.383248 (init=  10.000000)
       cen            =  10.943759 +/- 0.052711 (init=  10.800000)
       off            =  2.209804 +/- 0.022001 (init= -3.100000)
       wid            =  2.013217 +/- 0.052131 (init=  1.000000)

    [[Correlations]]     (unreported correlations are <  0.100)
       amp, off             = -0.864
       amp, wid             =  0.812
       off, wid             = -0.699
    =======================================================
