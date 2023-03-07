.. _lmfit: https://lmfit.github.io/lmfit-py/

..  _lineshape-functions-label:

==================================
Some Builtin Line-shape Functions
==================================

.. versionchanged:: 0.9.34
   The definitions of these line shapes are now taken from the
   `lmfit`_ package, and have a more uniform interface.

Larch provides a number of convenience functions for common line-shapes
used in fitting of experimental data.  This list is not exhaustive, but can
be amended easily.  All these functions return either a floating point
scalar or array, depending on the input ``x``.

.. function:: gaussian(x, amplitude=1, center=0, sigma=1)

    a Gaussian or normal distribution function (see
    https://en.wikipedia.org/wiki/Normal_distribution), with three
    Parameters: ``amplitude``, ``center``, and ``sigma``.

    .. math::

        f(x; A, \mu, \sigma) = \frac{A}{\sigma\sqrt{2\pi}} e^{[{-{(x-\mu)^2}/{{2\sigma}^2}}]}

    where the parameter ``amplitude`` corresponds to :math:`A`, ``center`` to
    :math:`\mu`, and ``sigma`` to :math:`\sigma`.

    The full width at half maximum is :math:`2\sigma\sqrt{2\ln{2}}`,
    approximately :math:`2.3548\sigma`.   The maximum height is
    :math:`A/(\sigma\sqrt{2\pi})`.

.. function:: lorentzian(x, amplitude=1, center=0, sigma=1)

    A Lorentzian or Cauchy-Lorentz distribution function (see
    https://en.wikipedia.org/wiki/Cauchy_distribution), with three
    Parameters: ``amplitude``, ``center``, and ``sigma``.

    .. math::

        f(x; A, \mu, \sigma) = \frac{A}{\pi} \big[\frac{\sigma}{(x - \mu)^2 + \sigma^2}\big]

    where the parameter ``amplitude`` corresponds to :math:`A`, ``center`` to
    :math:`\mu`, and ``sigma`` to :math:`\sigma`.  The full width at
    half maximum is :math:`2\sigma`.  The maximum height is
    :math:`A/(\sigma\pi)`.


.. function:: voigt(x, amplitude=1, center=0, sigma=1, gamma=None)

    A Voigt distribution function (see
    https://en.wikipedia.org/wiki/Voigt_profile), with four Parameters:
    ``amplitude``, ``center``, ``sigma``, and ``gamma`` defined as:


    .. math::

        f(x; A, \mu, \sigma, \gamma) = \frac{A \textrm{Re}[w(z)]}{\sigma\sqrt{2\pi}}

    where

    .. math::
        :nowrap:

        \begin{eqnarray*}
             z   &=& \frac{x-\mu +i\gamma}{\sigma\sqrt{2}} \\
            w(z) &=& e^{-z^2}{\operatorname{erfc}}(-iz)
        \end{eqnarray*}

    and :func:`erfc` is the complimentary error function.  As above, the
    parameter ``amplitude`` corresponds to :math:`A`, ``center`` to
    :math:`\mu`, and ``sigma`` to :math:`\sigma`.  With the default value of
    ``None``, ``gamma`` (:math:`\gamma`) is constrained to have value equal
    to ``sigma``, though it can be varied independently.  For the case when
    :math:`\gamma = \sigma`, the full width at half maximum is approximately
    :math:`3.6013\sigma`.

.. function:: pvoigt(x, amplitude=1, center=0, sigma=1, fraction=0.5)

    A pseudo-Voigt distribution function, which is a weighted sum of a
    Gaussian and Lorentzian distribution functions with the same values for
    ``amplitude`` (:math:`A`) , ``center`` (:math:`\mu`) and the same full
    width at half maximum (so constrained values of `sigma``,
    :math:`\sigma`).  A paramater ``fraction`` (:math:`\alpha`) controls
    controls the relative weight of the Gaussian and Lorentzian components,
    giving the full definition of

    .. math::

        f(x; A, \mu, \sigma, \alpha) = \frac{(1-\alpha)A}{\sigma_g\sqrt{2\pi}}
           e^{[{-{(x-\mu)^2}/{{2\sigma_g}^2}}]}
           + \frac{\alpha A}{\pi} \big[\frac{\sigma}{(x - \mu)^2 + \sigma^2}\big]


.. function:: pearson7(x, amplitude=1, center=0, sigma=1, exponent=0.5)


    A Pearson VII distribution function (see
    https://en.wikipedia.org/wiki/Pearson_distribution#The_Pearson_type_VII_distribution),
    with four parameers: ``amplitude`` (:math:`A`), ``center``
    (:math:`\mu`), ``sigma`` (:math:`\sigma`), and ``exponent`` (:math:`m`)
    in

    .. math::

        f(x; A, \mu, \sigma, m) = \frac{A}{\sigma{\beta(m-\frac{1}{2}, \frac{1}{2})}} \bigl[1 + \frac{(x-\mu)^2}{\sigma^2}  \bigr]^{-m}

   where :math:`\beta` is the beta function (see `scipy.special.beta`)


.. function:: students_t(x, amplitude=1, center=0, sigma=1)

    A Student's t distribution function (see
    https://en.wikipedia.org/wiki/Student%27s_t-distribution), with three
    Parameters: ``amplitude`` (:math:`A`), ``center`` (:math:`\mu`) and
    ``sigma`` (:math:`\sigma`) in

    .. math::

        f(x; A, \mu, \sigma) = \frac{A \Gamma(\frac{\sigma+1}{2})}
            {\sqrt{\sigma\pi}\,\Gamma(\frac{\sigma}{2})}
            \Bigl[1+\frac{(x-\mu)^2}{\sigma}\Bigr]^{-\frac{\sigma+1}{2}}


    where :math:`\Gamma(x)` is the gamma function.


.. function:: breit_wigner(x, amplitude=1, center=0, sigma=1, q=1)

    A Breit-Wigner-Fano distribution function (see
    https://en.wikipedia.org/wiki/Fano_resonance>), with four Parameters:
    ``amplitude`` (:math:`A`), ``center`` (:math:`\mu`), ``sigma``
    (:math:`\sigma`), and ``q`` (:math:`q`) in

    .. math::

        f(x; A, \mu, \sigma, q) = \frac{A (q\sigma/2 + x - \mu)^2}{(\sigma/2)^2 + (x - \mu)^2}

.. function:: lognormal(x, cen=0, sigma=1)

    A Log-normal distribution function (see
    https://en.wikipedia.org/wiki/Lognormal), with three Parameters
    ``amplitude`` (:math:`A`), ``center`` (:math:`\mu`) and ``sigma``
    (:math:`\sigma`) in

    .. math::

        f(x; A, \mu, \sigma) = \frac{A e^{-(\ln(x) - \mu)/ 2\sigma^2}}{x}


Several builtin special functions can also be used to create lineshapes
useful in fitting spectra and other x-ray data.  Some of these are detailed
in the :ref:`Table of Useful Line shapes <fit-funcs_table>`.

.. index:: lineshapes for fitting
.. _fit-funcs_table:

    Table of Useful Line shapes.


    ================================================ ======================================
     *function*                                       *description*
    ================================================ ======================================
    gaussian(x, amplitude, center, sigma)             Gaussian, normal distribution
    lorentzian(x, amplitude, center, sigma)           Lorentzian distribution
    voigt(x, amplitude, center, sigma, gamma)         Voigt distribution
    pvoigt(x, amplitude, center, sigma, fraction)     pseudo-Voigt distribution
    pearson7(x, amplitude, center, sigma, exponent)   Pearson-7 distribution
    students_t(x, amplitude, center, sigma)           Student's t distribution
    breit_wigner(x, amplitude, center, sigma, q)      Breit-Wigner-Fano distribution
    lognormal(x, amplitude, center, sigma)            Log-normal distribution
    arctan(x)                                         Arc-tangent function
    erf(x)                                            Error function
    erfc(x)                                           Complemented Error function (1-erf(x))
    gammaln(x)                                        log of absolute value of gamma(x)
    ================================================ ======================================


Other standard special functions (Bessel functions, Legendre polynomials,
etc) can be accessed from ``scipy.special``::

    from scipy.special import j0 # Bessel function of order 0,
    from scipy.special import y1 # Bessel function of second kind of order 1

A host of functions to generate other distribution functions can be accessed from ``scipy.stats``.
