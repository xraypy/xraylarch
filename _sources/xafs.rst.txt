.. _xafs-chapter:

=======================
XAFS Analysis
=======================

One of the primary motivations for Larch was processing XAFS data.  Larch
was originally conceived to be version 2 of Ifeffit :cite:`ifeffit`,
replacing and expanding all the XAFS analysis capabilities of that package.
XAFS Analysis can generally be broken into a few separate steps:
This replacement is essentially complete insofar as all the main
functionality of Ifeffit is available in Larch.  There may still be a few
minor features of Ifeffit that are not yet available, and some
functionality to port from Athena :cite:`athena` back to the core
library.  In addition, there are some minor differences in implementation
details, so that slightly different numerical results may be obtained.
Importantly, several features are available with Larch that were not
available with Ifeffit 1.2 and some small errors in Ifeffit 1.2 have been
fixed.

  1. Reading in raw data.
  2. Making corrections to the data, and converting to  :math:`\mu(E)`
  3. Pre-edge background removal and normalization.
  4. Interpreting normalized :math:`mu(E)` as XANES spectra
  5. Post-edge background removal, conversion to :math:`\chi(k)`
  6. XAFS Fourier Transform to :math:`\chi(R)`
  7. Reading and processing FEFF Paths from external files.
  8. Fitting XAFS :math:`\chi(k)` to a sum of FEFF paths.

The XAFS-specific functions in Larch follow these general steps.  They are
all kept in the :data:`_xafs` Group, which can be easily accessed, as this
is in the default search path.


:synopsis: Basic XAFS Functions

.. toctree::
   :maxdepth: 2

   xafs_utilities
   xafs_preedge
   xafs_xanes
   xafs_autobk
   xafs_fourier
   xafs_wavelets
   xafs_feffpaths
   xafs_feffit
   xafs_diffkk

