==============================================
XAFS: Fitting XAFS to Feff Paths
==============================================

.. module:: _xafs
   :synopsis: XAFS Feff Path and fitting functions

Fitting XAFS data with structural models based on Feff calculations is a
primary motivation for Larch.  In this section, we describe how to set up a
fitting model to fit a set of FEFF calculations to XAFS data.  Many parts
of the documentation so far have touched on important aspects of this
process, and those sections will be referenced here.

The basic approach is to create a model EXAFS :math:`\chi(k)` as a sum of
scattering paths that will be compared to experimentally derived
:math:`\chi(k)`.  The model will be parameterized in terms of Larch
Parameters defined by :func:`_math.param`.  A fit, using the same fitting
infrastructure as to :func:`_math.minimize` will be used to refine the
values of the variable parameters in the model.  To be clear, the Path
Parameters for all Feff Paths in the fits should be written in terms of
variable parameters help in a single parameter group.  The refinement will
be done by comparing the model and experimental :math:`\chi(k)` after a
*Transformation* based on the Fourier transforms in :ref:`xafs-ft_sec`.

The function :func:`feffit` is the principle function to do the fit of a
set of Feff paths to XAFS spectra.  This essentially runs
:func:`_math.minimize` with a parameter group, but with a built-in
objective function to calculate the fit residual.  This built-in objective
function calculates the residual as the difference of model and
experimental :math:`\chi(k)` for a list of *Datasets*.  Here, a *Feffit
Dataset* is an important concept that will allow us to easily extend
modeling to multiple data sets.

A *Feffit Dataset* has three principle components.  First, it has an
experimental data, :math:`\chi(k)`.  Second, it has a list of Feff paths --
:func:`ff2chi` will be used to calculate the model :math:`\chi(k)`.  Third,
it has a *Feffit Transform* group which holds the Fourier transform and
fitting ranges to select how the data and model are to be compared.  In
addition, a fit has a single parameter group, holding all the variable and
constrained parameters used by all the paths and data sets in a fit.

There are then 3 principle functions for setting up and executing
:func:`feffit`:

  1. :func:`feffit_transform` is used to create a Transform group,
     which holds the set of Fourier transform parameters.

  2. :func:`feffit_dataset` is used to create a Dataset group, which
     consists of the three components described above:

     a. a group holding experimental data (``k`` and ``chi``).
     b. a list of Feff paths.
     c. a Transform group.

  3. Finally, :func:`feffit` is run with a parameter group containing
     the variable and constrained Parameters for the fit, and a dataset
     or list of datasets groups.

:func:`feffit_transform`
~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: feffit_transform(fitspace='r', kmin=0, kmax=20, kweight=2, ...)

    create and return Feffit Transform group to be used in a Feffit dataset.

    :param fitspace: name of FT type for fit  ('r').
    :param kmin:     starting *k* for FT Window (0).
    :param kmax:     ending *k* for FT Window (20).
    :param dk:       tapering parameter for FT Window (4).
    :param dk2:      second tapering parameter for FT Window (None).
    :param window:   name of window type ('kaiser').
    :param nfft:     value to use for :math:`N_{\rm fft}` (2048).
    :param kstep:    value to use for :math:`\delta{k}` (0.05).
    :param kweight:  exponent for weighting spectra by :math:`k^{\rm kweight}` (2).
    :param rmin:     starting *R* for Fit Range and/or reverse FT Window (0).
    :param rmax:     ending *R* for Fit Range and/or reverse FT Window (10).
    :param dr:       tapering parameter for reverse FT Window 0.
    :param rwindow:  name of window type for reverse FT Window ('kaiser').
    :returns:        a Feffit Transform group

    The parameters stored in the returned group object will be used to
    control how the fit is performed.

:func:`feffit_dataset`
~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: feffit_dataset(data=None, pathlist=[], transform=None)

    create a Feffit Dataset group.

    :param data:      group containing experimental EXAFS (needs arrays ``k`` and ``chi``).
    :param pathlis:   list of FeffPath groups, as created from :func:`feffpath`.
    :param transform: Feffit Transform group.
    :returns:         a Feffit Dataset group.

    A Dataset group is pretty simple, initially consisting of ``data``, a
    ``pathlist``, and a ``transform``, though each of these can be complex.

    The value for ``data`` must be a group containing arrays ``k`` and
    ``chi`` (as determined :func:`_xafs.autobk` or some other procedure).
    If it contains a value (scalar or array) ``epsilon_k``, that will be
    used as the uncertainty in :math:`\chi(k)` for weighting the fit.
    Otherwise, the uncertainty in :math:`\chi(k)` will be estimated
    automatically.  The ``pathlist`` is a list of Feff Paths, each of which
    can have its Path Parameters written in terms of fit parameters (see
    the final example in the previous section).  This list of paths will be
    sent to :func:`ff2chi` to caclulate the model :math:`\chi` to compare
    to the experimental data.  Finally, ``transform`` is a Feffit transform
    group, as defined above.

:func:`feffit`
~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: feffit(paramgroup, datasets, rmax_out=10, path_outputs=True)

    execute a Feffit fit.  This simply takes a parameter group, as does
    :func:`_math.minimize`, and a Feffit dataset or list of Feffit
    datasets.  If ``path_outputs==True``, all paths will be separately
    Fourier transformed, with the result being put in the corresponding
    FeffPath group.
