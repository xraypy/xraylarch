.. _xafs-chapter:

=======================
XAFS Analysis
=======================

One of the primary motivations for Larch was processing XAFS data.  Larch
was originally conceived to be version 2 of Ifeffit, replacing and
expanding all the XAFS analysis capabilities of that package.

As of this writing (Oct, 2012), this replacement is approximately complete,
in that essentially all the functionality of Ifeffit 1 is available in
Larch.  There are some slight differences in implementation details, such
that slightly different numerical results are obtained.  Importantly, some
new features are already available with Larch that were not available with
Ifeffit 1.2 and some small errors in Ifeffit 1.2 have been fixed.


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
which can be easily accessed, as this is in the default search path.  Note
that many of the XAFS functions take a **group** argument, which is a group
into which resulting data are written.  That is, many of the functions have
several output arrays and groups.  Many of the functions will return
the most fundamental result, but this will be a minimal subset of the
possible outputs that would go into the supplied **group**.

The XAFS functionality is described in further detail in the sections
listed below.

.. toctree::
   :maxdepth: 2

   preedge
   autobk
   xafsft
   feffpaths
   feffit
