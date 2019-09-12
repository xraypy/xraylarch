==================================================
Getting Started with Larch
==================================================

Larch provides several tools for working with X-ray spectroscopy data.
First, Larch provides a Python programming library that attempts to include
all the functionality needed visualizing and analyzing X-ray Absorption and
Flourescence spectroscopy data.  It also includes an embedded Python-like
scripting language for interacting with data that can be used either from a
very basic command-line interface or as a callable service.  Finally, Larch
has a few GUI applications built on top of these components for X-ary
absorption spectroscopy data, and for X-ray Fluorescence and Diffraction
mapping.

Because of these different levels of access available, it can be somewhat
confusing to answer the question "What is Larch?" and slightly overwhelming
for new people to know where to get started using it.  We'll try to get you
started using Larch, and then point to next places to go for getting the
most out of it.

First, install Larch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are new to Larch, we recommend installing using the binary installer
for your operating system listed in the :ref:`Table of Larch Installers
<installers_table>`.  On the other hand, if you are familiar with Python
and want to use Larch as a library see :ref:`Downloading and
Installation <install-chapter>` for other ways to install Larch into your
existing Python environment.


Second, use Athena, XASViewer and/or GSEMapViewer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are mostly interested in using Larch as a backend for the Athena and
Artemis programs for XAFS Analysis, just install Larch and the latest
version of Demeter, and Demeter should find and use Larch for EXAFS
Analysis, replacing the older Ifeffit library and its many limitations.

Even using Larch instead of Ifeffit, Athena still has some limitations for
XAFS Analysis, and development and support for it has declined in recent
years.  You may be interested in the XAS Viewer program for XAFS processing
and visualization.  At this writing, :ref:`XAS Viewer <xasviewer-chapter>`
is nearly a complete replacement for Athena, with several improvements in
graphics and handling of large data sets.  XAS Viewer is especially aimed
at XANES Analysis, and so includes robust tools for peak-fitting, and
machine-learning methods such as Principal Component Analysis, Partial
Least Squares and LASSO regression.

If you are a user of the GSECARS microprobe beamline or have XRF Mapping
data from a compatible beamline (XFM at NSLS-II, maybe others), you'll
want to start using the :ref:`GSE Mapviewer <gsemapviewer-chapter>` program
for reading, displaying, and working with X-ray fluorescence maps.  Much of
the documentation here discusses commands you can type in the "Larch
Buffer", available from the Mapviewer program for scripting and more
detailed access to the data in the XRF map HDF5 files.

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
