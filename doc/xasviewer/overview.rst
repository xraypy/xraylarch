.. include:: ../_config.rst

.. |pin| image:: ../_images/pin_icon.png
    :width: 18pt
    :height: 18pt

.. _xasviewer_overview:

XAS Viewer Overview
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The main features of XAS Viewer can be broken into a few categories.  Here
we give a brief overview, and then expand on these topics in later sections.


===================================
Data Input and Output
===================================

XAS Viewer can import XAS data in the following formats

   * XDI data files - the standard data format for XAS data (:ref:`xasviewer_plaintext`).
   * plain text data data files with data arrays in column format (:ref:`xasviewer_plaintext`).
   * Athena Project Files (:ref:`xasviewer_athena`).
   * ESRF Spec/BLISS HDF5 files (:ref:`xasviewer_blisshdf5`).
   * Larch Session files (:ref:`xasviewer_sessionfiles`).

For exporting or saving data, XAS Viewer can save multiple XAS spectra as:

   * Athena Project files (:ref:`xasviewer_athena`).
   * CSV files, from selected groups or for fitting and analysis results.
   * Larch Session files (:ref:`xasviewer_sessionfiles`).

See :ref:`xasviewer_io` for details


===================================
XAS Data Processing and Management
===================================

Each XAS spectra in XAS Viewer is contained in a *Group* of data. All of
the processing and analysis arrays and settings for this spectra will be
contained within this Group.  Each Group will be shown by its "File Name"
(assigned even if created and not read from an external file) and also have
a "Group Name" -- the name in the Larch interpreter from which this Group
of data can be accessed.

From XAS Viewer, the following processing operations can be done on any
Group or any set of Groups of XAS Data:

   * Merging: adding together the :math:`\mu(E)` signals.
   * Setting an Energy Reference: Each Group has an Energy Reference Group used when calibrating energies.
   * Energy Calibration: aligning energies of Groups. (:ref:`xasviewer_energy_calib`)
   * Rebinning of data onto a different energy grid
   * Remove glitches or truncating data.
   * Smoothing of data.
   * Deconvolution of data.
   * Correcting for Over-absorption of fluorescence XANES data.
   * Pre-edge subtraction.
   * Normalization, either using polynomials or the MBACK algorithm.

All of these processing steps can be done interactively, with users able to adjust
a small set of curated parameters and then visualize the results of these adjustments.


===================================
XANES Analysis
===================================

   * linear combination analysis of spectra.
   * principal component analysis.
   * regression of XANES spectra with a predicting external variable.
   * pre-edge peak fitting.

===================================
EXAFS Processing
===================================

   * EXAFS background spline removal.
   * forward Fourier transforms from :math:`k` to :math:`R`
   * back Fourier transforms from :math:`R` to filtered-:math:`k` space
   * Cauchy wavelet transforms.

===================================
EXAFS Modeling with FEFF
===================================

   * Browser for CIF files from American Mineralogist Crystal Structure Database.
   * Convert CIF files (from AMCSDB or external file) to feff.inp for Feff6/Feff8l.
   * Run Feff6 or Feff8, saving and browsing EXAFS Paths from these Feff runs.
   * Feff Fitting of single EXAFS spectra for a sum of Feff paths.

XAS Viewer presents a "Normalization" form for basic pre-edge subtraction,
and normalization of XAFS spectra. :numref:`fig_xasviewer_1` shows the main
window for the XAS Viewer program.  The left-hand portion contains a list
of files (or data Groups) that have been read into the program.  Clicking
on the file name makes that "the current data group", while checking the
boxes next to each name will select multiple Groups.  Buttons at the top of
the list of files can be used to "Select All" or "Select None".
Right-clicking on the file list will pop up a menu that allows more
detailed selecting of data sets.

.. _fig_xasviewer_1:

.. figure:: ../_images/XASViewer_Main.png
    :target: ./_images/XASViewer_Main.png
    :width: 75%
    :align: center

    XASViewer showing the File/Group list on the left-hand side and the
    the XAFS pre-edge subtraction and normalization panel on the right.

The right-hand portion of the XAS Viewer window shows multiple forms for
more specialized XAFS data processing tasks, each on a separate Notebook
tab.  These will be covered in more detail in sections below. The default
panel shown is for pre-edge subtraction and normalization
(:ref:`xasviewer_preedge`), with other available tabs for fitting pre-edge
peaks (:ref:`xasviewer_peakfit`), Linear Combination Analysis
(:ref:`xasviewer_lincombo`),
Principal Component Analysis (:ref:`xasviewer_pca`),
Advanced Linear Regression (:ref:`xasviewer_regression`),
EXAFS Analysis (:ref:`xasviewer_exafs_bkg` and
:ref:`xasviewer_exafs_fft`), and Feff fitting (:ref:`xasviewer_feffit`).

There are a few important general notes to mention about XAS Viewer before
going into more detail about how to use it.  First, XAS Viewer is still in
active development.  If you find problems with it or unexpected or missing
functionality, please let us know.  Second, XAS Viewer has many features,
functionality, and concepts in common with Athena and Sixpack. This is
intentional, as we intend XAS Viewer to be a useful alternative to these
applications, possibly with new or better features but also without losing
too many features or requiring too much relearning of concepts or workflow.
As an important example of this compatibility, XAS Viewer can read in and
import data from Athena Project files, and can save these project files as
well, so that if you have lots of data organized with Athena Project Files,
you can use XAS Viewer and Athena on the same datasets.  If you find
features to be missing or different from how Athena or Sixpack work, let us
know.

As a GUI, XAS Viewer is intended to make data processing analysis easy and
intuitive. As a Larch application it is also intended to enable more
complex analysis, batch processing, and scripting of analysis tasks.  To do
this, essentially all the real processing work, including most of the
plotting of data, is done in XAS Viewer through the Larch Buffer (as shown
in :ref:`larchgui_app`) which records the commands as it executes them.  If,
at any point you want to know exactly what XAS Viewer is "really doing",
you can open the Larch Buffer and see the commands being executed.  You can
also copy the code from the Larch buffer to reproduce the analysis steps,
or modify into procedures for batch processing with the Larch scripting
language or with Python.  Essentially all of the data used in XAS Viewer is
available from the Larch buffer.

XAS Viewer will display many different datasets as 2-d line plots.  As with
all such plots made with Larch (see :ref:`plotting-chapter`), these are
highly interactive, customizable, and can produce publication-quality
images.  The plots can be zoomed in and out, and can be configured to
change the colors, linestyles, margins, text for labels, and more. From any
plot window you can use Ctrl-C to copy the image to the clipboard, Ctrl-S
to Save the image as PNG file, or Ctrl-P to print the image with your
systems printer. Ctrl-K will bring up a window with forms to configure the
colors, text, styles and so on. These common options are available from the
File and Options menu of the plotting window.

In particular, clicking on the legend for any labeled curve on a plot will
toggle whether that curve is displayed and partially lighten the label
itself.  This feature of the plotting window means that XAS Viewer may draw
several different traces on the same plot window and allow (or even expect)
you to turn some of them on or off interactively to better view the
different components being shown.  This can be especially useful for
comparing XANES spectra or for inspecting the results of peak fitting.

Also note that many of the entries for numbers on the form panels in XAS
Viewer have a button with a 'pin' icon |pin|.  Clicking anywhere on the
plot window will remember the X and Y values of the last point clicked, and
show the value in the middle section of the status bar, just below the plot
itself. Clicking on any of these 'pin' buttons will insert the appropriate
value (usually the energy) from that "most recently clicked position" into
the corresponding field.
