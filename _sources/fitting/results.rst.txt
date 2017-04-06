.. _fitting-results-sec:

============================
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
variable names and meanings as outlines in
:ref:`Table of Fit Statistics <minimize-stats_table>`.  For advanced users,
the full residual vector,
covarance matrix, and jacobian matrix from the fit, as well as several more
esoteric outputs from MINPACK's lmdif function are put in
*paramgroup.lmdif*.

.. _minimize-stats_table:

   Table of Fit Statistics.
   Listed are the name of the variable added to the fit *paramgroup*, and
   the statistical quantity it holds.

    ======================= ==================================================
     *attribute*               *statistical quantity or other output*
    ======================= ==================================================
     residual                final array returned from objective function
     nvarys                  number of independent variables
     nfree                   number of free parameters (len(residual) - nvarys)
     chi_square              :math:`\chi^2`, chi-square
     chi_reduced             :math:`\chi_\nu^2`, reduced chi-square
     message                 an output message about fit
     errorbars               flag for whether errorbars were calculated
     fit_details             Group containing output data from fitting method
     fit_details.method      name of fitting method used.
     fit_details.nfev        number of calls to (evaluations of) objective function
    ======================= ==================================================

Additional outputs written to the ``fit_details`` group vary for each
fitting method.

.. function:: fit_report(paramgroup, show_correl=True, min_correl=0.1)

   returns a fit report for a fit given a parameter group.

   :param paramgroup:  parameter group, after being used in a fit.
   :param show_correl: flag (``True``/``False``) to show parameter correlations.
   :param min_correl:  smallest absolute value of correlation to show.
   :returns:   string of fit report.   This can be printed or stored.


A typical result from :func:`fit_report` would look like this::

    larch> print fit_report(params)
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

