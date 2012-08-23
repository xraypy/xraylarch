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

    ======================= =============================================
     *attribute*               *statistical quantity*
    ======================= =============================================
     residual                residual array, with npts elements
     nfcn_calls              number of calls to objective function
     nvarys                  number of independent variables
     nfree                   number of free parameters (npts - nvarys)
     chi_square              :math:`\chi^2`, chi-square
     chi_reduced             :math:`\chi_\nu^2`, reduced chi-square
     message                 an output message about fit
     errorbars               flag for whether errorbars were calculated
     lmdif                   Group containing output data from MINPACK-1
    ======================= =============================================
