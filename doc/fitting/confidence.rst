===================================================
Advanced Confidence Intervals and Chi-square maps
===================================================

Having good estimates for uncertainties in fitted parameters is important
for any scientific analysis.  One of principle attractions to using the
Levenberg-Marquardt algorithm that is the default fitting mechanism with
the :func:`minimize` function is that it will automatically calculate
estimates of parameter uncertainties and correlations.  This is very
convenient and generally reliable, but it should be made clear that the
basic assumptions made when these uncertainties are estimated are not
always perfect.  Unfortunately, it is sometimes difficult to tell when this
is the case.

It is therefore fairly common to see analyses that include explicit
exploration of Parameter values away from their best-fit solution, in order
to determine the degree of confidence in the best-fit values.
The Larch provides two main functions to help explore such cases.  To be
sure, they are much slower than the automatic estimation of the
uncertainties.  For many (perhaps most) cases, they do not provide much
better insight than the automatic method.


.. module:: _math

.. function:: confidence_intervals(minimizer, sigmas=(1, 2, 3), prob_func=None, maxiter=200)

    Calculate confidence intervals for the parameters from a given fit.

    :param minimizer: the minizer object returned by :func:`minimize`.
    :param sigmas: list of sigma-levels to find parameter values for.
    :param prob_func: ``None`` or callable function to calculate the
    	   probality from the opimized chi-square. By default,
           :func:`f_compare`, the standard F-test, is used.

    The function returns a dictionary of parameter names, with each value
    containing a list of (sigma, value) pairs.

This function will adjust the value for each parameter, re-optimizing the
other parameters until it finds the parameter values that increase sigma by
the levels indicated.

.. function:: confidence_report(conf_values)

    Returns string of a confidence interval report.

    :param conf_values: confidence values returned by :func:`confidence_intervals`.

.. function:: f_test(ndata, nparams, chisquare, chisquare0, nfix=1)

    Returns the standard F-test value for the probability that one fit is
    better than another.




Confidence interval, Example 1
-------------------------------

Let's begin with a shortened version of the first example from the previous
section.

.. literalinclude:: ../../examples/fitting/doc_example_conf1.lar

The printed output from ``fit_report(params)`` will include this::

    [[Variables]]
       amp            =  12.129867 +/- 0.124722 (init=  5.000000)
       cen            =  1.476822 +/- 0.017266 (init=  2.000000)
       off            =  0.998814 +/- 0.007131 (init=  0.000000)
       wid            =  2.022301 +/- 0.016938 (init=  1.000000)

    [[Correlations]]     (unreported correlations are <  0.100)
       amp, off             = -0.861
       amp, wid             =  0.808
       off, wid             = -0.692
    =======================================================

while the output from the much more explicit search done in
:func:`confidence_intervals` and reported by :func:`confidence_report` will be::


    # Confidence Interval Report
    # Sigmas:          -3         -2         -1          0          1          2          3
    # Percentiles:  -99.730    -95.450    -68.269      0.000     68.269     95.450     99.730
    #==========================================================================================
     amp             11.755      11.88     12.005      12.13     12.256     12.385     12.517
        -best      -0.37459   -0.24967   -0.12455          0    0.12604    0.25555    0.38759
     wid             1.9707     1.9885     2.0053     2.0223     2.0395     2.0569     2.0749
        -best     -0.051552  -0.033784  -0.016975          0   0.017156   0.034567   0.052626
     off             0.9766    0.98468     0.9912    0.99881     1.0064     1.0128     1.0209
        -best     -0.022212  -0.014138  -0.0076156          0  0.0075667   0.013987   0.022049
     cen             1.4248     1.4423     1.4596     1.4768     1.4941     1.5113     1.5289
        -best     -0.052057   -0.03452  -0.017248          0   0.017249   0.034524   0.052068

The automatic error estimates given from :func:`minimize` are meant to be
1-:math:`\sigma` uncertainties.   Comparing the two methods we find:

    ============= =============== ========================== =======================
     Parameter      Best Value      Automatic                 Explicit
     Name                           1-:math:`\sigma` value    1-:math:`\sigma` value
    ============= =============== ========================== =======================
      amp           12.1299         +/- 0.1247                 +0.1267, -0.1246
      cen            1.4768         +/- 0.0173                 +0.0172, -0.0172
      off            0.9988         +/- 0.0071                 +0.0076, -0.0076
      cen            2.0223         +/- 0.0169                 +0.0172, -0.0170
    ============= =============== ========================== =======================

which seems to justify the use of the automated method.


Confidence interval, Example 2
-------------------------------

Of course, there are more challenging cases than the one above.
