.. _xafs-chapter:

=======================
XAFS Analysis
=======================

One of the primary motivations for Larch was processing XAFS data.  Larch
was originally conceived to be version 2 of Ifeffit (:cite:ts:`ifeffit`),
replacing and expanding all the XAFS analysis capabilities of that package.

This replacement is essentially complete, with all the main functionality
of Ifeffit available in Larch.  There may still be a few minor features of
Ifeffit that are not yet available, and some features to port from Athena
(:cite:ts:`athena`) back to the core library.   There are some slight
differences in implementation details, such that slightly different
numerical results are obtained.  Importantly, some new features are already
available with Larch that were not available with Ifeffit 1.2 and some
small errors in Ifeffit 1.2 have been fixed.

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

There is a set of conventions used to help organize the output arrays from
the XAFS functions that are worth understanding.  These are really only
conventions, but can make using the XAFS function a much more pleasant
experience.

First, all the XAFS functions here take a **group** argument, which is used
as the group into which results are written.  There is also a special
group, ``_sys.xafsGroup`` that is used as the default group to write
outputs to if no **group** argument is supplied.  When an an explicit
**group** argument is given, ``_sys.xafsGroup`` is set to this group.  This
means that when working with a set of XAFS data all contained within a
single group (which is expected to be the normal case), the **group**
argument does not need to be typed repeatedly.

.. index:: First Argument Group convention

Second, while the XAFS functions are generally meant to take arrays of data
as the first two arguments, they allow the first argument to be a Group if
that Group has the expected named arrays.  This convention, known as the
**First Argument Group** convention is worth understanding and using.  For
example, the :func:`autobk` function generally expects the first argument
to be an array of energy values and the second to be an array of absorbance
values.  But a normal use case would look like::

     autobk(dat.energy, dat.mu, group=dat, rbkg=1, ....)

This can be abbreviated as::

     autobk(dat, rbkg=1, ....)

That is, as long as the Group ``dat`` has an energy array named ``energy``
and absorbance array named ``mu`` the two forms above are equivalent.
This nearly makes the Larch XAFS functions be object-oriented, or in this
case, **Group oriented**.


Further details of the various XAFS functionals are described in the sections
listed below.

.. toctree::
   :maxdepth: 2

   preedge
   autobk
   utilities
   xafsft
   feffpaths
   feffit
   wavelets
