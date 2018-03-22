==================================================
Getting Started with Larch
==================================================

Larch provides both GUI applications and a programming library for
visualizing and analyzing X-ray spectroscopy data.  It can be slightly
overwhelming to know where to get started with Larch.  We'll try to get you
started using Larch, and then point to next place to go for getting the
most out of it.

First, install Larch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are new to Larch, we recommend installing from the appropriate
installer for your operating system listed in the :ref:`Table of Larch
Installers <installers_table>`.

If you are familiar with Python and want to use Larch as a library, see the
:ref:`Downloading and Installation <install-chapter>` chapter.


Second, use GSEMapViewer, XAS_Viewer, or Larch_GUI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are a user of the GSECARS microprobe, you'll want to start using the
GSE Mapviewer program for reading, displaying, and working with X-ray
fluorescence maps.   Much of the documentation here discusses commands you
can type in the "Larch Buffer", available from the Mapviewer program for
scripting and more detailed access to the data in the XRF map HDF5 files.


If you are mostly interested in using Larch as a backend for the Athena and
Artemis programs for XAFS Analysis, just install Larch and the latest
version of Demeter, and Demeter should find and use Larch for EXAFS
Analysis, replacing the older Ifeffit library and its many limitations.
You may also be interested in the XAS_Viewer program for XANES
visualization and peak fitting, and aiming for more XANES analysis tools.

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
