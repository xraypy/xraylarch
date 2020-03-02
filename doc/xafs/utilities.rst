=========================================================
XAFS Functions: Overview and Naming Conventions
=========================================================

As with most Larch functions, each of the XAFS functions is designed to be
able to act on arbitrary arrays of data to allow maximum flexibility in
processing data.  In addition, many of the Larch XAFS functions can write
out several output values, including both scalars and arrays.  While
flexible, this could get rather cumbersome, and mean that you would
generally have to keep track of a large set of related arrays.

Naming conventions for XAFS arrays
=========================================

In Larch, it is most natural to put related data into a Group.  This is
often natural as data read in from a file is already held in a Group.  If a
set of XAFS data is held within a Group, then the Group members named
`energy` and `k` and `chi` can be assumed to have the same standard meaning
for all groups of XAFS Data.  To make this most common usage easy, all of
the XAFS functions follow a couple conventions for working more easily with
Groups that can work on arbitrary arrays of data, but assume that they will
write output values to a Group.  In addition, the XAFS functions can
usually just be given a Group that follows the expected XAFS naming
convention.  This is not rigidly enforced, and is not exclusive (that is,
you can add data with other names), but following the expected naming
conventions will make processing XAFS data much easier.

The naming convention define a set of **expected names and meaning** for
data arrays and scalars within a Group.  This is summarized in the
:ref:`Table of Conventional Names for an XAFS Group <xafsnames_table>` below.


.. _xafsnames_table:

**Table of Conventional Names for an XAFS Group** These are the standard names for arrays and
scalars for various data associated with XAFS, including FEFF calculations.  Given are the name,
the physical quantity described, and the name of function that will generate this value.


  +---------------+--------+-----------------------------+------------------------------------+
  | name          | type   |   meaning                   | created by                         |
  +===============+========+=============================+====================================+
  | energy        | array  | :math:`E` in eV             | original data                      |
  +---------------+--------+-----------------------------+------------------------------------+
  | mu            | array  | :math:`\mu`                 | original data                      |
  +---------------+--------+-----------------------------+------------------------------------+
  | e0            | scalar | :math:`E_0`                 | :func:`pre_edge`, :func:`find_e0`  |
  +---------------+--------+-----------------------------+------------------------------------+
  | edge_step     | scalar | :math:`\Delta \mu`          | :func:`pre_edge`                   |
  +---------------+--------+-----------------------------+------------------------------------+
  | dmude         | array  | :math:`d\mu/dE`             | :func:`pre_edge`                   |
  +---------------+--------+-----------------------------+------------------------------------+
  | norm          | array  | normalized :math:`\mu`      | :func:`pre_edge`                   |
  +---------------+--------+-----------------------------+------------------------------------+
  | flat          | array  | flattened :math:`\mu`       | :func:`pre_edge`                   |
  +---------------+--------+-----------------------------+------------------------------------+
  | pre_edge      | array  | pre-edge curve              | :func:`pre_edge`                   |
  +---------------+--------+-----------------------------+------------------------------------+
  | post_edge     | array  | normalization curve         | :func:`pre_edge`                   |
  +---------------+--------+-----------------------------+------------------------------------+
  | bkg           | array  | :math:`\mu_0(E)`            | :func:`autobk`                     |
  +---------------+--------+-----------------------------+------------------------------------+
  | chie          | array  | :math:`\chi(E)`             | :func:`autobk`                     |
  +---------------+--------+-----------------------------+------------------------------------+
  | k             | array  | :math:`k`                   | :func:`autobk`                     |
  +---------------+--------+-----------------------------+------------------------------------+
  | chi           | array  | :math:`\chi(k)`             | :func:`autobk`                     |
  +---------------+--------+-----------------------------+------------------------------------+
  | kwin          | array  | :math:`\Omega(k)`           | :func:`xftf`, :func:`ftwindow`     |
  +---------------+--------+-----------------------------+------------------------------------+
  | r             | array  | :math:`R`                   | :func:`xftf`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | chir          | array  | :math:`\chi(R)` (complex)   | :func:`xftf`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | chir_mag      | array  | :math:`|\chi(R)|`           | :func:`xftf`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | chir_re       | array  | :math:`\rm Re[\chi(R)]`     | :func:`xftf`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | chir_im       | array  | :math:`\rm Im[\chi(R)]`     | :func:`xftf`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | rwin          | array  | :math:`\Omega(R)`           | :func:`xftr`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | q             | array  | :math:`q`                   | :func:`xftr`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | chiq          | array  | :math:`\chi(q)` (complex)   | :func:`xftr`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | chiq_mag      | array  | :math:`|\chi(q)|`           | :func:`xftr`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | chiq_re       | array  | :math:`\rm Re[\chi(q)]`     | :func:`xftr`                       |
  +---------------+--------+-----------------------------+------------------------------------+
  | chiq_im       | array  | :math:`\rm Im[\chi(q)]`     | :func:`xftr`                       |
  +---------------+--------+-----------------------------+------------------------------------+

where :math:`q`, :math:`\chi(q)`, and so on indicates back-transformed :math:`k`.


The XAFS functions encourage following this convention, in that they are consistent in wanting
:math:`\chi(k)` to be represented by the two arrays ``GROUP.k`` and ``GROUP.chi``


.. _Set XAFS Group:

`group` argument and ``_sys.xafsGroup``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The XAFS functions need to write outputs to some group -- there are simply
too many outputs to return and expect you to manage.  To better accomodate
this, all functions take a `group` argument, which is used as the group
into which results are written.  This gives a convenient way to manage the
results of the different analysis steps, but gets tedious to provide this
argument repeatedly when working with a particular data set.

For XAFS analysis, there is also a special group, ``_sys.xafsGroup`` that
is used as the default group to write outputs to if no `group` argument is
supplied.  In addition, when an explicit `group` argument is given,
``_sys.xafsGroup`` is set to this group.  In short, the ``_sys.xafsGroup``
will be used as the "current, default group".  This means that when working
with a set of XAFS data all contained within a single group (which is
expected to be the normal case), the `group` argument does not need to be
typed repeatedly.

Because this uses a global group in the Larch interpreter, this convention
works from with the Larch language, but does not work from plain Python
unless an instance of a Larch session is passed into the `larch.xafs`
function using the `_larch` argument.

.. _First Argument Group:

First Argument Group convention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since the XAFS functions need to write outputs to some group and will
generally work with groups that contain data following :ref:`Table of
Conventional Names for an XAFS Group <xafsnames_table>`, most of the XAFS
functions follow what is called the **First Argument Group** convention.
This convention gives a simple approach when working with groups of XAFS
data and it is worth understanding and using this for most work with the
XAFS work.  This convention is built on the ``_sys.xafsGroup`` convention
discussed above but is even easier to use.

While the XAFS functions can take arrays of data as the first two arguments
most work will have these arrays in a single group with array names that
follows the conventions above.  As an example, the most general use of the
:func:`autobk` function takes an array of energy as the first argument, an
array of mu as the second argument, and supplying an output group for
placing all the arrays and data calculated within the function.  That is,
the most general use would look like::

     autobk(energy, mu, group=dat, rbkg=1, ....)

Of course, most usage will actually want to use `energy` and `mu` arrays
from the same group, and use that group as the output group, so that all
data stays contained within the same group.  That would make the call above
look like::

     autobk(dat.energy, dat.mu, group=dat, rbkg=1, ....)

where the group name `dat` is repeated three times.

The First Argument Group convention allows this to be written as::

     autobk(dat, rbkg=1, ....)

That is, as long as the Group `dat` follows the XAFS naming conventions
(for :func:`autobk` that it has an energy array named `energy` and
absorbance array named `mu`) the two forms above are equivalent.  All the
XAFS functions follow this convention and use a consistent set of attribute
names (see :ref:`Table of Conventional Names for an XAFS Group
<xafsnames_table>`).  This convention nearly makes the Larch XAFS routines
into object-oriented, or in this case **Group oriented**, set of functions
that interact in a coherent and predictable way on an XAFS dataset.


Plotting Macros for XAFS
================================

XAFS analysis often uses several different standard views of the data arrays
for :math:`\mu(E)`, :math:`\chi(k)`, and :math:`\chi(R)`.  Larch's plotting
capabilities provide wide flexibility in how plots can be done.  While that
flexibility can be useful in general, within the narrow scope of plotting
XAFS data, being able to easily create consistent plots with reasonable
defaults produces results that are easier to digest and understand.

The macros described here attempt to provide that functionality of
easy-to-use standard plotting macros. In particular, they automatically
handle typesetting the labels for the plot axes in a consistent manner, and
assign consistent labels to the different curves shown.  The results are also
easily extended, so that you can add curves, annotations, etc.  Many of the
examples in the following sections in this chapter make use of these macros.

:func:`plot_mu`
~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_mu(dgroup, norm=False, deriv=False, show_pre=False, show_post=False, show_e0=False, emin=None, emax=None, label=None, new=True, win=1)

    Plot :math:`\mu(E)` for an XAFS data group in various forms

   :param dgroup:  group of XAFS data after :func:`pre_edge()` results (see note below)
   :param norm:    bool whether to show normalized data [``False``]
   :param deriv:   bool whether to show derivative of XAFS data [``False``]
   :param show_pre:  bool whether to show pre-edge curve [``False``]
   :param show_post:  bool whether to show post-edge curve [``False``]
   :param show_e0:  bool whether to show E0 [``False``]
   :param show_deriv: bool whether to show deriv together with mu [``False``]
   :param emin:  min energy to show, relative to E0 [``None``, start of data]
   :param emax:  max energy to show, relative to E0 [``None``, end of data]
   :param label: string for label [``None``:  'mu', 'dmu/dE', or 'mu norm']
   :param new:  bool whether to start a new plot [``True``]
   :param win:  integer plot window to use [1]

   The input data group must have the following attributes: `energy`, `mu`,
   `norm`, `e0`, `pre_edge`, `edge_step`, `filename`

:func:`plot_bkg`
~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False, label=None, new=True, win=1)

    Plot :math:`\mu(E)` and background :math:`\mu_0(E)` for XAFS data group

    :param dgroup:   group of XAFS data after autobk() results (see note below)
    :param norm:   bool whether to show normalized data [``True``]
    :param emin:   min energy to show, relative to :math:`E_0` [``None``, start of data]
    :param emax:   max energy to show, relative to :math:`E_0` [``None``, end of data]
    :param show_e0:  bool whether to show E0 [``False``]
    :param label: string for label [``None``:  'mu']
    :param new:   bool whether to start a new plot [``True``]
    :param win:   integer plot window to use [1]

    The input data group must have the following attributes: `energy`, `mu`,
    `bkg`, `norm`, `e0`, `pre_edge`, `edge_step`, `filename`

:func:`plot_chik`
~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_chik(dgroup, kweight=None, kmax=None, show_window=True, label=None, new=True, win=1)

    Plot k-weighted :math:`\chi(k)` for XAFS data group

    :param dgroup:       group of XAFS data after autobk() results (see note below)
    :param kweight:      k-weighting for plot [read from last :func:`xftf()`, or 0]
    :param kmax:         max k to show [``None``, end of data]
    :param show_window:  bool whether to also plot k-window [``True``]
    :param label:        string for label [``None``:  'chi']
    :param new:          bool whether to start a new plot [``True``]
    :param win:       integer plot window to use [1]

    The input data group must have the following attributes: `k`, `chi`,
    `kwin`, `filename`.

:func:`plot_chir`
~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_chir(dgroup, show_mag=True, show_real=False, show_imag=False, rmax=None, label=True, new=True, win=1)

    Plot :math:`\chi(R)` for XAFS data group

    :param dgroup:       group of XAFS data after xftf() results (see note below)
    :param show_mag:     bool whether to plot :math:`|\chi(R)|` [``True``]
    :param show_real:    bool whether to plot :math:`Re[\chi(R)]` [``False``]
    :param show_imag:    bool whether to plot :math:`Im[\chi(R)]` [``False``]
    :param rmax:         max R to show [``None``, end of data]
    :param label:        string for label [``None``:  'chir']
    :param new:          bool whether to start a new plot [``True``]
    :param win:          integer plot window to use [1]

    The input data group must have the following attributes: `r`,
    `chir_mag`, `chir_im`, `chir_re`, `kweight`, `filename`

:func:`plot_chifit`
~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_chifit(dataset, kmin=0, kmax=None, rmax=None, show_mag=True, show_real=False, show_imag=False, new=True, win=1)

    Plot k-weighted :math:`\chi(k)` and :math:`\chi(R)` for fit to feffit dataset

    :param dataset:      feffit dataset, after running :func:`feffit`.
    :param kmin:         min k to show [0]
    :param kmax:         max k to show [``None``, end of data]
    :param rmax:         max R to show [``None``, end of data]
    :param show_mag:     bool whether to plot :math:`|chi(R)|` [``True``]
    :param show_real:    bool whether to plot :math:`Re[`chi(R)]` [``False``]
    :param show_imag:    bool whether to plot :math:`Im[\chi(R)]` [``False``]
    :param new:          bool whether to start a new plot [``True``]
    :param win:          integer plot window to use [1]



:func:`plot_path_k`
~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_path_k(dataset, ipath, kmin=0, kmax=None, offset=0, label=None, new=False, win=1, **kws)

    Plot k-weighted :math:`\chi(k)` for a single Path of a feffit dataset

    :param  dataset:      feffit dataset, after running :func:`feffit`
    :param  ipath:        index of path, starting count at 0 [0]
    :param  kmin:         min k to show [0]
    :param  kmax:         max k to show [``None``, end of data]
    :param  offset:       vertical offset to use for plot [0]
    :param  label:        path label ['path I']
    :param  new:          bool whether to start a new plot [``True``]
    :param  win:          integer plot window to use [1]
    :param  kws:          additional keyword arguments are passed to plot()


:func:`plot_path_r`
~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_path_r(dataset, ipath,rmax=None, offset=0, label=None, show_mag=True, show_real=False, show_imag=True, new=False, win=1, **kws)

    Plot :math:`\chi(R)` for a single Path of a feffit dataset

    :param  dataset:      feffit dataset, after running :func:`feffit`
    :param  ipath:        index of path, starting count at 0 [0]
    :param  kmax:         max k to show [None, end of data]
    :param  offset:       vertical offset to use for plot [0]
    :param  label:        path label ['path I']
    :param  show_mag:     bool whether to plot :math:`|\chi(R)|` [``True``]
    :param  show_real:    bool whether to plot :math:`Re[\chi(R)]` [``False``]
    :param  show_imag:    bool whether to plot :math:`Im[\chi(R)]` [``False``]
    :param  new:          bool whether to start a new plot [``True``]
    :param  win:          integer plot window to use [1]
    :param  kws:          additional keyword arguments are passed to plot()



:func:`plot_paths_k`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_paths_k(dataset, offset=-1, kmin=0, kmax=None, new=True, win=1, **kws):

    Plot k-weighted `\chi(k)` for model and all paths of a feffit dataset

    :param dataset:      feffit dataset, after running :func:`feffit`
    :param kmin:         min k to show [0]
    :param kmax:         max k to show [``None``, end of data]
    :param offset:       vertical offset to use for paths for plot [-1]
    :param new:          bool whether to start a new plot [``True``]
    :param win:          integer plot window to use [1]
    :param kws:          additional keyword arguments are passed to plot()



:func:`plot_paths_r`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_paths_r(dataset, offset=-0.5, rmax=None, show_mag=True, show_real=False, show_imag=False, new=True, win=1, **kws):

    Plot :math:`\chi(R)` for model and all paths of a feffit dataset

    :param dataset:      feffit dataset, after running func:`feffit`
    :param offset:       vertical offset to use for paths for plot [-0.5]
    :param rmax:         max R to show [``None``, end of data]
    :param show_mag:     bool whether to plot :math:`|\chi(R)|` [T``rue``]
    :param show_real:    bool whether to plot :math:`Re[\chi(R)]` [``False``]
    :param show_imag:    bool whether to plot :math:`Im[\chi(R)]` [``False``]
    :param new:          bool whether to start a new plot [``True``]
    :param win:          integer plot window to use [1]
    :param kws:          additional keyword arguments are passed to plot()



:func:`plot_prepeaks_baseline`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_prepeaks_baseline(dgroup, subtract_baseline=False, show_fitrange=True, show_peakrange=True, win=1, **kws):

    Plot pre-edge peaks and baseline fit, as from :func:`pre_edge_baseline`
    or XAS Viewer GUI


    :param dgroup:      data group, after running :func:`pre_edge_baseline`
    :param subtract_baseline:  bool whether to subtract baseline for plot
    :param show_fitrange:  bool whether to show fit range as vertical bars
    :param show_peakrange:  bool whether to show pre-edge peak range with markers
    :param win:          integer plot window to use [1]
    :param kws:          additional keyword arguments are passed to plot()

    The `dgroup` group must have a `prepeaks` subgroup.


:func:`plot_prepeaks_fit`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. function:: plot_prepeaks_fit(dgroup, show_init=False, subtract_baseline=False, show_residual=False, win=1, **kws):

    Plot pre-edge peaks and fit, as XAS Viewer GUI


    :param dgroup:      data group, after running pre-edge peak fit.
    :param show_init:    bool whether to show initial model, before fitting
    :param subtract_baseline:  bool whether to subtract baseline for plot
    :param show_residual:  bool whether to show residual as a stacked plot.
    :param win:          integer plot window to use [1]
    :param kws:          additional keyword arguments are passed to plot()

    The `dgroup` group must have a `peakfit_history` subgroup. Currently,
    this is automatically generated only using the XAS Viewer GUI or
    scripts written (and possibly altered) by it.


Utility Functions for XAFS
=============================================


Listed here are some general purpose functions for XAFS.


:func:`ktoe` and :func:`etok`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: etok(energies)

    Convert photo-electron energy in eV to wavenumber in :math:`\AA^{-1}`.
    energies can be a single number or array of numbers.

..  function:: ktoe(wavenumbers)

    Convert photo-electron wavenumber in :math:`\AA^{-1}` ot energy in eV.
    wavenumber can be a single number or array of numbers.

An example use would be to print out a table of energies and :math:`k` values::

    larch> kvals = linspace(0, 25, 26)
    larch> evals = ktoe(kvals)
    larch> for k,e in zip(kvals, evals)):
    larch>      print " %5.1f 1/Ang ->  %8.2f eV" %(k , e)
    larch> endfor
       0.0 1/Ang ->      0.00 eV
       1.0 1/Ang ->      3.81 eV
       2.0 1/Ang ->     15.24 eV
       3.0 1/Ang ->     34.29 eV
       4.0 1/Ang ->     60.96 eV
       5.0 1/Ang ->     95.25 eV
       6.0 1/Ang ->    137.16 eV
       7.0 1/Ang ->    186.69 eV
       8.0 1/Ang ->    243.84 eV
       9.0 1/Ang ->    308.61 eV
      10.0 1/Ang ->    381.00 eV
      11.0 1/Ang ->    461.01 eV
      12.0 1/Ang ->    548.64 eV
      13.0 1/Ang ->    643.89 eV
      14.0 1/Ang ->    746.76 eV
      15.0 1/Ang ->    857.25 eV
      16.0 1/Ang ->    975.36 eV
      17.0 1/Ang ->   1101.08 eV
      18.0 1/Ang ->   1234.43 eV
      19.0 1/Ang ->   1375.40 eV
      20.0 1/Ang ->   1523.99 eV
      21.0 1/Ang ->   1680.20 eV
      22.0 1/Ang ->   1844.03 eV
      23.0 1/Ang ->   2015.48 eV
      24.0 1/Ang ->   2194.55 eV
      25.0 1/Ang ->   2381.24 eV



:func:`estimate_noise`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  function:: estimate_noise(k, chi=None, group=None, rmin=15, rmax=30, ....)

    Automatically estimate the noise level in a :math:`\chi(k)` spectrum.


    :param k:       1-d array of :math:`k`
    :param chi:     1-d array of :math:`\chi`
    :param group:   output group.
    :param rmin:    minimum :math:`R` value for noise estimate.
    :param rmax:    maximum :math:`R` value for noise estimate.
    :param kweight:  exponent for weighting spectra by k**kweight [1]
    :param kmin:     starting k for FT Window [0]
    :param kmax:     ending k for FT Window  [20]
    :param dk:       tapering parameter for FT Window [4]
    :param dk2:      second tapering parameter for FT Window [None]
    :param window:   name of window type ['kaiser']
    :param nfft:     value to use for N_fft [2048].
    :param kstep:    value to use for delta_k ( Ang^-1) [0.05]


    The method uses an XAFS Fourier transform, and many of arguments
    (**kmin**, **kmax**, etc) are identical to those of :func:`xftf`.

    This function follows the First Argument Group convention with arrays named `k` and `chi`.
    The following outputs are written to the supplied **group** (or `_sys.xafsGroup` if
    **group** is not supplied):

     ================= ===============================================================
      attribute         meaning
     ================= ===============================================================
      epsilon_k          estimated noise level in :math:`\chi(k)`.
      epsilon_r          estimated noise level in :math:`\chi(R)`.
      kmax_suggest       suggested highest :math:`k` value for which :math:`|\chi(k)| > \epsilon_k`
     ================= ===============================================================

This method uses the high-R portion of :math:`\chi(R)` (between **rmin**
and **rmax**) as a measure of the noise level in the :math:`\chi(R)` data
and uses Parseval's theorem to convert this noise level to that in
:math:`\chi(k)`.  This method implicitly assumes that there is no signal in
the high-R portion of the spectrum, and that the noise in the spectrum is
"white" (independent of :math:`R`) .  Each of these assumptions can be
legitimately questioned.  Then again, making the assertion that these
assumptions are invalid and disregarding the estimated noise level here
would require knowledge of the noise in an XAFS spectrum that most users do
not have.  At the very least, this estimate should be be interpreted as a
minimal estimate of the noise level in :math:`\chi(k)`.

The estimate for the output value **kmax_suggest** has a tendency to be
pessimistic in how far out the :math:`\chi(k)` data goes before being
dominated by noise, but has the advantage of being an impartial measure of
data quality. It is particularly pessimistic for extremely good data.  Then
again, considering that the estimate for :math:`\epsilon` is probably too
small, the estimate may not be that bad.
