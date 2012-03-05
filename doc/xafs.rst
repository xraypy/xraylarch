===============================
XAFS Analysis with Larch
===============================

One of the primary motivations for Larch was processing XAFS data.  In
fact, Larch is intended as version 2 of the Ifeffit engine, replacing and
expanding all the XAFS analysis capabilities of that package.  As of this
writing, this replacement is well under way, but not complete.

As with most analysis of scientific data, XAFS Analysis can generally be
broken into a few separate steps.  For XAFS these are:

  1. Reading in raw data.
  2. Making corrections to the data, and converting to  :math:`\mu(E)`
  3. Pre-edge background removal and Normalization
  4. Interpreting normalized mu(E) as XANES spectra
  5. Post-edge background removal, conversion to :math:`\chi(k)`
  6. XAFS Fourier Transform to :math:`\chi(R)`
  7. Reading and processing FEFF Paths from external files.
  8. Fitting XAFS :math:`\chi(k)` to FEFF paths.

As of this writing, many of these steps are supported in Larch.  All the
XAFS-specific functions are kept in the :data:`_xafs` Group, and can be
easily accessed as this is in the default search path.

.. module:: _xafs
   :synopsis: Basic XAFS Functions

..  function:: pre_edge(energy, mu, group=None, ...)

..  function:: find_e0(energy, mu, group=None, ...)


..  function:: autobk(energy, mu, group=None, ...)


..  function:: ftwindow(k, ...)


..  function:: xafsft(k, chi, group=None, ...)





