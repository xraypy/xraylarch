==============================================
XAFS: Post-edge Background Subtraction
==============================================

Background subtraction is an important data processing steps in EXAFS
analysis, converting the measured :math:`\mu(E)` into the :math:`\chi(k)`
ready for quantitative analysis.  In larch, this step is performed by the
:func:`autobk` function.  This function has many options and subtleties,
and this section is devoted to this function and the underlying algorithm.


The :func:`autobk` function
=============================

..  function:: autobk(energy, mu, group=None, rbkg=1.0, ...)

    Determine the post-edge background function, :math:`\mu_0(E)`, and
    corresponding :math:`\chi(k)`.

    :param energy:  1-d array of x-ray energies, in eV
    :param mu:      1-d array of :math:`\mu(E)`
    :param group:   output group
    :param rbkg:    distance (in :math:`\rm\AA`) for :math:`\chi(R)` above
                    which the signal is ignored. Default = 1.
    :param e0:          edge energy, in eV. If `None`, it will be determined.
    :param edge_step:   edge step.  If `None`, it will be determined here.
    :param pre_edge_kws:  keyword arguments to pass to :func:`pre_edge`.
    :param nknots:   number of knots in spline.  If `None`, it will be determined.
    :param kmin:     minimum :math:`k` value   [0]
    :param kmax:     maximum :math:`k` value   [full data range].
    :param kweight:  :math:`k` weight for FFT.  [1]
    :param dk:       FFT window window parameter.  [0]
    :param win:      FFT window function name.     ['hanning']
    :param nfft:     array size to use for FFT [2048]
    :param kstep:    :math:`k` step size to use for FFT [0.05]
    :param k_std:    optional :math:`k` array for standard :math:`chi(k)`.
    :param chi_std:  optional :math:`\chi` array for standard :math:`chi(k)`.
    :param nclamp:    number of energy end-points for clamp [2]
    :param clamp_lo:  weight of low-energy clamp [1]
    :param clamp_hi:  weight of high-energy clamp [1]
    :param calc_uncertaintites:  Flag to calculate uncertainties in  :math:`\mu_0(E)` and :math:`\chi(k)` [``False``]

    :returns: ``None``.

    If a ``group`` argument is provided, the following data is put into it:

       ================= ===============================================================
        attribute         meaning
       ================= ===============================================================
        bkg               array of :math:`\mu_0(E)` (not normalized)
        chie              array of :math:`\chi(E)` values.
        k                 array of :math:`k` values, on uniform grid.
        chi               array of :math:`\chi(k)` values, the EXAFS.
        *delta_chi*       array of uncertainty in :math:`\chi(k)`.
        *delta_bkg*       array of uncertainty in :math:`\mu_0(E)`.
        autobk_details    Group of arrays with autobk details.
       ================= ===============================================================

    Here, the arrays ``group.k``, ``group.chi``, and ``group.delta_chi``
    will be the same length, giving :math:`\chi(k)` and its uncertainty
    from 0 to a maximum k value determined by ``kmax`` or the range of
    available data.  The arrays ``group.bkg``, ``group.delta_bkg``, and
    ``group.chie`` will correspond to the input ``energy`` array, but will
    only be calculated and written if the argument ``calc_uncertainties``
    is ``True``.   In addition, if pre-edge subtraction had not been done
    previously, it will be done here, and the outputs described for
    :func:`pre_edge` will also be written to ``group``.

    The ``group.autobk_details`` group will contain the following attributes:

       ================= ===========================================================
        attribute         meaning
       ================= ===========================================================
        spline_pars       Parameters used for determining :math:`\mu_0(E)` spline.
        init_bkg          Initial value for :math:`\mu_0(E)`
        init_chi          Initial value for :math:`\chi(k)`
        knots_e           Spline knot energies
        knots_y           Spline knot values
        init_knots_y      Initial Spline knot values
       ================= ===========================================================

    Note that ``e0`` and ``edge_step`` can be specified.  If not specified,
    they will be determined by calling :func:`pre_edge`.  The
    ``pre_edge_kws`` argument can be used to pass custom arguments to
    :func:`pre_edge`.

The AUTOBK Algorithm
======================

The background subtraction method used is the **AUTOBK** algorithm, in
which a spline function is matched to the low-*R* components of the
resulting :math:`\chi(k)`.

For reference, :math:`k = \sqrt{2m_e (E-E_0)/\hbar^2}` is the wavenumber of
the ejected photo-electron, where :math:`E_0` is the absorption threshold
energy (the 0 of photo-electron energy).  For :math:`k` in units of
:math:`\rm \AA^{-1}` and :math:`E` in units of eV, :math:`k \approx
\sqrt{(E-E_0)/3.81}`.  With this conversion of energy to wavenumber,
:math:`\chi(k)` is defined from

    :math:`\chi(E) = \frac{\mu(E)-\mu_0(E)}{\Delta\mu}`

where :math:`\mu_0(E)` represents the idealized x-ray absorption of a
bare atom, embedded in the molecular or solid environment, but without
scattering of the outgoing photo-electron that gives rise to the EXAFS, and
:math:`\Delta\mu` is the edge step in :math:`\mu(E)`.

The quantity :math:`\mu_0(E)` cannot be independently measured.  Here we
empirically determine it given the data for :math:`\mu(E)` by fitting a
spline (a piece-polynomial function that is easily adjusted even while its
smoothness is controlled) to :math:`\mu(E)`.  An advantage to what could
easily be described as an *ad hoc* approach is that the data for
:math:`\mu(E)` can hide many systematic drifts and dependencies that are
slowly varying with energy.

You may also note the definition above normalizes to the edge step
:math:`\Delta\mu` instead of the energy-dependent :math:`\mu_0(E)`, as is
often described in introductory texts on EXAFS.  The reason for this is
essentially the same -- so that we do not need to carefully take care of
slow energy drifts in the measured :math:`\mu(E)` or worry about having an
absolute measure of :math:`\mu(E)`.

:math:`R_{\rm bkg}` and spline for :math:`\mu_0(E)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Of course, a spline is a general mathematical function, and so using one to
match :math:`\mu(E)` that we will subtract from the same :math:`\mu(E)`
could easily match *too* well, and erase much of the data we're interested
in.  Therefore, we have to carefully consider both how flexible the spline
can be and what portions of the spectrum we want it to match.  What we want
is a :math:`\mu_0(E)` that removes the low frequency (low-*R*) portions of
the :math:`\chi` spectra, and recognizing this can tell us how to determine
both of these.

First, since we know the EXAFS oscillations do not extend far below the
near-neighbor distance and since atoms are essentially never closer than 1
:math:`\rm\AA`, and generally more like 2 :math:`\rm\AA`, we can say that we want
to remove the frequencies of :math:`\chi` below some distance,
:math:`R_{\rm bkg}` (or ``rbkg`` in :func:`autobk`).  That is, we want to
the spline function to be adjusted so that the components of
:math:`\chi(R)` below :math:`R_{\rm bkg}` are minimized.  We can use a
default of 1 :math:`\rm\AA`, and recommend that the value be roughly half the
expected near-neighbor distance.

The second question of how flexible to make the spline is answered from
basic signal processing through the `Nyquist-Shannon sampling theorem
<http://en.wikipedia.org/wiki/Nyquist-Shannon_sampling_theorem>`_,
which tells us how many adjustable parameters to use for our spline:

.. math::

  N_{\rm spline}  =  1 + \frac{2R_{\rm bkg} \Delta k}{\pi}

where :math:`\Delta k` is the :math:`k` range of the data.  We create a
spline function consisting of :math:`N_{\rm spline}` adjustable points
(*knots* in the spline, where the second derivatives are allowed to
change), evenly spaced in :math:`k` (that is, quadratic in energy).  We do
a fit that adjusts the values of the function at each knot, computes
:math:`\mu_0(E)` by simple spline interpolation, calculates
:math:`\chi(k)`, does a Fourier transform to :math:`\chi(R)`, and then
seeks to minimize the components of :math:`\chi(R)` below :math:`R_{\rm
bkg}`.  In this way we satisfy both considerations above: limiting the
number of knots prevents the spline from being able to follow the
frequencies of :math:`\chi(k)` we care about most, and limiting the portion
of the spectrum to be minimized to the very low-:math:`R` components, we do
not even try to match those frequencies.  Thus, we are ensured of a
:math:`\mu_0(E)` that only removes the low-:math:`R` components of
:math:`\chi`.

Selecting Fourier transform parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to determine :math:`\mu_0(E)` in this way, we must do a Fourier
transform.  These are discussed in more detail in the next section, but
here we mention the parameters affecting the Fourier transform used, and
their default values.  The default parameter values are generally
sufficient, and need only minor adjustments except in unusual cases.

    ========== ====================== ============================================
     argument   meaning                default, recommended values
    ========== ====================== ============================================
     kmin       :math:`k_{\rm min}`    0. should be below 1.0
     kmax       :math:`k_{\rm max}`    highest :math:`k` value. Useful data range.
     kweight    :math:`kw`             1. should be 0 or 1 (but not > 2)
     win        window function name   Hanning, Parzen works well too.
     dk         window sill size       0. should be 0 or 1
     nfft       FFT array size           2048.  No reason to change this.
     kstep      :math:`k` step size     0.05.  No reason to change this.
    ========== ====================== ============================================

Using a standard :math:`\chi(k)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We said above that we want simply to minimize the low-:math:`R` components
of :math:`\chi`.  In principle, there should be some leakage of the first
shell to fairly low-:math:`R`.  This is especially noticeable for a short
ligand (say, below 1.75 :math:`\rm\AA` or so) of a low-Z atom (notably, C,
N, and O).  Normally, this is not a serious problem, but it does point out
that :math:`\mu_0(E)` might want to leave some first-shell leakage at
low-:math:`R`.

To accout for this, you can proved a spectrum of :math:`chi(k)` for a
standard that is meant to be close to the spectrum being analyzed.  This is
done by providing 2 arrays: ``k_std`` and ``chi_std``, which need to be the
same lenth.  By providing these, the best values for :math:`\mu_0(E)` will
be those that minimize the the Fourier transorm of the difference of
:math:`\chi(k)` for the data and standard.    This can be especially helpful
to give more consistent background

End-point clamps for the spline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because the spline is chosen to match the low-:math:`R` components of
:math:`\chi`, the process does not even look at how the resulting
:math:`\mu_0(E)` looks.  This can lead to some unstable behavior at the
end-points of the spline, and cause :math:`\chi(k)` to diverge at the ends.

This can be remedied by add *clamps* to fit.  These include a few points at
the low- and high-ends of the :math:`\chi(k)` array, and include them in
the array to be minimized in the fit.  This has the tendency to push the
end-points of :math:`\chi(k)` to zero.

There are three parameters influencing the clamps.  ``nclamp`` sets the
number of data points of :math:`\chi(k)` at the beginning and end of the
:math:`k` range to add to the fit.  ``clamp_lo`` sets the weighting factor
applied to the first ``nclamp`` points for the low-:math:`k` end fo the
data range, and ``clamp_hi`` sets the weighting factor applied to the last
``nclamp`` points at the high-:math:`k` end.

There is not an easy way to determine ahead of time what the clamp
parameters will be.  Typically, ``nclamp`` need only be 1 to 5 data points
(with 2 being the default).  Setting ``nclamp`` to 0 will remove the clamps
completely.  Values for ``clamp_lo`` and ``clamp_hi`` are floating point
numbers, and should range from about 1 (the default) to 10 or 20 for a very
strong clamp that will almost certainly force :math:`\chi(k)` to be 0 at
the end-points.

Recommendations
~~~~~~~~~~~~~~~~~

Here, we give a few recommendations on what parameters most affect the
background subtraction.  These parameters are (in roughly increasing
order):

 0. ``rbkg``:  This is the main parameter that sets how flaexible the
 spline function can be.

 1.  ``e0``: It can be hard to know what :math:`E_0` should be for any XAFS
 spectra.  As this sets the value of :math:`k=0`, it will affect the
 location of the knots, and can have a profound affect on the results.  If
 you're unhappy with the :math:`\mu_0(E)` and :math:`\chi(k)`, playing with
 the ``e0`` parameter.

 2. ``kweight``: Increasing this emphasizes the fit at high *k*.  Trying
 both values of 0 and 1 is always a good idea.

 3. ``clamp_lo`` and ``clamp_hi``: If :math:`\mu_0(E)` swoops up or down at
 the endpoints too much, increasing these values can help greatly.


Examples
==========


