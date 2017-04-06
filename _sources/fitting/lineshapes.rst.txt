
..  _lineshape-functions-label:

==================================
Some Builtin Line-shape Functions
==================================

Larch provides a number of convenience functions for common line-shapes
used in fitting of experimental data.  This list is not exhaustive, but can
be amended easily.  All these functions return either a floating point
scalar or array, depending on the input ``x``.

.. function:: gaussian(x, cen=0, sigma=1)

   a Gaussian or normal distribution function:

.. math::

  f(x, \mu, \sigma) = \frac{1}{\sigma\sqrt{2\pi}} e^{[{-{(x-\mu)^2}/{{2\sigma}^2}}]}

where *cen* is used for :math:`\mu`.
The Full-Width at Half-Maximum is :math:`2\sigma\sqrt{2\ln{2}}`,
approximately :math:`2.3548\sigma`

.. function:: lorentzian(x, cen=0, sigma=1)

   a Lorentzian or Cauchy-Lorentz distribution function:

.. math::

  f(x, \mu, \sigma) = \frac{1}{\pi} \big[\frac{\sigma}{(x - \mu)^2 + \sigma^2}\big]

where *cen* is used for :math:`\mu`. The Full-Width at Half-Maximum is
:math:`2\sigma`.

.. function:: voigt(x, cen=0, sigma=1, gamma=None)

   a Voigt distribution function.   The definition used here is

.. math::

    f(x, \mu, \sigma, \gamma) = \frac{\textrm{Re}[w(z)]}{\sigma\sqrt{2 \pi}}

where

.. math::
   :nowrap:

   \begin{eqnarray*}
     z &=& \frac{x-\mu +i\gamma}{\sigma\sqrt{2}} \\
     w(z) &=& e^{-z^2}{\operatorname{erfc}}(-iz)
   \end{eqnarray*}

and :func:`erfc` is the complimentary error function.  As above, *cen* is
used for :math:`\mu` here, *sigma* for :math:`\sigma`, and *gamma* for the
parameter :math:`\gamma`.  If *gamma* is left as ``None``, it is set equal
to *sigma*.  For the case when :math:`\gamma = \sigma`, the Full-Width at
Half-Maximum is approximately :math:`3.6013\sigma`.

.. function:: pvoigt(x, cen=0, sigma=1, frac=0.5)

   a pseudo-Voigt distribution function, which is a weighted sum of a
   Gaussian and Lorentzian distribution functions with the same values for
   *cen* (:math:`\mu`) and *sigma* (:math:`\sigma`), and *frac* setting the
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

    s = \frac{\Gamma(p) \sqrt{2^{1/p} -1}}{ \sigma\sqrt{\pi}\,\Gamma(p-1/2)}

where :math:`\Gamma(x)` is the gamma function.


.. function:: students_t(x, cen=0, sigma=1)

   Student's t distribution function.

.. math::

    f(x, \mu, \sigma) = \frac{\Gamma(\frac{\sigma+1}{2})} {\sqrt{\sigma\pi}\,\Gamma(\frac{\sigma}{2})} \Bigl[1+\frac{(x-\mu)^2}{\sigma}\Bigr]^{-\frac{\sigma+1}{2}}


where :math:`\Gamma(x)` is the gamma function.

.. function:: breit_wigner(x, cen=0, sigma=1, q=1)

    Breit-Wigner-Fano distribution function.

.. math::

    f(x, \mu, \sigma, q) = \frac{(q\sigma/2 + x - \mu)^2}{(\sigma/2)^2 + (x - \mu)^2}


.. function:: logistic(x, cen=0, sigma=1)

   Logistic lineshape, a sigmoidal curve

.. math::

   f(x, \mu, \sigma) = 1  - \frac{1}{1 + e^{(x-\mu)/\sigma}}


.. function:: lognormal(x, cen=0, sigma=1)

   log-normal function

.. math::

    f(x, \mu, \sigma) = \frac{e^{-(\ln(x) - \mu)/ 2\sigma^2}}{x}


Several builtin special functions can also be used to create lineshapes
useful in fitting spectra and other x-ray data.  Some of these are detailed
in the :ref:`Table of Useful Line shapes <fit-funcs_table>`.

.. index:: lineshapes for fitting
.. _fit-funcs_table:

    Table of Useful Line shapes.

    ================================= ======================================
     *function*                         *description*
    ================================= ======================================
    gaussian(x, cen, sigma)           Gaussian, normal distribution
    lorentzian(x, cen, sigma)         Lorentzian distribution
    voigt(x, cen, sigma, gamma)       Voigt distribution
    pvoigt(x, cen, sigma, frac)       pseudo-Voigt distribution
    pearson7(x, cen, sigma, expon)    Pearson-7 distribution
    students_t(x, cen, sigma)         Student's t distribution
    breit_wigner(x, cen, sigma, q)    Breit-Wigner-Fano distribution
    logistic(x, cen, sigma)           Logistic distribution
    lognormal(x, cen, sigma)          Log-normal distribution
    arctan(x)                         Arc-tangent function
    erf(x)                            Error function
    erfc(x)                           Complemented Error function (1-erf(x))
    gammaln(x)                        log of absolute value of gamma(x)
    ================================= ======================================


Other standard special functions (Bessel functions, Legendre polynomials,
etc) can be accessed from scipy.special::

    from scipy.special import j0 # Bessel function of order 0,
    from scipy.special import y1 # Bessel function of second kind of order 1

A host of functions to generate other distribution functions can be accessed from scipy.stats.

