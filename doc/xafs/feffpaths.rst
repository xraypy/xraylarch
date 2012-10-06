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


..  function:: feffpath(filename, label=None, s02=None, degen=None, e0=None, deltar=None, sigma2=None, ...)

    create a Feff Path object from a *feffNNNN.dat* file.


..  function:: ff2chi(pathlist, paramgroup=None, group=None, k=None, kmax=None, kstep=0.05)

    sum a set of Feff Paths


Feff Path Object
~~~~~~~~~~~~~~~~~~

   Table of Feff Path Parameters, listed in the :ref:`Table of Feff Path Parameters <xafs-pathparams_table>`.

.. index:: Feff Path Parameters
.. _xafs-pathparam_table:

    Table of Feff Path Parameters

       =================== =========================================================
        parameter name          description
       =================== =========================================================
        reff                nominal path length
        nleg                number of path legs (1+number of scatterers)
	geom                path geometry: list of (symbol, ipot, x, y, z)
        degen               path degeneracy
        label               path description
        s02                 :math:`S_0^2`
        e0                  e0
        deltar              deltar
        sigma2              sigma2
        third               third
        fourth              fourth
        ei                  ei
       =================== =========================================================


FEFF Data structure
~~~~~~~~~~~~~~~~~~~~~~


<feffdat.FeffDatFile object at 0x7318f90>
larch> dir(a._dat)
['__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__', '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'amp', 'degen', 'edge', 'exch', 'filename', 'gam_ch', 'geom', 'k', 'kf', 'lam', 'mag_feff', 'mu', 'nleg', 'pha', 'pha_feff', 'potentials', 'read', 'real_phc', 'red_fact', 'reff', 'rep', 'rnorman', 'rs_int', 'title', 'version', 'vint']


Example:  Reading a FEFF file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here we simply read a *feffNNNN.dat* file and manipulate its contents.

Example:  Adding FEFF files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now, we add some FEFF files together, applying path parameters.x
