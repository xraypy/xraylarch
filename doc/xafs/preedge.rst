==============================================
XAFS: Pre-edge Subtraction and Normalization
==============================================

After reading in data and constructing :math:`\mu(E)`, the principle
pre-processing steps for XAFS analysis.  are pre-edge subtraction and
normalization.  Reading data and constructing :math:`\mu(E)` are handled by
internal larch functions, especially :func:`read_ascii`.  The main
XAFS-specific function for pre-edge subtraction and normalizaiton is
:func:`pre_edge`.

..  function:: pre_edge(energy, mu, group=None, ...)

    Pre-edge subtraction and normalization.  This performs a number of steps:
       1. determine :math:`E_0` (if not supplied) from max of deriv(mu)
       2. fit a line of polymonial to the region below the edge
       3. fit a polymonial to the region above the edge
       4. extrapolate the two curves to :math:`E_0` to determine the edge jump

    :param energy:  1-d array of x-ray energies, in eV
    :param mu:      1-d array of :math:`\mu(E)`
    :param group:   output group
    :param e0:      edge energy, :math:`E_0` in eV.  If None, it will be determined here.
    :param step:    edge jump.  If None, it will be determined here.
    :param pre1:    low E range (relative to E0) for pre-edge fit
    :param pre2:    high E range (relative to E0) for pre-edge fit
    :param nvict:   energy exponent to use for pre-edg fit.  See Note below.
    :param norm1:   low E range (relative to E0) for post-edge fit
    :param norm2:   high E range (relative to E0) for post-edge fit
    :param nnorm:   number of terms in polynomial (that is, 1+degree) for
                    post-edge, normalization curve. Default=3 (quadratic)

    :returns:  None.

    If a ``group`` argument is provided, the following data is put into it:

       ==============   ======================================================
        attribute        meaning
       ==============   ======================================================
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
        norm_c2          quadratic coefficient of normalizaion polynomial
        norm_c*          higher power coefficents of normalization polynomial
       ==============   ======================================================

Notes:
   nvict gives an exponent to the energy term for the pre-edge fit.
   That is, a line :math:`(m E + b)` is fit to
   :math:`\mu(E) E^{nvict}`   over the pr-edge region, E= [E0+pre1, E0+pre2].

..  function:: find_e0(energy, mu, group=None, ...)

    Determine :math:`E_0`, the energy threshold of the absorption edge,
    from the arrays energy and mu for :math:`\mu(E)`.

    This finds the point with maximum derivative with some
    checks to avoid spurious glitches.


    :param energy:  array of x-ray energies, in eV
    :param   mu:    array of :math:`\mu(E)`
    :param group:   output group

    The value of ``e0`` will be written to the output group.


Example
=========

A simple example of pre-edge subtraction::

    fname = 'fe2o3_rt1.xmu'
    dat = read_ascii(fname, labels='energy xmu i0')

    pre_edge(dat.energy, dat.xmu, group=dat)

    show(dat)

    newplot(dat.energy, dat.xmu, label=' $ \mu(E) $ ',
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




