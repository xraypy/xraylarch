.. _Larch For XAFS Analysis (youtube.com): https://youtube.com/playlist?list=PLgNIl_xwV_vK4V6CmrsEsahNCAsjt8_Be


==================================================
Getting Started with Larch
==================================================

Larch provides several tools for working with X-ray spectroscopy data.
First, Larch has a few GUI applications, especially ``Larix``, ``GSE
XRM MapViewer``, and ``LarchXRF`` for working with X-ray spectroscopy
data.  Second, Larch provides a Python programming library that
includes (or, at least aims to include) all the functionality needed
for visualizing, processing, and analyzing X-ray Absorption and
Fluorescence spectroscopy data.  The GUIs are all built on top of this
Python library.



First, install Larch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are new to Larch, we recommend installing using the binary
installer for your operating system listed in the :ref:`Table of Larch
Installers <installers_table>`.  If you are familiar with Python and
want to use Larch as a library see :ref:`Downloading and Installation
<install-chapter>` for other ways to install Larch into your existing
Python environment.


Second, use Larix (was XAS Viewer) and/or GSE MapViewer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

   Instructional videos for using Larix are at `Larch For XAFS Analysis (youtube.com)`_.

The :ref:`Larix <larix_app>` (was XAS Viewer) Graphical User Interface program
provides a complete set of tools for the visualization, processing, and
analysis of XAS data, Both XANES and and EXAFS data processing and fitting are
supported.

Larix aims to be a complete (or nearly so) replacement for Athena and
Artemis programs. There are several improvements in graphics and
handling of large data sets, and some improvements in XAFS data
processing too.  In particular, For XANES analysis, Larix includes
more robust tools for peak-fitting, and machine-learning methods such
as Principal Component Analysis, Partial Least Squares and LASSO
regression.

Larix provides graphical user interface tools for running Feff to to simulate
EXAFS :math:`\chi(k)` spectra.  A graphical form for browsing 20,000 CIF
Structures from the American Mineralogist Crystal Structure Database is
included, and you can import other CIF files or structure files from DFT or
other calculations. Any of these structure files can be used to create inputs
for and run Feff (either Feff6 or Feff8l) to calculate EXAFS path
contributions and organize these results.

Larix also includes a form to build a sum-of-paths model for an EXAFS spectrum
from a set of Feff path and to help you fit a sum of Feff Paths to
experimental EXAFS :math:`\chi(k)` spectra.  This includes friendly tools to
set up EXAFS fitting parameters, working with and constraining Path
Parameters, running fits and browsing the results.

For all its processing and fitting (pre-edge peaks, PCA, Feff-fit), Larix
always saves the full of history of commands it runs as code that can be
modified or re-run in batch.  For "Feff fitting" in particular, a fitting
script can be saved for any fit and run either in the Larch macro language or
(with uncommenting of some `import` statements`) run as a standalone Python
script.  Larch can also be used as a backend for the Athena and Artemis
programs for XAFS Analysis. When you install Larch and the latest version of
Demeter, and Demeter should find and use Larch for EXAFS Analysis, replacing
the older Ifeffit library and its many limitations.

If you are a user of the GSECARS microprobe beamline or have XRF Mapping
data from a compatible beamline (XFM at NSLS-II, maybe others), you'll want
to start using the :ref:`GSE Mapviewer <mapviewer_app>` program for
reading, displaying, and working with X-ray fluorescence maps.  Much of the
documentation here discusses commands you can type in the "Larch Buffer",
available from the Mapviewer program for scripting and more detailed access
to the data in the XRF map HDF5 files.

If you are a general-purpose user or ready for more control over data
analysis for many types of data, the Larch GUI can help you browse through
the available commands and data, and provide a good starting point for
interactive, exploratory data analysis.


Third, start scripting with Larch and/or Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once you've done a little bit of GUI or interactive work, you may be ready
to write scripts.  Such scripts can help you automate repeated tasks and
can build and remember more complex analyses.  The combination of the high
level commands of Larch and the interactive command-line GUI for
exploratory data analysis are a great way to get started in writing your
own scripts and building up more sophisticated programs.

The :ref:`Larix <larix_app>` application can assist you get started with this,
as it keeps a history of all commands it executes that can be saved and re-run
or modified to run in the Larch macro language or (with including the
appropriate `import` statements) as a Python program.
