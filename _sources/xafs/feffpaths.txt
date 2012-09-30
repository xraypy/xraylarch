==============================================
XAFS: Reading and using Feff Paths
==============================================

.. module:: _xafs


For modeling EXAFS data, Larch relies heavily on calculations of
theoretical XAFS spectra using FEFF.  Being able to run FEFF and use its
results is thus of fundamental importance for using Larch for fitting EXAFS
spectra.  While a complete description of FEFF is beyond the scope of this
documentation, here we describe how to read the results from FEFF into
Larch.  The main interface for this is the :func:`feff_path` function that
reads FEFF *feffNNNN.dat* file into a larch FeffPath object.


..  function:: feff_path(filename...)

    create a Feff Path object


Feff Path Object
~~~~~~~~~~~~~~~~~~

Example:  Reading a FEFF file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here we simply read a *feffNNNN.dat* file and manipulate its contents.

