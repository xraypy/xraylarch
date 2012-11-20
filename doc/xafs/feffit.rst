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

    execute a Feffit fit.

    :param paramgroup:  group containing parameters for fit
    :param datasets:   Feffit Dataset group or list of Feffit Dataset group.
    :param rmax_out:   maximum :math:`R` value to calculate output arrays.
    :param path_output:  Flag to set whether all Path outputs should be written.
    :returns:         a fit results group.

    The ``paramgroup`` is a group containing all fitting parameters for the
    model.  The ``datasets`` argument can be either a single Feffit Dataset
    as created by :func:`feffit_dataset` or a list of them.  If
    ``path_outputs==True``, all Feff Paths in the fit will be separately
    Fourier transformed.

    When the fit is completed, the returned value will be a group
    containing three objects:

      1. ``datasets``: an array of FeffitDataSet groups used in the fit.

      2. ``params``: This will be identical to the input parameter group.

      3. ``fit``: an object which points to the low-level fit.

    In addition, the output statistics listed below in :ref:`Table of
    Feffit Output Statistics <xafs-feffit_stats_table>`.  will be written
    the ``paramgroup`` group.  Since each varied and constrained parameter
    will also have best-values and estimated uncertainties, this allows the
    parameter group to be considered the principle group for a particular
    fit -- it holds the variable parameters and statistical results needed
    to compare two fits.

    On output, a new sub-group called ``model`` will be created for each
    Feffit Dataset. This will parallel the ``data`` group, in the sense
    that it will have output arrays listed in the :ref:`Table of Feffit
    Output Arrays <xafs-feffit_arrays_table>`.

    If ``path_outputs==True``, all Feff Paths in the fit will be separately
    Fourier transformed., with the result being put in the corresponding
    FeffPath group.

    A final note on the outputs of :func:`feffit`: the ``param`` sub-group in
    the output is truly identical to the input ``paramgroup``.  It is not a
    copy but points to the same group of values (see
    :ref:`tutor-objectids_sec`).

.. index:: Feffit Output Statistics
.. _xafs-feffit_stats_table:

    Table of Feffit Output Statistics.  These values will be written to the
    ``paramgroup`` group. Listed here are the group component name and a
    description of its content.  Many of these are described in more detail
    in :ref:`Fit Results and Outputss <fitting-results-sec>`

        ================= =====================================================================
         component name     description
        ================= =====================================================================
           chi_reduced      reduced chi-square statistic.
           chi_square       chi-square statistic.
           covar            covariance matrix.
           covar_vars       list of variable names for rows and colums of covariance matrix.
           errorbars        Flag whether error bars could be calculated.
           fit_details      group with additional fit details.
           message          output message from fit.
           nfree            number of degrees of freedom in fit.
           nvarys           number of variables in fit.
        ================= =====================================================================

.. index:: Feffit Output Arrays
.. _xafs-feffit_arrays_table:

    Table of Feffit Output Arrays.  The following arrays will be written
    into the ``data`` and ``model`` sub-group for each dataset. The arrays
    will be created using the Path Parameters used in the most recent fit
    and the Feffit Transform group.  Many of these arrays have names
    following the conventions for :func:`xftf` in section on :ref:`Fourier
    Transforms for XAFS <xafs-ft_sec>`.

        ================= =====================================================================
         array name        description
        ================= =====================================================================
            k                  wavenumber array of :math:`k`.
            chi                :math:`\chi(k)`.
            kwin               window :math:`\Omega(k)` (length of input chi(k)).
            r                  uniform array of :math:`R`, out to ``rmax_out``.
            chir               complex array of :math:`\tilde\chi(R)`.
            chir_mag           magnitude of :math:`\tilde\chi(R)`.
            chir_pha           phase of :math:`\tilde\chi(R)`.
            chir_re            real part of of :math:`\tilde\chi(R)`.
            chir_im            imaginary part of :math:`\tilde\chi(R)`.
        ================= =====================================================================


:func:`feffit_report`
~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: feffit_report(fit_result)

    return a printable report from a Feffit fit.

    :param fit_result:  output group from :func:`feffit`.


Example 1: Simple fit with 1 Path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We start with a fairly minimal example, fitting spectra read from a data
file with a single Feff Path.


.. literalinclude:: ../../examples/feffit/doc_feffit1.lar


This simply follows the essential steps:

 1. A group of parameters ``pars`` is defined.  Note that you can include
 upper and/or lower bounds and mix the use of :func:`_math.guess` and
 :func:`_math.param`.

 2. A Feff Path is defined with :func:`feffpath`, as discussed in the
 previous section. Here we assign each of the Path Parameters to the name
 of one of the fitting parameters.  More complex expressions and relations
 can be used, but for this example, we're keeping it simple.

 3. A Feffit Transform is created with :func:`feffit_transform`, which
 essentially sets the Fourier transform parameters and fit ranges.

 4. A Feffit Dataset is created with :func:`feffit_dataset`.  To begin the
 fit, this includes a ``data`` group, a ``transform`` group, and a
 ``pathlist``,  which is a list of FeffPaths.

 5. The fit is run with :func:`feffit`, and the output group is saved.
 This output group is used by :func:`feffit_report` to generate a fit
 report (shown below).

 6. Plots are made from the dataset, using rather long-winded :func:`plot`
 commands.

running this example prints out the following report::

    =================== FEFFIT RESULTS ====================
    [[Statistics]]
       npts, nvarys       = 106, 4
       nfree, nfcn_calls  = 102, 31
       chi_square         = 5407.674717
       reduced chi_square = 53.016419

    [[Data]]
       n_independent      = 14.260
       eps_k, eps_r       = 0.000178, 0.008480
       fit space          = r
       r-range            = 1.400, 3.000
       k-range            = 3.000, 17.000
       k window, dk       = kaiser, 3.000
       k-weight           = 2
       paths used in fit  = ['feffcu01.dat']

    [[Variables]]
       amp            =  0.935940 +/- 0.101085   (init=  1.000000)
       del_e0         =  3.901883 +/- 1.318563   (init=  0.100000)
       del_r          = -0.005843 +/- 0.006784   (init=  0.000000)
       sig2           =  0.008705 +/- 0.000795   (init=  0.002000)

    [[Correlations]]    (unreported correlations are <  0.100)
       amp, sig2            =  0.928
       del_e0, del_r        =  0.920
       del_r, sig2          =  0.161
       amp, del_r           =  0.141

    [[Paths]]
       feff.dat file = feffcu01.dat
              Atom     x        y        z     ipot
               Cu    0.0000,  0.0000,  0.0000  0 (absorber)
               Cu    0.0000, -1.8016,  1.8016  1
         reff   =  2.54780
         Degen  =  12.00000
         S02    =  0.93594 +/-  0.10108
         E0     =  3.90188 +/-  1.31856
         R      =  2.54196 +/-  0.00678
         deltar = -0.00584 +/-  0.00678
         sigma2 =  0.00871 +/-  0.00080

    =======================================================

and generates the plots shown below


.. _xafs_fig12:

  .. image:: ../images/feffit_example1.png
     :target: ../_images/feffit_example1.png
     :width: 48 %
  .. image:: ../images/feffit_example2.png
     :target: ../_images/feffit_example2.png
     :width: 48 %

  Figure 12. Results for Feffit for a simple 1-shell fit to a
  spectrum from Cu metal.

This is a pretty good fit to the first shell of Cu metal, and shows the
basic mechanics of fitting XAFS data to Feff Paths.  There are several
things that might be added to this for modeling more complex XAFS data,
including adding more paths to a fit, including multiple-scattering paths,
simultaneously modeling more than one data set, and building more complex
fitting models.  We'll get to these in the following examples.

But first, a small detour.  The plotting commands in the above example for
plotting :math:`\chi(k)` and
:math:`\chi(R)` for data and model will be useful for the other examples as
well, so we'll create a slightly generalized function to make such plots
and put it into a separate file, *doc_macros.lar*.  This will look like
this:

.. literalinclude:: ../../examples/feffit/doc_macros.lar

and we can then replace the plot commands in the script above with::

    run('doc_macros.lar')
    show_chifit(dset, title='First shell fit to Cu')

We'll use this in the examples below.



Example 2: Fit 1 dataset with 3 Paths
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We'll continue with the Cu data set, and add more paths.  This is fairly
straightforward, though a main concern of XAFS analysis comes up that we
should address.  This is that there simply is not enough freedom in the
XAFS signal to measure all the Path Parameters independently.   Thus we
need to be able to apply constraints to the Path Parameters.

Here, for example, we apply the same amplitude reduction factor and the
same :math:`E_0` shift to all Paths.  We also scale the change in distance
by an expansion factor :math:`\alpha`, using the builtin value of half-path
distance, ``reff``.

.. literalinclude:: ../../examples/feffit/doc_feffit2.lar

Here we simply create ``path2`` and ``path3`` using nearly the same parameters
as for ``path1`` -- only ``sigma2`` is allowed to vary independently for
each path.  Note that we also increased the :math:`R` range for the fit.

The output for this fit is being::

    =================== FEFFIT RESULTS ====================
    [[Statistics]]
       npts, nvarys       = 146, 6
       nfree, nfcn_calls  = 140, 50
       chi_square         = 7701.538999
       reduced chi_square = 55.010993

    [[Data]]
       n_independent      = 19.608
       eps_k, eps_r       = 0.000178, 0.008480
       fit space          = r
       r-range            = 1.400, 3.600
       k-range            = 3.000, 17.000
       k window, dk       = kaiser, 3.000
       k-weight           = 2
       paths used in fit  = ['feff0001.dat', 'feff0002.dat', 'feff0003.dat']

    [[Variables]]
       alpha          = -0.001970 +/- 0.002731   (init=  0.000000)
       amp            =  0.933500 +/- 0.104437   (init=  1.000000)
       del_e0         =  4.106844 +/- 1.337739   (init=  0.100000)
       sig2_1         =  0.008675 +/- 0.000826   (init=  0.002000)
       sig2_2         =  0.012120 +/- 0.002648   (init=  0.002000)
       sig2_3         =  0.006568 +/- 0.008944   (init=  0.002000)

    [[Correlations]]    (unreported correlations are <  0.100)
       amp, sig2_1          =  0.928
       alpha, del_e0        =  0.921
       amp, sig2_2          =  0.323
       sig2_1, sig2_2       =  0.301
       amp, sig2_3          =  0.272
       sig2_1, sig2_3       =  0.269
       alpha, sig2_1        =  0.185
       del_e0, sig2_3       =  0.182
       alpha, amp           =  0.166
       alpha, sig2_3        =  0.153

    [[Paths]]
       feff.dat file = feff0001.dat
              Atom     x        y        z     ipot
               Cu    0.0000,  0.0000,  0.0000  0 (absorber)
               Cu    0.0000, -1.8016,  1.8016  1
         reff   =  2.54780
         Degen  =  12.00000
         S02    =  0.93350 +/-  0.10444
         E0     =  4.10684 +/-  1.33774
         R      =  2.54278 +/-  0.00696
         deltar = -0.00502 +/-  0.00696
         sigma2 =  0.00868 +/-  0.00083

       feff.dat file = feff0002.dat
              Atom     x        y        z     ipot
               Cu    0.0000,  0.0000,  0.0000  0 (absorber)
               Cu   -3.6032,  0.0000,  0.0000  1
         reff   =  3.60320
         Degen  =  6.00000
         S02    =  0.93350 +/-  0.10444
         E0     =  4.10684 +/-  1.33774
         R      =  3.59610 +/-  0.00984
         deltar = -0.00710 +/-  0.00984
         sigma2 =  0.01212 +/-  0.00265

       feff.dat file = feff0003.dat
              Atom     x        y        z     ipot
               Cu    0.0000,  0.0000,  0.0000  0 (absorber)
               Cu    1.8016, -1.8016,  0.0000  1
               Cu    1.8016,  0.0000, -1.8016  1
         reff   =  3.82180
         Degen  =  48.00000
         S02    =  0.93350 +/-  0.10444
         E0     =  4.10684 +/-  1.33774
         R      =  3.81427 +/-  0.01044
         deltar = -0.00753 +/-  0.01044
         sigma2 =  0.00657 +/-  0.00894

    =======================================================
