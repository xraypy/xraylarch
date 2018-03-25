.. _guis-xas_viewer:


XAS_Viewer
=======================

The XAS_Viewer GUI uses Larch to read and display XAFS spectra.  This is
still in active development, with more features planned with special
emphasis on helping users with XANES analysis.  Current features (as of
March, 2018, Larch version 0.9.36) include:

   * read XAFS spectra from simple data column files.
   * read XAFS spectra from Athena Project files.
   * XAFS pre-edge removal and normalization.
   * visualization of normalization steps.
   * fitting of pre-edge peaks.
   * saving of data to Athena Project files.
   * saving of data to CSV files.


.. _lmfit:    http://lmfit.github.io/lmfit-py




The XAS Viewer GUI includes a simple form for basic pre-edge subtraction,
normalization, and de-convolution of XAFS spectra.
:numref:`fig_xasviewer_1a` shows the main window for the XAS Viewer
program.  The left-hand portion contains a s list of files (or data groups)
that have been read into the program. Clicking on the file or group name
makes that "the current data group", while checking the boxes next to each
name will select multiple files or group.  Buttons at the top of the list
of files can be used to "Select All" or "Select None".

The right-hand portion of the XAS Viewer window shows multiple forms for
data processing, each on a separate Notebook tab.  The main tab shown is
labeled "XAS Normalization" with a form for normalizing XAS data, and
choices for how to plot the data for the current group or the selected
groups. This form is provides a graphical interface to the :func:`pre_edge`
and related functions.  A separate window (:numref:`fig_xasviewer_1b`) will
show an interactive plot of the chosen data to be plotted. As with all
Larch plots, the plot can be zoomed in an out, and configured to change
colors, linestyles, text for labels, and so on.  For example, clicking on
the legend for each spectra will toggle the display of that spectra.

Note that many of the entries for numbers on the form panels have a button
with a fancy '+' sign.  Clicking anywhere on the plot window will remember
the energy value of the last point clicked. Then, clicking on one of
these buttons will insert that "last-clicked energy" value into the
corresponding field.

The XAS Viewer program has notebook tabs or more specialized XANES and XAFS
analysis.  Currently (March 2018), the only additional functionality is for
fitting pre-edge peaks, which is under the "Pre-edge Peak Fit" tab as shown
below, but we will be adding more functionality soon.



.. subfigstart::

.. _fig_xasviewer_1a:

.. figure:: ../_images/XAS_Viewer_xasnorm.png
    :target: ../_images/XAS_Viewer_xasnorm.png
    :width: 100%
    :align: center

    Main XAFS pre-edge subtraction and normalization form.

.. _fig_xasviewer_1b:

.. figure:: ../_images/XAS_Viewer_xas_plot.png
    :target: ../_images/XAS_Viewer_xas_plot.png
    :width: 62%
    :align: center

    An example of an interactive plot of XANES data.

.. subfigend::
    :width: 0.48
    :alt: main xasviewer
    :label: fig_xasviewer_1

    XANES data normalization with XAS Viewer.


Data groups can be read from plain ASCII data files using a GUI form to
help build :math:`\mu(E)`, or from Athena Project files, as shown in
:numref:`fig_xasviewer_2a` and :numref:`fig_xasviewer_2b`.  Multiple data
groups can be read in, compared, and merged.  These datasets can then be
exported to Athena Project files, or to CSV files.


.. subfigstart::

.. _fig_xasviewer_2a:

.. figure:: ../_images/DataImporter.png
    :target: ../_images/DataImporter.png
    :width: 60%
    :align: center

    ASCII data file importer.

.. _fig_xasviewer_2b:

.. figure:: ../_images/AthenaImporter.png
    :target: ../_images/AthenaImporter.png
    :width: 100%
    :align: center

    Athena Project importer.

.. subfigend::
    :width: 0.48
    :alt: data importers
    :label: fig_xasviewer_2

    Data importers for XAS Viewer.


The "Pre-edge Peak Fit" tab (show in :numref:`fig_xasviewer_3a`) provides a
form for fitting pre-edge peaks to lineshapes such as Gaussian, Lorentzian,
or Voigt functions.  This provides an easy-to-use wrapper around `lmfit`_
and the :func:`minimize` function for curve-fitting with the ability to
constrain fitting Parameters.


To do fitting of pre-edge peaks with the interface, one begins by fitting a
"baseline" to account for the main absorption edge.  This baseline is
modeled as a Lorentzian curve plus a line.  Fitting a baseline requires
identifying energy ranges for both the main spectrum to be fitted and the
pre-edge peaks -- the part of the spectrum where the baseline should *not*
be fitted.  This is illustrated in :numref:`fig_xasviewer_3a` and
:numref:`fig_xasviewer_3b`.  Note that there are separate ranges for the
"fit range" and the "pre-edge peak" range (illustrated with grey lines and
blue '+' signs on the plot).  The "pre-edge peak" range should be inside
the fit range.

Clicking "Fit baseline" will fit a baseline function and display the
results.  The initial fit may have poorly guessed ranges for the pre-edge
peaks and fit range and may require some adjustment.

.. subfigstart::

.. _fig_xasviewer_3a:

.. figure:: ../_images/XAS_Viewer_prepeak_baseline.png
    :target: ../_images/XAS_Viewer_prepeak_baseline.png
    :width: 100%
    :align: center

    Pre-edge peak Window of XAS_Viewer, showing how select regions of
    pre-edge peaks for fiting a baseline.


.. _fig_xasviewer_3b:

.. figure:: ../_images/XAS_Viewer_plot_baseline.png
    :target: ../_images/XAS_Viewer_plot_baseline.png
    :width: 60%
    :align: center

    Plot of pre-edge peaks with baseline.  Note that the grey vertical
    lines show the fit range, the blue crosses show the pre-edge peak
    range, and the pink line shows the centroid of the pre-edge peaks after
    removal of the baseline.


.. subfigend::
    :width: 0.48
    :alt: pre-edge peak baseline
    :label: fig_xasviewer_3

    Pre-edge Peak baseline removal.


Once the pre-edge baseline is satisfactory, you can add functions to model
the pre-edge peaks themselves.  Select one of the "Peak Models" (typically
Gaussian, Lorentzian, or Voigt), which will show a new tab in the "model
components area" in the lower part of the form.  Note that the baseline
will consist of a Lorenztian and linear model component, so that there will
be at least 3 tabs for the 3 or more components of the pre-edge peak model.
This is shown in :numref:`fig_xasviewer_4a`, which shows the form for 1
Gaussian peak, and the baseline.

.. subfigstart::

.. _fig_xasviewer_4a:

.. figure:: ../_images/XAS_Viewer_prepeak_1gaussian.png
    :target: ../_images/XAS_Viewer_prepeak_1gaussian.png
    :width: 100%
    :align: center

    Pre-edge peak Window of XAS_Viewer, showing how select regions of
    pre-edge peaks for fiting a baseline.


.. _fig_xasviewer_4b:

.. figure:: ../_images/XAS_Viewer_plot_1gaussian.png
    :target: ../_images/XAS_Viewer_plot_1gaussian.png
    :width: 60%
    :align: center

    Pre-edge peak Window of XAS_Viewer, showing how select regions of
    pre-edge peaks for fiting a baseline.

.. subfigend::
    :width: 0.49
    :alt: pre-edge peak fit
    :label: fig_xasviewer_4

    Pre-edge Peak fit.

Upon doing a fit, the fit results are shown in a separate window, with an
example shown in :numref:`fig_xasviewer_5`.


.. _fig_xasviewer_5:

.. figure:: ../_images/XAS_Viewer_prepeak_fitresult.png
    :target: ../_images/XAS_Viewer_prepeak_fitresult.png
    :width: 45%
    :align: left

    Fit result frame for Pre-edge peak fit.
