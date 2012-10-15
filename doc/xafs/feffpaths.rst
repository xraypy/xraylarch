==============================================
XAFS: Reading and using Feff Paths
==============================================

.. module:: _xafs

For modeling EXAFS data, Larch relies heavily on calculations of
theoretical XAFS spectra using FEFF.  Being able to run FEFF and use its
results is of fundamental importance for using Larch for fitting EXAFS
spectra.  While a complete description of FEFF is beyond the scope of this
documentation, here we describe how to read the results from FEFF into
Larch.  The main interface for this is the :func:`feffpath` function that
reads FEFF *feffNNNN.dat* file and creates a FeffPath Group.


:func:`feffpath` and FeffPath Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The outputs from Feff for each path are complicated enough to need a
structured organization of data.  This is accomplished by providing a
special kind of a Larch Group -- a FeffPath Group which holds all the
information about a Feff Path, including the photo-electron scattering
amplitudes and phase-shifts needed to describe and calculate the EXAFS for
that Path.  A FeffPath Group is created with the :func:`feffpath`
group. For many uses a Feff Path can be treated as a "black box", and
simply setting the adjustable Path Parameters and passing around these
Groups is sufficient for simulating and fitting EXAFS spectra.

At times it can be helpful to inspect and study the detailed components of
the Feff Path.  Since a FeffPath Group is a regular Larch Group, all the
data can be read and viewed.  A FeffPath Group has the components listed in
the :ref:`Table of Feff Path Parameters <xafs-pathparams_table>`.  This
includes the *Adjustable Numerical Path Parameters* -- the values of which
can be changed to affect the calculated EXAFS for the Path -- as well as
the arrays for :math:`k` and :math:`\chi` and several other attributes.
Since this Group is used to calculate :math:`\chi(k)` for the path, many of
the components need to be in place and holding the expected values so that
the calculation can be done correctly, Due to Larch's flexibility, it is
possible to delete, overwrite, or put inappropriate values into the
components of a FeffPath Group, and care must be taken to avoid this.


.. index:: Feff Path Parameters

.. _xafs-pathparams_table:

    Table of FeffPath attributes, including the Path Parameters used in the
    EXAFS equation.  The attributes here are arranged by category.  The *Info*
    attributes are informational only.  The two *Numerical* attributes ``reff``
    and ``nleg`` are used in the EXAFS equation but are meant to be constants
    and their values should not be changed.  The *Adjustable* attributes are the
    standard Adjustable, Numerical Path Parameters that can be changed to affect
    the resulting EXAFS :math:`\chi(k)`.  These can be set either as constant
    values or fitting Parameters as defined by :func:`_math.param`.  The *Output
    array* attributes are the arrays output from :func:`path2chi`.  Finally, the
    sub-group ``_feffdat`` contains the low-level data as read directly from the
    *feffNNNN.dat* file, which is detailed in the next section,
    :ref:`xafs-feffdat_sec`.

    +-----------------+-----------------+----------------------------------------------------+
    | attribute name  | category        | description                                        |
    +=================+=================+====================================================+
    |   filename      |  Info           | name of *feffNNNN.dat* file                        |
    +-----------------+-----------------+----------------------------------------------------+
    |   label         |  Info           | path description                                   |
    +-----------------+-----------------+----------------------------------------------------+
    |   geom          |  Info           | path geometry: list of (symbol, ipot, x, y, z)     |
    +-----------------+-----------------+----------------------------------------------------+
    |   reff          |  Numerical      | :math:`R_{\rm eff}`, nominal path length           |
    +-----------------+-----------------+----------------------------------------------------+
    |   nleg          |  Numerical      | number of path legs (1+number of scatterers)       |
    +-----------------+-----------------+----------------------------------------------------+
    |   degen         |  Adjustable     | :math:`N`, path degeneracy                         |
    +-----------------+-----------------+----------------------------------------------------+
    |   s02           |  Adjustable     | :math:`S_0^2`, amplitude reduction factor          |
    +-----------------+-----------------+----------------------------------------------------+
    |   e0            |  Adjustable     | :math:`E_0`, energy origin                         |
    +-----------------+-----------------+----------------------------------------------------+
    |   deltar        |  Adjustable     | :math:`\delta R`, shift in path length             |
    +-----------------+-----------------+----------------------------------------------------+
    |   sigma2        |  Adjustable     | :math:`\sigma^2`, mean-square displacement         |
    +-----------------+-----------------+----------------------------------------------------+
    |   third         |  Adjustable     | :math:`c_3`,  third cumulant                       |
    +-----------------+-----------------+----------------------------------------------------+
    |   fourth        |  Adjustable     | :math:`c_4`, the fourth cumulant                   |
    +-----------------+-----------------+----------------------------------------------------+
    |   ei            |  Adjustable     | :math:`E_i`, imaginary energy shift.               |
    +-----------------+-----------------+----------------------------------------------------+
    |   k             |  Output array   | :math:`k`, photo-electron wavenumber               |
    +-----------------+-----------------+----------------------------------------------------+
    |   chi           |  Output array   | :math:`\chi`, the EXAFS                            |
    +-----------------+-----------------+----------------------------------------------------+
    |   chi_imag      |  Output array   | :math:`\rm{Im}(\chi)`, imaginary EXAFS             |
    +-----------------+-----------------+----------------------------------------------------+
    |   p             |  Output array   | :math:`p`, complex photo-electron wavenumber       |
    +-----------------+-----------------+----------------------------------------------------+
    |   _feffdat      |  Group          | a Group containing raw data from *feffNNNN.dat*    |
    +-----------------+-----------------+----------------------------------------------------+


..  function:: feffpath(filename, label=None, s02=None, degen=None, e0=None, deltar=None, sigma2=None, ...)

    create a FeffPath Group from a *feffNNNN.dat* file.

    :param filename:  name (full path of) *feffNNNN.dat* file
    :param label:     label for path   [file name]
    :param degen:     path degeneracy, :math:`N` [taken from file]
    :param s02:       :math:`S_0^2`    value or parameter [1.0]
    :param e0:        :math:`E_0`      value or parameter [0.0]
    :param deltar:    :math:`\delta R` value or parameter [0.0]
    :param sigma2:    :math:`\sigma^2` value or parameter [0.0]
    :param third:     :math:`c_3`      value or parameter [0.0]
    :param fourth:    :math:`c_4`      value or parameter [0.0]
    :param ei:        :math:`E_i`      value or parameter [0.0]
    :returns: a FeffPath Group.

For all the options described above with **value or parameter** either a
numerical value or a Parameter (as created by :func:`_math.param`) can be given.


:func:`path2chi` and :func:`ff2chi`: Generating :math:`\chi(k)` for a FeffPath
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: path2chi(path, paramgroup=None, kmax=None, kstep=0.05, k=None)

    calculate :math:`\chi(k)` for a single Feff Path.

    :param path:        a FeffPath Group
    :param paramgroup:  a Parameter Group for calculating Path Parameters [``None``]
    :param kmax:        maximum :math:`k` value for :math:`\chi` calculation [20].
    :param kstep:       step in :math:`k` value for :math:`\chi` calculation [0.05].
    :param k:           explicit array of :math:`k` values to calculate :math:`\chi`.
    :returns: ``None``

If ``k`` is specified, that will be used as the set of :math:`k` values at which
to calculate :math:`\chi`.  If not given, the values of ``kstep`` and ``kmax``
will be used to construct a uniformly-spaced array of :math:`k` values starting
at 0 and extending to (and including) ``kmax``.

The calculated :math:`\chi` array is placed in the Feff Path Group ``path`` as
``path.chi``.  In addition calculated arrays for :math:`k`, :math:`p`, and
:math:`\rm{Im}(\chi)` are placed in the variables ``path.k``, ``path.p``, and
``path.chi_imag``, respectively.  See :ref:`xafs-exafsequation_sec` for the
detailed definitions of the quantities.

If specified, ``paramgroup`` is used as the Parameter Group -- the group used
for evaluating parameter expressions (ie, constraints using named variables).
This is similar to the use in REFERENCE HERE.

..  function:: ff2chi(pathlist, paramgroup=None, group=None, k=None, kmax=None, kstep=0.05)

    sum the :math:`\chi(k)` for a list of FeffPath Groups.

    :param pathlist:    a list of FeffPath Groups
    :param paramgroup:  a Parameter Group for calculating Path Parameters [``None``]
    :param group:       a Group to which the outputs are written  [``None``]
    :param kmax:        maximum :math:`k` value for :math:`\chi` calculation [20].
    :param kstep:       step in :math:`k` value for :math:`\chi` calculation [0.05].
    :param k:           explicit array of :math:`k` values to calculate :math:`\chi`.
    :returns: ``None``

This essentially calls :func:`path2chi` for each of the paths in the
``pathlist`` and writes the resulting arrays for :math:`k` and :math:`\chi` the
sum of :math:`\chi` for all the paths) to ``group.k`` and ``group.chi``.

.. index:: Feff.dat File Group

.. _xafs-feffdat_sec:

The Feff.Dat File Group
~~~~~~~~~~~~~~~~~~~~~~~~~~

Each FeffPath Group will have a ``_feffdat`` sub-group which contains the results of the Feff
calculation.  Many of these (including the arrays of data) are used for the calculations of
:math:`\chi(k)` for that Path, while others (such as ``geom`` and ``nleg``) are copied into the
FeffPath Group, and others still (such as ``exch`` and ``rnorman``) are left only in the
``_feffdat`` Group, though they may be used for further study.

As with the FeffPath Group, this Group has an expected set of components that
should be treated as read-only.

.. _xafs-feffdat_table:

    Table of Feff.dat components.  Listed here is the component read from
    the Feff.dat file and stored in the ``_feffdat`` group for each FeffPath.

    ================= =====================================================================
     attribute          description
    ================= =====================================================================
       amp               array: total amplitude,   :math:`F_{\rm eff}(k)`
       degen             path degeneracy (coordination number)
       edge              energy threshold relative to atomic valu (a poor estimate)
       exch              string describing electronic exchange model
       filename          File name
       gam_ch            core level energy width
       geom              path geometry: list of (Symbol, Z, ipot, x, y, z)
       k                 array: k values, :math:`k_{\rm feff}`
       kf                k value at Fermi level
       lam               array: mean-free path,  :math:`\lambda(k)`
       mag_feff          array: magnitude of Feff
       mu                Fermi level, eV
       pha               array: total phase shift, :math:`\delta(k)`
       pha_feff          array: scattring phase shift
       potentials        path potentials: list of (ipot, z, r_MuffinTin, r_Norman)
       real_phc          array: central atom phase shift
       red_fact          array: amplitude reduction factor
       rep               array: real part of p, :math:`p_{\rm real}(k)`
       rnorman           Norman radius
       rs_int            interstitial radius
       title             user title
       version           Feff version
       vint              interstitial potential
    ================= =====================================================================


The arrays from the data columns of the Feff data file break up the
amplitude and phase into two components (essentially as one for the central
atom and one for the scattering atoms) that are simply added together.
Thus ``amp`` = ``red_fact`` + ``mag_feff`` and the sum is used as
:math:`F_{\rm eff}(k)`.  Similarly, ``pha`` = ``real_phc`` + ``pha_feff``
and the sum is used as :math:`\delta(k)`.


.. index:: EXAFS Equation with Feff

.. _xafs-exafsequation_sec:

The EXAFS Equation using Feff and FeffPath Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now we are ready to write down the full EXAFS equation used for a Feff Path
using the terms defined above in the :ref:`Table of Feff Path Parameters
<xafs-pathparams_table>` and the :ref:`Table of Feff.Dat Components
<xafs-feffdat_table>`.  One of the trickier concepts is that we are
evaluating at experimental values of :math:`k` while the Feff calculation
is tabulated on its own set of :math:`k` values and we may need to apply an
energy shift of :math:`E_0` to the Feff calculation.  Thus, first we find
:math:`k` as

.. math::
    k = \sqrt{k_{\rm feff}^2  - {2m_e E_0}/{\hbar^2} }

Next, we note that


Example:  Reading a FEFF file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here we simply read a *feffNNNN.dat* file and manipulate its contents.

Example:  Adding FEFF files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now, we add some FEFF files together, applying path parameters.x
