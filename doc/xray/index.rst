.. _xraydb-chapter:

=====================
X-ray Databases
=====================

.. module:: _xray
   :synopsis: X-ray Properties

An important aspect of x-ray spectroscopies and scattering analysis is
having access to tabulated values for x-ray properties of various elements
and compounds.  Larch provides several functions to access these x-ray
properties.  These include basic atomic properties like atomic number and
mass, tabulated values of characteristic energies and transition
probabilites for core electron levels, absorption cross-sections, elastic
scattering terms, and anomalous scattering corrections.

Much of the speectroscopic data comes from the compilation of Elam, Ravel
and Sieber [ElamTables]_.  The core-hole widths for excited electronic
levels comes from Keski-Rahkonen and Krause [KeskiKrause]_, while elastic
x-ray scattering data, f0(q), is derived from Waasmaier and Kirfel
[WaasmaierKirfel]_.  Anomalous cross-sections from Cromer and Liberman
[CromerLiberman]_ (as implemented by Brennan and Cowan [BrennanCowan]_ )
are provided.  In addition, Chantler's [Chantler]_ values for absorption
cross-sections and anomalous x-ray scattering factors are available.
Except for the anomalous cross-section data from Cromer and Liberman (which
is implemented using the Fortran routine by Brennan and Cowan with slight
modifications), the data is accessed through a portable SQLite3 database
file.  This implementation was originally done by Darren Dale from CHESS
(see https://github.com/praxes/elam_physical_reference), with some
additions and alterations made for Larch.

The :ref:`Table of X-ray data functions <xraydb-funcs_table>` gives a brief
description to the available functions for accessing these data.  More
detailed descriptions of function arguments, returned values, and so on are
then given.

.. index:: X-ray data resources
.. _xraydb-funcs_table:

    Table of X-ray data functions.  These functions calculate and return some element-specific
    properties.  Except where noted, the first argument can either be a atomic number or valid
    atomic symbol (case insensitive).  Data for elements with atomic number > 92 may not be
    available and when provided may not be very reliable.  Except where noted, the data comes from
    Elam, Ravel, and Sieber.

     ========================== =======================================================
      function                    description
     ========================== =======================================================
      :func:`atomic_number`      atomic number from symbol
      :func:`atomic_symbol`      atomic symbol from number
      :func:`atomic_mass`        atomic mass
      :func:`atomic_density`     atomic density (for pure element)
      :func:`xray_edges`         list of x-ray edges data for an element
      :func:`xray_edge`          xray edge data for a particular element and edge
      :func:`xray_lines`         list of x-ray emission line data for an element
      :func:`xray_line`          xray emission line data for an element and line
      :func:`core_width`         core level width for an element and edge
      :func:`mu_elam`            absorption cross-section
      :func:`coherent_xsec`      coherent cross-section
      :func:`incoherent_xsec`    incoherent cross-section
      :func:`ck_probability`     Coster-Kronig probability
      :func:`f0`                 elastic scattering factor (Waasmaier and Kirfel)
      :func:`f0_ions`            list of valid "ions" for :func:`f0` (Waasmaier and Kirfel)
      :func:`chantler_energies`  energies of tabulation for Chantler data (Chantler)
      :func:`f1_chantler`        f'  anomalous factor  Chantler)
      :func:`f2_chantler`        f'' anomalous factor (Chantler)
      :func:`mu_chantler`        absorption cross-section (Chantler)
      :func:`f1f2_cl`            f' and f'' anomalous factors (Cromer and Liberman)
     ========================== =======================================================

.. function:: atomic_number(symbol)

    return the atomic number from an atomic symbol ('H', 'C', 'Fe', etc)


.. function:: atomic_symbol(z)

    return the atomic symbol from an atomic number



.. rubric:: References

.. [BrennanCowan] S. Brennan and P. L. Cowen, *A suite of programs for
    calculating x-ray absorption, reflection, and diffraction performance
    for a variety of materials at arbitrary wavelengths*, Review of
    Scientific Instruments **63**, pp850--853 (1992) [`doi link <http://dx.doi.org/10.1063/1.1142625>`_].

.. [Chantler]   C. T. Chantler, Journal of Physical and  Chemica Reference
    Data **24**, p71 (1995)

.. [CromerLiberman] D. T. Cromer and D. A. Liberman *Anomalous dispersion
    calculations near to and on the long-wavelength side of an
    absorption-edge*, Acta Crystallographica **A37**, pp267-268 (1981)
    [`doi link <http://dx.doi.org/10.1107/S0567739481000600>`_].

.. [ElamTables]   W. T. Elam, B. D. Ravel and J. R. Sieber, Radiation
    Physics and Chemistry **63** (2), pp121--128 (2002)
    [`doi link <http://dx.doi.org/10.1016/S0969-806X(01)00227-4>`_].

.. [KeskiKrause]  O. Keski-Rahkonen and M. O. Krause, *Total and Partial
    Atomic-Level Widths*, Atomic Data and Nuclear Data Tables **14**,
    pp139-146 (1974)

.. [WaasmaierKirfel]  D. Waasmaier and A. Kirfel, *New Analytical
    Scattering Factor Functions for Free Atoms and Ions*,
    Acta Crystallographica **A51**, pp416-431 (1995)
    [`doi link <http://dx.doi.org/10.1107/S0108767394013292>`_].

