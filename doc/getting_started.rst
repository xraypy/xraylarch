.. _`Larch For XAFS Analysis (youtube.com)`:   https://youtube.com/playlist?list=PLgNIl_xwV_vK4V6CmrsEsahNCAsjt8_Be
==================================================
Getting Started with Larch
==================================================

Larch provides several tools for working with X-ray spectroscopy data.
First, Larch provides a Python programming library that includes (or, at
least aims to include) all the functionality needed for visualizing,
processing, and analyzing X-ray Absorption and Flourescence spectroscopy
data.  Most users will start Larch has a few GUI applications, especially
``XAS Viewer``, ``GSE XRM MapViewer``, and ``XRF Display`` for these.  In
addition, Larch includes an embedded Python-like macro language for
interacting with data that can be used either from a basic command-line
interface or as a callable service from a different programming language
(so that Athena and Artemis can use Larch instead of the older Ifeffit
library).  In fact, most of the Larch GUIs generate and run code in this
"larch macro language" so that it can be recorded for reproducible results
and to assist creating batch scripts and more complicated analysis scripts.

Because of these different levels of access available, it can be somewhat
confusing to answer the question "What is Larch?" and slightly overwhelming
for new people to know where to get started using it.

First, install Larch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are new to Larch, we recommend installing using the binary installer
for your operating system listed in the :ref:`Table of Larch Installers
<installers_table>`.  On the other hand, if you are familiar with Python
and want to use Larch as a library see :ref:`Downloading and Installation
<install-chapter>` for other ways to install Larch into your existing
Python environment.


Second, use XAS Viewer and/or GSE MapViewer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For working with XAS data, you may be interested in the XAS Viewer program
for XAFS processing and visualization.  At this writing, :ref:`XAS Viewer
<xasviewer_app>` includes a "nearly complete" set of tools for analyziing
XAS data, including XANES and EXAFS data processing, visualizaition, and
analysis.  Some instructional videos for using XAS Viewer are at
`Larch For XAFS Analysis (youtube.com)`_.



XAS Viewer is nearly a complete replacement for Athena, but with several
improvements in graphics, handling of large data sets, and some
improvements in XAFS data processing too.  For XANES analysis, XAS Viewer
includes robust tools for peak-fitting, and machine-learning methods such
as Principal Component Analysis, Partial Least Squares and LASSO
regression.

With version 0.9.53, XAS Viewer also provides graphical user interface
tools for running Feff and doing Fitting of Feff Paths to EXAFS
:math:`\chi(k)` spectra.  These tools include a form for browsing CIF
Structures from the American Mineralogist Crystal Structure Database (which
included with Larch), creating Feff6 or Feff8l inputs, running Feff6 or
Feff8l for EXAFS path calculations, and organinizing the results.  There is
also a page in the XAS Viewer for building a sum-of-paths model for an
EXAFS spectrum, working with and constraining Path Parameters, running
"Feff fits" and browsing the results. XAS Viewer always saves the full of
history of commands it runs as code that can be modified or re-run in
batch.  For "Feff fitting" in particular, a fitting script can be saved for
any fit and run either in the Larch macro language or (with uncommenting of
some `import` statements`) run as a Python program.

Larch can also be used as a backend for the Athena and Artemis programs for
XAFS Analysis, just install Larch and the latest version of Demeter, and
Demeter should find and use Larch for EXAFS Analysis, replacing the older
Ifeffit library and its many limitations.

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

The :ref:`XAS Viewer <xasviewer_app>` application can assist you get
started with this, as it keeps a history of all commands it executes that
can be saved and re-run or modified to run in the Larch macro language or
(with including the appropriate `import` statements) as a Python program.
