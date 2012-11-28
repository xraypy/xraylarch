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
    control how the fit is performed.  That is, the Transform group
    determines the Fourier transform parameters and fit space for a fit.
    All the arguments passed in will be stored as variables of the same
    name in the Feffit Transform group.  Several additional variables will
    be stored in this group as well, and are set once the group has been
    used to do some transforms.  These include:

      ================= =====================================================================
       component name        description
      ================= =====================================================================
         epsilon_k        estimated noise in the :math:`\chi(k)` data.
         epsilon_r        estimated noise in the :math:`\chi(R)` data.
         n_idp            estimated number of independent points in the data.
      ================= =====================================================================


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
            chir_re            real part of :math:`\tilde\chi(R)`.
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
       chi_square         = 5511.562862
       reduced chi_square = 54.034930

    [[Data]]
       n_independent      = 14.260
       eps_k, eps_r       = 0.000172, 0.008189
       fit space          = r
       r-range            = 1.400, 3.000
       k-range            = 3.000, 17.000
       k window, dk       = kaiser, 4.000
       k-weight           = 2
       paths used in fit  = ['feffcu01.dat']

    [[Variables]]
       amp            =  0.934846 +/- 0.101517   (init=  1.000000)
       del_e0         =  3.861891 +/- 1.323453   (init=  0.100000)
       del_r          = -0.006031 +/- 0.006754   (init=  0.000000)
       sig2           =  0.008698 +/- 0.000794   (init=  0.002000)

    [[Correlations]]    (unreported correlations are <  0.100)
       amp, sig2            =  0.928
       del_e0, del_r        =  0.920
       del_r, sig2          =  0.159
       amp, del_r           =  0.138

    [[Paths]]
       feff.dat file = feffcu01.dat
              Atom     x        y        z     ipot
               Cu    0.0000,  0.0000,  0.0000  0 (absorber)
               Cu    0.0000, -1.8016,  1.8016  1
         reff   =  2.54780
         Degen  =  12.00000
         S02    =  0.93485 +/-  0.10152
         E0     =  3.86189 +/-  1.32345
         R      =  2.54177 +/-  0.00675
         deltar = -0.00603 +/-  0.00675
         sigma2 =  0.00870 +/-  0.00079

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
plotting :math:`\chi(k)` and :math:`\chi(R)` for data and model will be
useful for the other examples as well, so we'll create a slightly
generalized function to make such plots and put this and several other
plotting functions into a separate file, *doc_macros.lar*.  This will look
like this:

.. literalinclude:: ../../examples/feffit/doc_macros.lar

This defines several new plotting functions :func:`plot_chifit`,
:func:`plot_path_k`, and :func:`plot_path_r`, and so on which we'll find
useful in later examples.  Using the first of these, we can then replace
the plot commands in the script above with::

    run('doc_macros.lar')
    plot_chifit(dset, title='First shell fit to Cu')

and get reproducible plots without having to copy and paste the same code
fragment everywhere.  We'll use this in the examples below.


Example 2: Fit 1 dataset with 3 Paths
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We'll continue with the Cu data set, and add more paths to model further
shells.  This is fairly straightforward, but in the interest of space,
we'll limit the example here to 3 paths to model the first two shells of
copper.  This is a small step, but highlights a main concern with XAFS
analysis that we need to address.  This is the fact that there simply is
not enough freedom in the XAFS signal to measure all the possible
adjustable Path Parameters independently.  Thus we need to be able to apply
constraints to the Path Parameters.

Here, we use two of the most common types of constraints.  First, we apply
the same amplitude reduction factor and the same :math:`E_0` shift to all
Paths.  These may seem obvious for this example, but for more complicated
examples, either including shells of mixed species or Feff Paths generated
from different calculation, these become less obvious.

Second, we introduce a scale the change in distance by a singple expansion
factor :math:`\alpha` (``alpha`` in the script), and using the builtin
value of half-path distance, ``reff``, and setting ``deltar =
'alpha*reff'`` for all Paths.  During the calculation of :math:`\chi(k)`
for each path that happens in the fitting process, the value of ``reff``
will be updated to the correct value for each path.  Thus, as the value of
``alpha`` varies in the fit, each path will use its proper value for
``reff``, so that each ``deltar`` will be different but not independent.
This ensures that all the path lengths change in a manner consistent with
one another.

.. literalinclude:: ../../examples/feffit/doc_feffit2.lar

Here we simply create ``path2`` and ``path3`` using nearly the same parameters
as for ``path1``.   Compared to the previous example, the other changess
are that the  :math:`R` range for the fit has been increased so that the
fit will try to fit the second shell, and that  ``sigma2`` is allowed to
vary independently for each path.

The output for this fit is a bit longer, being::

    =================== FEFFIT RESULTS ====================
    [[Statistics]]
       npts, nvarys       = 132, 6
       nfree, nfcn_calls  = 126, 50
       chi_square         = 4312.647261
       reduced chi_square = 34.227359

    [[Data]]
       n_independent      = 17.825
       eps_k, eps_r       = 0.000180, 0.008540
       fit space          = r
       r-range            = 1.400, 3.400
       k-range            = 3.000, 17.000
       k window, dk       = kaiser, 4.000
       k-weight           = 2
       paths used in fit  = ['feff0001.dat', 'feff0002.dat', 'feff0003.dat']

    [[Variables]]
       alpha          = -0.002436 +/- 0.001754   (init=  0.000000)
       amp            =  0.931861 +/- 0.067134   (init=  1.000000)
       del_e0         =  3.855156 +/- 0.871283   (init=  0.100000)
       sig2_1         =  0.008663 +/- 0.000527   (init=  0.002000)
       sig2_2         =  0.013728 +/- 0.002425   (init=  0.002000)
       sig2_3         =  0.008167 +/- 0.006718   (init=  0.002000)

    [[Correlations]]    (unreported correlations are <  0.100)
       amp, sig2_1          =  0.930
       alpha, del_e0        =  0.922
       amp, sig2_3          =  0.249
       sig2_1, sig2_3       =  0.247
       amp, sig2_2          =  0.241
       sig2_1, sig2_2       =  0.225
       alpha, sig2_1        =  0.181
       del_e0, sig2_3       =  0.162
       alpha, amp           =  0.161
       alpha, sig2_3        =  0.146
       del_e0, sig2_2       = -0.123

    [[Paths]]
       feff.dat file = feff0001.dat
              Atom     x        y        z     ipot
               Cu    0.0000,  0.0000,  0.0000  0 (absorber)
               Cu    0.0000, -1.8016,  1.8016  1
         reff   =  2.54780
         Degen  =  12.00000
         S02    =  0.93186 +/-  0.06713
         E0     =  3.85516 +/-  0.87128
         R      =  2.54159 +/-  0.00447
         deltar = -0.00621 +/-  0.00447
         sigma2 =  0.00866 +/-  0.00053

       feff.dat file = feff0002.dat
              Atom     x        y        z     ipot
               Cu    0.0000,  0.0000,  0.0000  0 (absorber)
               Cu   -3.6032,  0.0000,  0.0000  1
         reff   =  3.60320
         Degen  =  6.00000
         S02    =  0.93186 +/-  0.06713
         E0     =  3.85516 +/-  0.87128
         R      =  3.59442 +/-  0.00632
         deltar = -0.00878 +/-  0.00632
         sigma2 =  0.01373 +/-  0.00243

       feff.dat file = feff0003.dat
              Atom     x        y        z     ipot
               Cu    0.0000,  0.0000,  0.0000  0 (absorber)
               Cu    1.8016, -1.8016,  0.0000  1
               Cu    1.8016,  0.0000, -1.8016  1
         reff   =  3.82180
         Degen  =  48.00000
         S02    =  0.93186 +/-  0.06713
         E0     =  3.85516 +/-  0.87128
         R      =  3.81249 +/-  0.00670
         deltar = -0.00931 +/-  0.00670
         sigma2 =  0.00817 +/-  0.00672

    =======================================================

With plots of data and fits as shown below.


.. _xafs_fig13:

  .. image:: ../images/feffit_example3.png
     :target: ../_images/feffit_example3.png
     :width: 48 %
  .. image:: ../images/feffit_example4.png
     :target: ../_images/feffit_example4.png
     :width: 48 %

  Figure 13. Results for Feffit for a 3-shell fit to a spectrum from Cu
  metal, constraining all path distances to expand with a single variable.


Here, we show both the magnitude and real part of :math:`\chi(R)`.  The fit
to the real part shows excellent agreement over the fit :math:`R` range of
[1.4, 3.4] :math:`\AA`.  It is often useful the contributions from the
indvidual paths.  With the macros defined above, this is pretty
straightforward, as we can just do::

    plot_modelpaths_k(dset, offset=-1)
    plot_modelpaths_r(dset, comp='re', offset=-1, xmax=6)

to generate the following plots of the contributions of the differnt paths:


.. _xafs_fig14:

  .. image:: ../images/feffit_example5.png
     :target: ../_images/feffit_example5.png
     :width: 48 %
  .. image:: ../images/feffit_example6.png
     :target: ../_images/feffit_example6.png
     :width: 48 %

  Figure 14. Path contributions to full mode for the 3-shell fit to Cu
  spectrum.

Example 3: Fit 3 datasets with 3 Paths each
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We'll extend the above example by adding two more data sets.  This
highlights another key concept in modeling XAFS data and reducing the
number of freely varying parameters in a fit.

