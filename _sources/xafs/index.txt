.. _xafs-chapter:

=======================
XAFS Analysis
=======================

One of the primary motivations for Larch was processing XAFS data.  Larch
was originally conceived to be version 2 of Ifeffit, replacing and
expanding all the XAFS analysis capabilities of that package.

As of this writing (Feb, 2013), this replacement is essentially complete,
with all the main functionality of Ifeffit 1 available in Larch.  There may
still be a few minor features of Ifeffit that are not yet available.  There
are some slight differences in implementation details, such that slightly
different numerical results are obtained.  Importantly, some new features
are already available with Larch that were not available with Ifeffit 1.2
and some small errors in Ifeffit 1.2 have been fixed.

XAFS Analysis can generally be broken into a few separate steps:

  1. Reading in raw data.
  2. Making corrections to the data, and converting to  :math:`\mu(E)`
  3. Pre-edge background removal and normalization.
  4. Interpreting normalized mu(E) as XANES spectra
  5. Post-edge background removal, conversion to :math:`\chi(k)`
  6. XAFS Fourier Transform to :math:`\chi(R)`
  7. Reading and processing FEFF Paths from external files.
  8. Fitting XAFS :math:`\chi(k)` to a sum of FEFF paths.

Broadly speaking, Larch can do all of these steps.


.. module:: _xafs
   :synopsis: Basic XAFS Functions


The XAFS-specific functions in Larch are kept in the :data:`_xafs` Group,
which can be easily accessed, as this is in the default search path.  The
XAFS functions described here represent the general steps outlined above.
Each of these functions produce several scalar values and arrays for their
results.  Indeed, many of the functions have several output arrays.  In
addition, several of the functions produce groups containing details of fit
results.

To accomodate and help organize the output arrays from these functions, the
XAFS functions here take a **group** argument, which takes a group into
which results are written.  There is a special group, ``_sys.xafsGroup``
that is used as the default group.  When any of these functions gives an
explicit **group** argument, ``_sys.xafsGroup`` is set to this group.  When
the **group** argument is omitted, outputs will be written to the most
``_sys.xafsGroup``, that is, the most recently used group.  For many
analysis scripts where a single data set is being analyzed, using a single
main data group and using the default ``_sys.xafsGroup`` can be convenient.
For anything more complicated than a basic script, explicitly specifying
**group** is recommended.

Further details of the various XAFS functionals are described in the sections
listed below.

.. toctree::
   :maxdepth: 2

   preedge
   autobk
   xafsft
   feffpaths
   feffit
