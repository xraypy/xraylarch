===================================================================
XAFS: Pre-edge Subtraction, Normalization, and data treatment
===================================================================

After reading in data and constructing :math:`\mu(E)`, the principle
pre-processing steps for XAFS analysis are pre-edge subtraction and
normalization.  Reading data and constructing :math:`\mu(E)` are handled by
internal larch functions, especially :func:`read_ascii`.  The main
XAFS-specific function for pre-edge subtraction and normalization is
:func:`pre_edge`.

This chapter also describes methods for the treatment of XAFS and XANES
data including corrections for over-absorption (sometimes confusingly
called *self-absorption*) and for spectral convolution and de-convolution.


The :func:`find_e0` function
=================================

.. autofunction:: larch.xafs.find_e0


The :func:`pre_edge` function
=================================

..  function:: pre_edge(energy, mu, group=None, e0=None, step=None, pre1=None, pre2=None, norm1=None, norm2=None, nnorm=None, nvict=0)

    Pre-edge subtraction and normalization.  This performs a number of steps:
       1. determine :math:`E_0` (if not supplied) from max of deriv(mu)
       2. fit a line of polynomial to the region below the edge
       3. fit a polynomial to the region above the edge
       4. extrapolate the two curves to :math:`E_0` to determine the edge jump

    :param energy:  1-d array of x-ray energies, in eV
    :param mu:      1-d array of :math:`\mu(E)`
    :param group:   output group
    :param e0:      edge energy, :math:`E_0` in eV.  If None, it will be found.
    :param step:    edge jump.  If None, it will be found here.
    :param pre1:    low E range (relative to E0) for pre-edge fit. See Notes.
    :param pre2:    high E range (relative to E0) for pre-edge fit. See Notes.
    :param norm1:   low E range (relative to E0) for post-edge fit. See Notes.
    :param norm2:   high E range (relative to E0) for post-edge fit. See Notes.
    :param nnorm:   degree of polynomial (ie, norm+1 coefficients will be found) for
                    post-edge normalization curve. See Notes.
    :param nvict:   energy exponent to use.  See Notes.
    :param make_flat: boolean (Default True) to calculate flattened output.

    :returns:  None.

    Follows the :ref:`First Argument Group`, using group members named
    ``energy`` and ``mu``.  The following data is put into the output
    group:

       ==============   =======================================================
        attribute        meaning
       ==============   =======================================================
        e0               energy origin
        edge_step        edge step
        norm             normalized mu(E)   (array)
        flat             flattened, normalized mu(E)   (array)
        pre_edge         pre-edge curve (array)
        post_edge        post-edge, normalization curve  (array)
        pre_slope        slope of pre-edge line
        pre_offset       offset of pre-edge line
        nvict            value of nvict used
        nnorm            value of nnorm used
        norm_c0          constant of normalization polynomial
        norm_c1          linear coefficient of normalization polynomial
        norm_c2          quadratic coefficient of normalization polynomial
        norm_c*          higher power coefficients of normalization polynomial
       ==============   =======================================================

For the pre-edge portion of the spectrum, a line is fit to :math:`\mu(E)
E^{\rm{nvict}}` in the region :math:`E={\rm{[e0+pre1, e0+pre2]}}`. `pre1`
and `pre2` default to `None`, which will set:

  - `pre1` = `e0` - 2nd energy point
  - `pre2` = roughly `pre1/3.0`, rounded to 5 eV steps

For the post-edge, a polynomial of order `nnorm` is fit to :math:`\mu(E)
E^{\rm{nvict}}` in the region :math:`E={\rm{[e0+norm1,
e0+norm2]}}`. `norm1`, `norm2`, and `nnorm` default to `None`, which will
set:

   - `norm2` = max energy - `e0`
   - `norm1` = roughly `norm2/3.0`, rounded to 5 eV

The value for `nnorm` = 2 if `norm2-norm1>350`, 1 if `norm2-norm1>50`, or 0 if less.

The "flattened" :math:`\mu(E)` is found by fitting a quadratic curve (no
matter the value of `nnorm`) to the post-edge normalized :math:`\mu(E)` and
subtracts that curve from it.


Pre-Edge Subtraction Example
=================================

A simple example of pre-edge subtraction:

.. code:: python

    # Larch
    fname = 'fe2o3_rt1.xmu'
    dat = read_ascii(fname, labels='energy mu i0')

    pre_edge(dat, group=dat)

    plot_mu(dat, show_pre=True, show_post=True)

or in plain Python:

.. code:: python

    from larch.io import read_ascii
    from larch.xafs import pre_edge
    from wxmplot.interactive import plot

    fname = 'fe2o3_rt1.xmu'
    dat = read_ascii(fname, labels='energy mu i0')

    pre_edge(dat, group=dat)

    plot(dat.energy, dat.mu, label='mu', xlabel='Energy (eV)',
         title=fname,show_legend=True)
    plot(dat.energy, dat.pre_edge, label='pre-edge line')
    plot(dat.energy, dat.post_edge, label='post-edge curve')

gives the following results:

.. _xafs_fig1:

.. figure::  ../_images/xafs_preedge.png
    :target: ../_images/xafs_preedge.png
    :width: 65%
    :align: center

    XAFS Pre-edge subtraction.


The MBACK algorithm
===================

Larch provides an implementation of the MBACK algorithm of
Weng :cite:`Weng` with an option of using the modification proposed by
Lee *et al* :cite:`lee-xiang`.  In MBACK, the data are matched to the tabulated
values of the imaginary part of the energy-dependent correction to the
Thompson scattering factor, :math:`f''(E)`.  To account for any
instrumental or sample-dependent aspects of the shape of the measured
data, :math:`\mu_{data}(E)`, a Legendre polynomial of order :math:`m`
centered around the absorption edge is subtracted from the data.  To
account for the sort of highly non-linear pre-edge which often results
from Compton scattering in the measurement window of an
energy-discriminating detector, a complementary error function is
added to the Legendre polynomial.

The form of the normalization function, then, is

.. math::

  \mu_{back}(E) = \left[\sum_0^m C_i(E-E_0)^i\right] + A\cdot\operatorname{erfc}\left((E-E_{em}\right)/\xi)

where :math:`A`, :math:`E_{em}`, and :math:`\xi` are the amplitude,
centroid, and width of the complementary error function and :math:`s`
is a scaling factor for the measured data.  :math:`E_{em}` is
typically the centroid of the emission line for the measured edge.
This results in a function of :math:`3+m` variables (a tabulated value
of :math:`E_{em}` is used).  The function to be minimized, then is

.. math::

   \frac{1}{n_1} \sum_{1}^{n_1} \left[\mu_{tab}(E) + \mu_{back}(E) + s\cdot\mu_{data}(E)\right]^2 +
   \frac{1}{n_2} \sum_{n_1+1}^{N} \left[\mu_{tab}(E) + \mu_{back}(E) + s\cdot\mu_{data}(E)\right]^2

To give weight in the fit to the pre-edge region, which typically has
fewer measured points than the post-edge region, the weight is
adjusted by breaking the minimization function into two regions: the
:math:`n_1` data points below the absorption edge and the :math:`n_2`
data points above the absorption edge.  :math:`n_1+n_2=N`, where N is
the total number of data points.

If this is used in publication, a citation should be given to Weng :cite:`Weng`.

..  function:: mback(energy, mu, group=None, ...)

    Match measured :math:`\mu(E)` data to tabulated cross-section data.

    :param energy:    1-d array of x-ray energies, in eV
    :param mu:        1-d array of :math:`\mu(E)`
    :param group:     output group
    :param z:         the Z number of the absorber
    :param edge:      the absorption edge, usually 'K' or 'L3'
    :param e0:        edge energy, :math:`E_0` in eV.  If None, the tabulated value is used.
    :param emin:      the minimum energy to include in the fit.  If None, use first energy point
    :param emax:      the maximum energy to include in the fit.  If None, use last energy point
    :param whiteline: a margin around the edge to exclude from the fit.  If not None, must be a positive integer
    :param leexiang:  flag for using the use the Lee&Xiang extension [False]
    :param tables:    'CL' (Cromer-Liberman) or 'Chantler', ['CL']
    :param fit_erfc:  if True, fit the amplitude and width of the complementary error function [False]
    :param return_f1: if True, put f1 in the output group [False]
    :param pre_edge_kws:  dictionary containing keyword arguments to pass to :func:`pre_edge`.
    :returns:  None.


    Follows the :ref:`First Argument Group`, using group members named
    ``energy`` and ``mu``.  The following data is put into the output
    group:

       ==============   ===========================================================
        attribute        meaning
       ==============   ===========================================================
        fpp              matched :math:`\mu(E)` data
        f2               tabulated :math:`f''(E)` data
        f1               tabulated :math:`f'(E)` data (if ``return_f1`` is True)
	mback_params     params group for the MBACK minimization function
       ==============   ===========================================================

Notes:

  - The ``whiteline`` parameter is used to exclude the region around the
    white line in the data from the fit.  The large spectral weight under
    the white line can skew the fit result, particularly in data
    measured over a short data range.  The value is eV units.
  - The ``order`` parameter is the order of the Legendre polynomial.
    Data measured over a very short data range are likely best processed
    with ``order=2``.  Extended XAS data are often better processed with
    a value of 3 or 4.  The order is enforced to be an integer between 1
    and 6.
  - A call to :func:`pre_edge` is made if ``e0`` is not supplied.
  - The option to return :math:`f'(E)` is used by :func:`diffkk`.


Here is an example of processing XANES data measured over an extended
data range.  This example is the K edge of copper foil, with the
result shown in :numref:`fig-mback-copper`.

.. code:: python

    from larch.io import read_ascii
    from larch.xafs import mback
    from wxmplot.interactive import plot

    data = read_ascii('../xafsdata/cu_10k.xmu')
    mback(data.energy, data.mu, group=a, z=29, edge='K', order=4)
    plot(data.energy, data.f2, xlabel='Energy (eV)', ylabel='matched absorption', label='$f_2$',
         legend_loc='lr', show_legend=True)
    plot(data.energy, data.fpp, label='Copper foil')

.. _fig-mback-copper:

.. figure::  ../_images/mback_copper.png
    :target: ../_images/mback_copper.png
    :width: 65%
    :align: center

    Using MBACK to match Cu K edge data measured on a copper foil.


Here is an example of processing XANES data measured over a rather
short data range.  This example is the magnesium silicate mineral
talc, Mg\ :sub:`3`\ Si\ :sub:`4`\ O\ :sub:`10`\ (OH)\ :sub:`2`,
measured at the Si K edge, with the result shown in
:numref:`fig-mback-talc`.  Note that the order of the Legendre polynomial
is set to 2 and that the ``whiteline`` parameter is set to avoid the
large features near the edge.

.. code:: python

  data=read_ascii('Talc.xmu')
  mback(data.e, data.xmu, group=a, z=14, edge='K', order=2, whiteline=50, fit_erfc=True)
  newplot(data.e, data.f2, xlabel='Energy (eV)', ylabel='matched absorption', label='$f_2$',
          legend_loc='lr', show_legend=True)
  plot(data.e, data.fpp, label='Talc ($\mathrm{Mg}_3\mathrm{Si}_4\mathrm{O}_{10}\mathrm{(OH)}_2$)')

.. _fig-mback-talc:

.. figure::  ../_images/mback_talc.png
    :target: ../_images/mback_talc.png
    :width: 65%
    :align: center

    Using MBACK to match Si K edge data measured on talc.



..  function:: mback_norm(energy, mu, group=None, ...)

    A simplified version of :func:`mback` to normalize :math:`\mu(E)` data
    to tabulated cross-section data for :math:`f''(E)`.


    Returns:
      group.norm_poly:     normalized mu(E) from pre_edge()
      group.norm:          normalized mu(E) from this method
      group.mback_mu:      tabulated f2 scaled and pre_edge added to match mu(E)
      group.mback_params:  Group of parameters for the minimization

    References:
      * MBACK (Weng, Waldo, Penner-Hahn): http://dx.doi.org/10.1086/303711
      * Chantler: http://dx.doi.org/10.1063/1.555974


    :param energy:   1-d array of x-ray energies, in eV
    :param mu:       1-d array of :math:`\mu(E)`
    :param group:    output group
    :param z:        the Z number of the absorber
    :param edge:     the absorption edge, usually 'K' or 'L3'
    :param e0:       edge energy, :math:`E_0` in eV.  If None, the tabulated value is used.
    :param pre1:     low E range (relative to E0) as for :func:`pre_edge`.
    :param pre2:     high E range (relative to E0) as for :func:`pre_edge`.
    :param norm1:    low E range (relative to E0) as for :func:`pre_edge`.
    :param norm2:    high E range (relative to E0) as for :func:`pre_edge`.
    :param nnorm:    degree of polynomial as for :func:`pre_edge`.

    Follows the :ref:`First Argument Group`, using group members
    named ``energy`` and ``mu``.  The following data is put into the output
    group:

       ==============   ===========================================================
        attribute        meaning
       ==============   ===========================================================
        norm_poly        normalized :math:`\mu(E)` from :func:`pre_edge`.
        norm             normalized :math:`\mu(E)` from this method/
        mback_mu         tabulated :math:`f'(E)` scalerd and pre-edge added
	mback_params     params group for the MBACK minimization function
       ==============   ===========================================================


Pre-edge baseline subtraction
======================================

A common application of XAFS is the analysis of "pre-edge peaks" of
matransition metal oxides to determine oxidation state and molecular
configuration. These peaks sit just below the main absorption edge
(typically, due to metal *4p* electrons) of a main *K* edge, and are due to
overlaps of the metal *d*-electrons and oxygen *p*-electrons, and are often
described in terms of molecular orbital theory.

To analyze the energies and relative strengths of these pre-edge peaks, it
is necessary to try to remove the contribution of the main edge.  The main
edge (or at least its low energy side) can be modeled reasonably well as a
Lorentzian function for these purposes of describing the tail below the
pre-edge peaks.


.. autofunction:: larch.xafs.prepeaks_setup

.. autofunction:: larch.xafs.pre_edge_baseline


Over-absorption Corrections
=================================

For XAFS data measured in fluorescence, a common problem of
*over-absorption* in which too much of the total X-ray absorption
coefficient is from the absorbing element.  In such cases, the implicit
assumption in a fluorescence XAFS measurement that the fluorescence
intensity is proportional to the absorption coefficient of the element of
interest breaks down.  This is often referred to as *self-absorption* in
the older XAFS literature, but the term should be avoided as it is quite a
different effect from self-absorption in X-ray fluorescence analysis.  In
fact, the effect is more like *extinction* in that the fluorescence
probability approaches a constant, with no XAFS oscillations, as the total
absorption coefficient is dominated by the element of interest.
Over-absorption most stongly effects the XAFS oscillation amplitude, and so
coordination number and mean-square displacement parameters in the EXAFS,
and edge-position and pre-edge peak height for XANES.  Fortunately, the
effect can be corrected for small over-absorption.


For XANES, a common correction method from the FLUO program by D. Haskel
(:cite:`fluo`) can be used.  The algorithm is contained in the
:func:`fluo_corr` function.


.. function:: fluo_corr(energy, mu, formula, elem, group=None, edge='K', anginp=45, angout=45, **pre_kws)

    calculate :math:`\mu(E)` corrected for over-absorption in fluorescence
    XAFS using the FLUO algorithm (suitabe for XANES, but questionable for
    EXAFS).

    :param energy:    1-d array of x-ray energies, in eV
    :param mu:        1-d array of :math:`\mu(E)`
    :param formula:   string for sample stoichiometry
    :param group:     output group
    :param elem:      atomic symbol ('Zn') or Z of absorbing element
    :param edge:      name of edge ('K', 'L3', ...) [default 'K']
    :param anginp:    input angle in degrees  [default 45]
    :param angout:    output angle in degrees [default 45]
    :param pre_kws:   additional keywords for :func:`pre_edge`.

    :returns:         None

    Follows the :ref:`First Argument Group`, using group members named
    ``energy`` and ``mu``.  The value of ``mu_corr`` and ``norm_corr`` will
    be written to the output group, containing :math:`\mu(E)` and
    normalized :math:`\mu(E)` corrected for over-absorption.


Spectral deconvolution
=================================

In order to readily compare XAFS data from different sources, it is
sometimes necessary to considert the energy resolution used to collect each
spectum.  To be clear, the resolution of an EXAFS spectrum includes
contributions from the x-ray sourse, instrumental broadening from the x-ray
optics (especially the X-ray monochromator used in most measurements), and
the intrinsic lifetime of the excited core electronic level.  For data
measured in X-ray fluorescence or electron emission mode, the energy
resolution can also includes the energy width of the decay channels
measured.

For a large fraction of XAFS data, the energy resolution is dominated by
the intrinsic width of the excited core level and by the resolution of a
silicon (111) double crystal monochromator, and so does not vary
appreciably between spectra taken at different facilities or at different
times.  Exceptions to this rule occur when using a higher order reflection
of a silicon monochromator or a different monochromator altogether.
Resolution can also be noticeably worse for data taken at older (first and
second generation) sources and beamlines, either without a collimating
mirror or slits before the monochromator to improve the resolution.
In addition, high-resolution X-ray fluorescence measurements can be used to
dramatically enhance the energy resolution of XAFS spectra, and are
becoming widely available.

Because of these effects, it is sometimes useful to change the resolution
of XAFS spectra.  For example, one may need to reduce the resolution to
match data measured with degraded resolution.  This can be done with
:func:`xas_convolve` which convolves an XAFS spectrum with either a
Gaussian or Lorentzian function with a known energy width.  Note that
convolving with a Gaussian is less dramatic than using a Lorenztian, and
usually better reflects the effect of an incident X-ray beam with degraded
resolution due to source or monochromator.

One may also want to try to improve the energy resolution of an XAFS
spectrum, either to compare it to data taken with higher resolution or to
better identify and enumerate peaks in a XANES spectrum.  This can be done
with :func:`xas_deconvolve` function which deconvolves either a Gaussian or
Lorentzian function from an XAFS spectrum.  This usually requires fairly
good data.  Whereas a Gaussian most closely reflects broadening from the
X-ray source, broadening due to the natural energy width of the core levels
is better described by a Lorenztian.   Therefore, to try to reduce the
influence of the core level in order better mimic high-resolution
fluorescence data, deconvolving with a Lorenztian is often better.



:func:`xas_convolve`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: xas_convolve(energy, norm=None, group=None, form='lorentzian', esigma=1.0, eshift=0.0):

    convolve a normalized mu(E) spectra with a Lorentzian or Gaussian peak
    shape, degrading separation of XANES features.

    This is provided as a complement to xas_deconvolve, and to deliberately
    broaden spectra to compare with spectra measured at lower resolution.


    :param energy:   1-d array of :math:`E`
    :param norm:     1-d array of normalized :math:`\mu(E)`
    :param group:    output group
    :param form:     form of deconvolution function. One of
                     'lorentzian' or  'gaussian' ['lorentzian']
    :param esigma:   energy :math:`\sigma` (in eV) to pass to
                     :func:`gaussian` or :func:`lorentzian` lineshape [1.0]
    :param eshift:   energy shift (in eV) to apply to result. [0.0]


    Follows the :ref:`First Argument Group`, using group members named
    ``energy`` and ``norm``.  The following data is put into the output
    group:


       ================= ===============================================================
        attribute         meaning
       ================= ===============================================================
        conv             array of convolved, normalized :math:`\mu(E)`
       ================= ===============================================================


:func:`xas_deconvolve`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: xas_deconvolve(energy, norm=None, group=None, form='lorentzian', esigma=1.0, eshift=0.0, smooth=True, sgwindow=None, sgorder=3)

    XAS spectral deconvolution

    de-convolve a normalized mu(E) spectra with a peak shape, enhancing the
    intensity and separation of peaks of a XANES spectrum.

    The results can be unstable, and noisy, and should be used
    with caution!

    :param energy:   1-d array of :math:`E`
    :param norm:     1-d array of normalized :math:`\mu(E)`
    :param group:    output group
    :param form:     form of deconvolution function. One of
                     'lorentzian' or  'gaussian' ['lorentzian']
    :param esigma:   energy :math:`\sigma` (in eV) to pass to
                     :func:`gaussian` or :func:`lorentzian` lineshape [1.0]
    :param eshift:   energy shift (in eV) to apply to result. [0.0]
    :param smooth:   whether to smooth the result with the Savitzky-Golay
                     method [``True``]
    :param sgwindow: window size for Savitzky-Golay function [found from data step and esigma]
    :param sgorder:  order for the Savitzky-Golay function [3]


    Follows the :ref:`First Argument Group`, using group members named
    ``energy`` and ``norm``.

    Smoothing with :func:`savitzky_golay` requires a window and order.  By
    default, ``window = int(esigma / estep)`` where estep is step size for
    the gridded data, approximately the finest energy step in the data.


    The following data is put into the output group:


       ================= ===============================================================
        attribute         meaning
       ================= ===============================================================
        deconv            array of deconvolved, normalized :math:`\mu(E)`
       ================= ===============================================================


Examples using :func:`xas_deconvolve` and :func:`xas_convolve`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An example using :func:`xas_deconvolve` to deconvolve a XAFS spectrum would
be:

.. literalinclude:: ../../examples/xafs/doc_deconv1.lar


resulting in deconvolved data:

.. _fig_deconv_fe:

.. figure::  ../_images/xafs_deconv1.png
    :target: ../_images/xafs_deconv1.png
    :width: 65%
    :align: center

    Deconvolved XAFS spectrum for :math:`\rm Fe_2O_3`.


To de-convolve an XAFS spectrum using the energy width of the core level,
we can use the :func:`_xray.core_width` functiion, as shown below for Cu metal.
We can also test that the deconvolution is correct by using
:func:`xas_convolve` to re-convolve the result and comparing it to original
data.  This can be done with:

.. literalinclude:: ../../examples/xafs/doc_deconv2.lar

with results shown below:

.. subfigstart::

.. _fig_xafs_deconv2a:

.. figure::  ../_images/xafs_deconv2a.png
    :target: ../_images/xafs_deconv2a.png
    :width: 100%
    :align: center

    XAS for Cu metal normalized :math:`\mu(E)` and spectrum
    deconvolved by the energy of its core level.

.. _fig_xafs_deconv2b:

.. figure::  ../_images/xafs_deconv2b.png
    :target: ../_images/xafs_deconv2b.png
    :width: 100%
    :align: center

    Comparison of original and re-convolved XAS spectrum for Cu metal.
    The difference shown in red is multiplied by 100.

.. subfigend::
    :width: 0.45
    :label: fig_xafs_deconv

    Example of simple usage of :func:`xas_deconvolve` and
    :func:`xas_convolve` for Cu metal.


Finally, de-convolution of :math:`L_{\rm III}` XAFS data can be
particularly dramatic and useful.  As with the copper spectrum above, we'll
deconvolve :math:`L_{\rm III}` XAFS for platinum, using the nominal energy
width of the core level (5.17 eV).  For this example, we also see
noticeable improvement in amplitude of the XAFS.

.. literalinclude:: ../../examples/xafs/doc_deconv3.lar

with results shown below:

.. subfigstart::

.. _fig_xafs_deconv3a:

.. figure::  ../_images/xafs_deconv3a.png
    :target: ../_images/xafs_deconv3a.png
    :width: 100%
    :align: center

.. _fig_xafs_deconv3b:

.. figure::  ../_images/xafs_deconv3b.png
    :target: ../_images/xafs_deconv3b.png
    :width: 100%
    :align: center

.. subfigend::
    :width: 0.45
    :label: fig_xafs_deconv3

    Example of simple usage of :func:`xas_deconvolve` and
    :func:`xas_convolve` for :math:`L_{\rm III}` XAFS of Pt metal.
    :math:`L_{\rm III}` XAFS of Pt metal, normalized :math:`\mu(E)` for raw
    data and the spectrum deconvolved by the energy of its core level.
