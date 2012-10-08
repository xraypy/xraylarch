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
reads FEFF *feffNNNN.dat* file into a larch FeffPath Group.

For many uses a Feff Path can be treated as a "black box" which holds the
EXAFS information for a scattering path, and simply setting the adjustable
Path Parameters and passing around these Groups is sufficient for
simulating and fitting EXAFS spectra.  For some cases, however, it can be
helpful to inspect and study the details of the Feff Path.  This ability is
readily available with Larch, as all the data from the Feff Path is exposed
and available.

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

The returned FeffPath Group is a regular Larch Group, but with a set of
components that are expected to be in place and holding the right values to
describe a Feff Path.  These are discussed in more detail below in
:ref:`xafs-feffpathgroup_sec`.

For all the options described above with **value or parameter** either a
numerical value or a Parameter (as created by :func:`_math.param`) can be given.

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
``path.chi``.  In addttion calculated arrays for :math:`k`, :math:`p`, and
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

.. index:: FeffPath Groups
.. _xafs-feffpathgroup_sec:

FeffPath Groups
~~~~~~~~~~~~~~~~~~

The functions listed above, as well as :func:`feffit` discussed in the next
session, use FeffPath Groups as the basic object holding information
about a Feff Path, including the photo-electron scattering amplitudes and
phase-shifts needed to describe the EXAFS for that Path.

A FeffPath is a regular Larch Group, but with a set of components that are hold
values to describe an EXAFS Scattering Path, and allow :math:`\chi(k)` to be
calculated for that Path.  Thus, a FeffPath needs to have several components in
place and holding the expected values so that the calculations can be done
correctly.  Specifically, a FeffPath Group has the components listed in the
:ref:`Table of Feff Path Parameters <xafs-pathparams_table>`.  This includes the
*Adjustable Numerical Path Parameters* -- the values of which can be changed to
affect the calculated EXAFS for the Path -- as well as the arrays for :math:`k`
and :math:`\chi` and several other attributes.

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

Due to Larch's flexibility, it is possible to delete, overwrite, or put inappropriate values into
these variables.  This can cause all sorts of trouble and care should be taken to not do this.

.. index:: Feff.dat File Group

.. _xafs-feffdat_sec:

The Feff.Dat File Group
~~~~~~~~~~~~~~~~~~~~~~~~~~

Each FeffPath Group will have a ``_feffdat`` sub-group which contains the results of the Feff
calculation.  Many of these (including the arrays of data) are used for the calculations of
:math:`\chi(k)` for that Path, while others (such as ``geom`` and ``nleg``) are copied into the
FeffPath Group, and others still (such as ``exch`` and ``rnorman``) are left only in the
``_feffdat`` Group, though they may be used for further study.

As with the FeffPath Group, this Group has a The full list

larch> dir(a._dat)
['__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__', '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'amp', 'degen', 'edge', 'exch', 'filename', 'gam_ch', 'geom', 'k', 'kf', 'lam', 'mag_feff', 'mu', 'nleg', 'pha', 'pha_feff', 'potentials', 'read', 'real_phc', 'red_fact', 'reff', 'rep', 'rnorman', 'rs_int', 'title', 'version', 'vint']


.. index:: EXAFS Equation with Feff

.. _xafs-exafsequation_sec:

The EXAFS Equation using Feff and FeffPath Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now we are ready to write down the full EXAFS equation used for a Feff
Path.



Example:  Reading a FEFF file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here we simply read a *feffNNNN.dat* file and manipulate its contents.

Example:  Adding FEFF files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now, we add some FEFF files together, applying path parameters.x
