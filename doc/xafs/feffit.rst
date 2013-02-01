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
    name in the Feffit Transform group.  Additional variables may
    be stored in this group as well, once the group has been
    used to do some transforms.


:func:`feffit_dataset`
~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: feffit_dataset(data=None, pathlist=[], transform=None)

    create a Feffit Dataset group.

    :param data:      group containing experimental EXAFS (needs arrays ``k`` and ``chi``).
    :param pathlist:  list of FeffPath groups, as created from :func:`feffpath`.
    :param transform: Feffit Transform group.
    :returns:         a Feffit Dataset group.

    A Dataset group is pretty simple, initially consisting of sub-groups ``data``,
    ``pathlist``, and ``transform``, though each of these can be complex.

    The value for ``data`` must be a group containing arrays ``k`` and
    ``chi`` (as determined :func:`_xafs.autobk` or some other procedure).
    If it contains a value (scalar or array) ``epsilon_k``, that will be
    used as the uncertainty in :math:`\chi(k)` for weighting the fit.
    Otherwise, the uncertainty in :math:`\chi(k)` will be estimated
    automatically, and stored in this dataset.

    The ``pathlist`` is a list of Feff Paths, each of which can have its
    Path Parameters written in terms of fit parameters (see the final
    example in the previous section).  This list of paths will be sent to
    :func:`ff2chi` to calculate the model :math:`\chi` to compare to the
    experimental data.   Finally, ``transform`` is a Feffit transform group,
    as defined above.

    A Dataset will also have a few other components, including:

      ================= ==========================================================
       component name        description
      ================= ==========================================================
         epsilon_k        estimated noise in the :math:`\chi(k)` data.
         epsilon_r        estimated noise in the :math:`\chi(R)` data.
         n_idp            estimated number of independent points in the data.
         model            a group for the model :math:`\chi` spectrum.
      ================= ==========================================================

   The ``model`` component will be set after a fit, and will contain the
   standard set of arrays for :math:`\chi(k)` and :math:`\chi(R)` for the
   fitting model, and can be directly compared to the arrays for the
   experimental data.


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
    in :ref:`fitting-results-sec`

        ================= =====================================================================
         component name     description
        ================= =====================================================================
           chi_reduced      reduced chi-square statistic.
           chi_square       chi-square statistic.
           covar            covariance matrix.
           covar_vars       list of variable names for rows and columns of covariance matrix.
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

running this example prints out the following report:

.. literalinclude:: ../../examples/feffit/doc_feffit1.out

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

Second, we introduce a scale the change in distance by a single expansion
factor :math:`\alpha` (``alpha`` in the script), and using the built-in
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
as for ``path1``.   Compared to the previous example, the other changes
are that the  :math:`R` range for the fit has been increased so that the
fit will try to fit the second shell, and that  ``sigma2`` is allowed to
vary independently for each path.

The output for this fit is a bit longer, being:

.. literalinclude:: ../../examples/feffit/doc_feffit2.out

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
individual paths.  With the macros defined above, this is pretty
straightforward, as we can just do::

    plot_modelpaths_k(dset, offset=-1)
    plot_modelpaths_r(dset, comp='re', offset=-1, xmax=6)

to generate the following plots of the contributions of the different paths:

.. _xafs_fig14:

  .. image:: ../images/feffit_example5.png
     :target: ../_images/feffit_example5.png
     :width: 48 %
  .. image:: ../images/feffit_example6.png
     :target: ../_images/feffit_example6.png
     :width: 48 %

  Figure 14. Path contributions to full mode for the 3-shell fit to Cu
  spectrum.

Example 3: Fit 3 datasets with 1 Path each
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We'll extend the above example by adding two more data sets.  Since the
three data sets have some things in common, we'll be able to use some a
smaller number of total variable parameters for all data sets than if we
had fit each of them individually.  This further allows us to reduce the
number of freely varying parameters in a model of XAFS data, and to better
measure the parameters that are varied.

Here, we'll use data on Cu metal measured at three different temperatures.
Since there is no phase change in the material over this temperature range,
the structure changes in small and predictable ways that lends itself to
simple parameterization.  In the interest of brevity, we'll only use one
path, but the example could easily be extended to include more paths.


In this example, we have three distinct datasets, so we'll have three lists
of paths.  Each of these will have a single path.  Since we're modeling
nearly the same structure, the three paths will use the same Feff.dat file
and have many parameters in common, but some parameters will be different
for each data set.  As with the previous example, we use the same amplitude
reduction factor :math:`E_0` shift to all data sets.  We allow distances to
vary, but constrain them so that the change is linear in the sample
temperature, as if there were a simple linear expansion in :math:`R`.  To
do this, we set ``deltar = 'dr_off + T*alpha*reff'``, where ``T`` is the
temperature for the dataset.  For :math:`\sigma^2` we'll use one of the
built-in models described in :ref:`Models for Calculating sigma2
<xafs-sigma2calcs_sec>`.  Here we'll use :func:`sigma2_eins`, but
:func:`sigma2_debye` can be used as well, and does a better job for
multiple-scattering paths in simple systems.  The model then uses 2
variable parameters for three temperature-dependent distances and 1
variable parameter for three temperature-dependent mean-square
displacements. The full script for the fit looks like this:

.. literalinclude:: ../../examples/feffit/doc_feffit3.lar

Here we read in 3 datasets for :math:`\mu(E)` data and do the background
subtraction on each of them.  We define 5 fitting parameters, including the
characteristic (here, Einstein) temperature which will determine the value of
:math:`\sigma^2`, and two parameters for the linear temperature dependence
of :math:`R`. The output for this fit is:

.. literalinclude:: ../../examples/feffit/doc_feffit3.out

Note that an uncertainty is estimated for the Path parameters, including
``sigma2``, which is calculated with the :func:`sigma2_eins` function.
Such derived uncertainties do reflect the uncertainties and correlations
between variables, but these derived uncertainties should definitely be
viewed as estimates.  In this examples, a simplistic evaluation of one of
the ``sigma2`` parameters using the estimated variance in the ``theta``::

    larch> _ave = sigma2_eins(10, pars.theta)
    larch> _dlo = sigma2_eins(10, pars.theta-pars.theta.stderr) - _ave
    larch> _dhi = sigma2_eins(10, pars.theta+pars.theta.stderr) - _ave
    larch> print "sigma2(T=10) = %.5f  (%+.5f, %+.5f)" % (_ave, _dlo, _dhi)
    sigma2(T=10) = 0.00328  (+0.00011, -0.00011)

gives an estimate about 3 times larger than the estimate automatically
derived from the fit.  Of course, the simple evaluation ignores the
correlation between parameters, and especially that if ``sigma2`` for one
dataset increases, so must ``sigma2`` for the other datasets.

The output plots for the fits to the three datasets are given below.

.. _xafs_fig15:

  .. image:: ../images/feffit_3temp1.png
     :target: ../_images/feffit_3temp1.png
     :width: 48 %
  .. image:: ../images/feffit_3temp2.png
     :target: ../_images/feffit_3temp2.png
     :width: 48 %

  **a**

  .. image:: ../images/feffit_3temp3.png
     :target: ../_images/feffit_3temp3.png
     :width: 48 %
  .. image:: ../images/feffit_3temp4.png
     :target: ../_images/feffit_3temp4.png
     :width: 48 %

  **b**

  .. image:: ../images/feffit_3temp5.png
     :target: ../_images/feffit_3temp5.png
     :width: 48 %
  .. image:: ../images/feffit_3temp6.png
     :target: ../_images/feffit_3temp6.png
     :width: 48 %

  **c**

  Figure 15. Fit to Cu metal at (a) 10 K, (b) 50 K, and (c) 150 K, from a
  simultaneous fit to all 3 datasets with 5 variables used.

Again, in the interest of brevity and consistency through this chapter,
these example are deliberately simple and meant to be illustrative of the
capabilities and procedures and should not be viewed as limiting the types
of problems that can be modeled.

Example 4: Measuring Coordination number
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For this and the following example, we switch from Cu metal data to data on
a simple metal oxide, FeO.  The structure is a basic rock-salt structure,
and we'll model 2 paths for Fe-O and Fe-Fe in this structure.  While the
data is imperfect, we'll use it to illustrate a few points in modeling
EXAFS data.


For the examples above with Cu metal, we tacitly assumed that the
coordination number for the different paths was correct, and we adjusted an
:math:`S_0^2` parameter.  But, as with many analyses on real systems of
research interest, we'd like to fit the coordination number for the two
different paths here.  To do this, we set an :math:`S_0^2` parameter to a
fixed value, and also force ``degen`` (the number of equivalent paths in
the structure used to generate the Feff.dat files) to be 1 for each path.
Instead, we'll define parameters ``n1`` and ``n2``, and set the Fe-O path's
amplitude to be ``s02*n1`` and the Fe-Fe path's amplitude to be ``s02*n2``.
We'll allow ``n1`` and ``n2`` to vary in the fit, and also define variable
parameters for the other path parameters, including separate variables for
:math:`\Delta R` and :math:`\sigma^2`.  The script for this fit is below:

.. literalinclude:: ../../examples/feffit/doc_feffit4.lar

The most important point here is the definitions used in setting up the
amplitudes for the paths:  first, that we set ``degen`` to 1, and second
that we used the expression ``s02*n1`` and so forth for the value of the
Path's amplitude.   A secondary note is that we gave two different
k-weights to :func:`feffit_transform`, which causes both k-weights to be
used in the fit.

The resulting output is

.. literalinclude:: ../../examples/feffit/doc_feffit4.out

with plots:

.. _xafs_fig16:

  .. image:: ../images/feffit_feo_k.png
     :target: ../_images/feffit_feo_k.png
     :width: 48 %
  .. image:: ../images/feffit_feo_r.png
     :target: ../_images/feffit_feo_r.png
     :width: 48 %

  Figure 16. Fits to 2-path fit to FeO EXAFS.

Example 5: Comparing Fits in different Fit Spaces
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We now turn to comparing fits in unfiltered k-space, R-space, and filter
k-space (or "q space").  This is partly to illustrate the preference for
using R- or q-space for fitting, and partly to demonstrate how one can run
similar fits and compare the results.  We'll use the FeO data from the
previous example.

To change fitting models and transform parameters, we'll make copies of the
parameter groups and dataset groups, make a few changes, and re-run the
fits.  For example, we can change the fitting space with (see
examples/feffit/doc_feffit5.lar)::

    larch> pars2 = copy(pars)   # copy parameters
    larch> dset2 = copy(dset)   # copy dataset
    larch> dset2.transform.fitspace = 'q'

Now we can run :func:`feffit` with the new parameter group and Dataset
group, and compare the results either by plotting models from the different
copies of the dataset or by viewing the parameter values and fit statistics
with::

    larch> out2  = feffit(pars2, dset2)
    larch> print '*** R Space ***'
    larch> print feffit_report(out, with_paths=False, min_correl=0.5)
    larch> print '*** Q Space ***'
    larch> print feffit_report(out2, with_paths=False, min_correl=0.5)

which gives

.. literalinclude:: ../../examples/feffit/doc_feffit5_qr.out

We can see that the results are not very different -- the best fit values
and uncertainties for the varied parameters are quite close for the fit in
'R' space and 'Q' space.

Now, we can try the fit in unfiltered 'K' space::

    larch> pars3 = copy(pars)   # copy parameters
    larch> dset3 = copy(dset)   # copy dataset
    larch> dset3.transform.kweight = 2
    larch> dset3.transform.fitspace = 'k'
    larch> out3 = feffit(pars3, dset3)
    larch  print feffit_report(out3, with_paths=False, min_correl=0.5)

(we need to specify only one k-weight for a k-space fit) which gives:

.. literalinclude:: ../../examples/feffit/doc_feffit5_k.out

This has pretty similar best-fit values, but dramatically larger estimates
of the errors.  The spectrum is really very poorly fit in k-space because
we have not accounted for the higher R components.  Using R (and Q) space,
we're able to limit the R range used in determining the parameter values,
estimated uncertainties, and the goodness-of-fit statistics.  But since we
can't place these limits on what portion of the data is being compared to
the model spectra in unfiltered k-space fit, the uncertainties reflect the
fact that the full experimental spectrum is not well model.  This is why it
is recommended to not fit in unfiltered k space: the uncertainties in the
parameters is too large.

Of course, here we've changed only one thing between these three fits --
the fitting 'space'.  The process of copying the parameter group and
dataset, making modifications and re-doing fits can also include changing
what parametres are varied, and what constraints are placed between
parameters.





