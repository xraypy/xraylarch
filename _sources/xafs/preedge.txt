==============================================
XAFS: Pre-edge Subtraction and Normalization
==============================================

After reading in data and constructing :math:`\mu(E)`, the principle
pre-processing steps for XAFS analysis are pre-edge subtraction and
normalization.  Reading data and constructing :math:`\mu(E)` are handled by
internal larch functions, especially :func:`read_ascii`.  The main
XAFS-specific function for pre-edge subtraction and normalization is
:func:`pre_edge`.

The :func:`pre_edge` function
=================================

..  function:: pre_edge(energy, mu, group=None, ...)

    Pre-edge subtraction and normalization.  This performs a number of steps:
       1. determine :math:`E_0` (if not supplied) from max of deriv(mu)
       2. fit a line of polynomial to the region below the edge
       3. fit a polynomial to the region above the edge
       4. extrapolate the two curves to :math:`E_0` to determine the edge jump


    :param energy:  1-d array of x-ray energies, in eV
    :param mu:      1-d array of :math:`\mu(E)`
    :param group:   output group
    :param e0:      edge energy, :math:`E_0` in eV.  If None, it will be determined here.
    :param step:    edge jump.  If None, it will be determined here.
    :param pre1:    low E range (relative to E0) for pre-edge fit
    :param pre2:    high E range (relative to E0) for pre-edge fit
    :param nvict:   energy exponent to use for pre-edge fit.  See Note below.
    :param norm1:   low E range (relative to E0) for post-edge fit
    :param norm2:   high E range (relative to E0) for post-edge fit
    :param nnorm:   number of terms in polynomial (that is, 1+degree) for
                    post-edge, normalization curve. Default=3 (quadratic)

    :returns:  None.


    Follows the First Argument Group convention, using group members named ``energy`` and ``mu``.
    The following data is put into the output group:

       ==============   =======================================================
        attribute        meaning
       ==============   =======================================================
        e0               energy origin
        edge_step        edge step
        norm             normalized mu(E)   (array)
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

   Notes:
      nvict gives an exponent to the energy term for the pre-edge fit.
      That is, a line :math:`(m E + b)` is fit to
      :math:`\mu(E) E^{nvict}`   over the pr-edge region, E= [E0+pre1, E0+pre2].

..  function:: find_e0(energy, mu=None, group=None, ...)

    Determine :math:`E_0`, the energy threshold of the absorption edge,
    from the arrays energy and mu for :math:`\mu(E)`.

    This finds the point with maximum derivative with some
    checks to avoid spurious glitches.


    :param energy:  array of x-ray energies, in eV
    :param   mu:    array of :math:`\mu(E)`
    :param group:   output group

    Follows the First Argument Group convention, using group members named ``energy`` and ``mu``.
    The value of ``e0`` will be written to the output group.



Pre-Edge Subtraction Example
=================================

A simple example of pre-edge subtraction::

    fname = 'fe2o3_rt1.xmu'
    dat = read_ascii(fname, labels='energy mu i0')

    pre_edge(dat, group=dat)

    show(dat)

    newplot(dat.energy, dat.mu, label=' $ \mu(E) $ ',
            xlabel='Energy (eV)',
            title='%s Pre-Edge ' % fname,
            show_legend=True)

    plot(dat.energy, dat.pre_edge, label='pre-edge line',
         color='black', style='dashed' )

    plot(dat.energy, dat.post_edge, label='normalization line',
         color='black', style='dotted' )

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
:cite:ts:`Weng` with an option of using the modification proposed by
:cite:ts:`lee-xiang`.  In MBACK, the data are matched to the tabulated
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

If this is used in publication, a citation should be given to
:cite:ts:`Weng`.

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


    Follows the First Argument Group convention, using group members named ``energy`` and ``mu``.
    The following data is put into the output group:

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
result shown in :num:`fig-mback-copper`.

.. code:: python

  data=read_ascii('../xafsdata/cu_10k.xmu')
  mback(data.energy, data.mu, group=a, z=29, edge='K', order=4)
  newplot(data.energy, data.f2, xlabel='Energy (eV)', ylabel='matched absorption', label='$f_2$',
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
:num:`fig-mback-talc`.  Note that the order of the Legendre polynomial
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
(:cite:ts:`fluo`) can be used.  The algorithm is contained in the
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

    Follows the First Argument Group convention, using group members named
    ``energy`` and ``mu``.  The value of ``mu_corr`` and ``norm_corr`` will
    be written to the output group, containing :math:`\mu(E)` and
    normalized :math:`\mu(E)` corrected for over-absorption.
