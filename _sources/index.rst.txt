.. xraylarch documentation master file

=====================================
Larch
=====================================

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/
.. _h5py: http://code.google.com/p/h5py/

Larch is an open-source library and toolkit for processing and analyzing
X-ray spectroscopic and scattering data collected at modern synchrotron
sources.  It also provides a wide selection of tools for organizing complex
data sets and processing and analyzing arrays of scientific data.

Larch is written in Python and relies heavily on the many scientific python
libraries including `numpy`_, `scipy`_, `h5py`_, and `matplotlib`_.  The
Larch package provides several GUI applications for visualization and
analysis of scientific data sets.  For programming and scripting, Larch can
also be used as a Python library or from its own Python-like macro language
that aims to be very easy to use for novices while also being complete
enough for advanced data processing and analysis.

Larch has several related target application areas:

  * XAFS analysis, becoming version 2 of the Ifeffit Package for EXAFS analysis.
  * Visualizing and analyzing micro-X-ray fluorescence and X-ray diffraction maps.
  * Quantitative X-ray fluorescence analysis.
  * Data collection software for synchrotron data.

A key idea is that these otherwise different application areas can share many
components and algorithms.  Connecting these through a common *macro language*
will strengthen the tools available for all of these areas.  In addition, the
macro language can provide a very shallow barrier for those interested in
scripting the manipulation and analysis of their data, while providing a
scripted, reproducible, and extensible analysis that can become the framework
upon which new analysis tools can be built.

Currently, Larch provides a complete set of XAFS Analysis tools (replacing all
of the Ifeffit package), has some support for visualizing and analyzing XRF
and XRD maps, and has many extra tools for X-ray spectral analysis, data
handling, and general-purpose data modeling.


Larch includes a Python several applications.

The following table lists the main Larch applications.  New and
in-development features and application will be explicitly described as
"beta".

.. _larch_app_table:

**Table of Larch Applications and Programs**
	The applications installed with Larch. Here, GUI = Graphical User
	Interface, CLI = Command Line Interface, and `beta` indicates a
	work in progress.


  +----------------------+-----------+---------------------------------------+
  | Application Name     | GUI / CLI | Description                           |
  +======================+===========+=======================================+
  | larch                | CLI       | simple command-lne interface          |
  +----------------------+-----------+---------------------------------------+
  | larch_gui            | GUI       | enhanced command-lne interface        |
  |                      |           | with data browser                     |
  +----------------------+-----------+---------------------------------------+
  | gse_mapviewer        | GUI       | XRF Map Viewer for data from the      |
  |                      |           | GSECARS X-ray microprobe              |
  +----------------------+-----------+---------------------------------------+
  | xas_viewer           | GUI       | Display XANES data, and Pre-edge      |
  |                      |           | Peak Fitting.                         |
  +----------------------+-----------+---------------------------------------+
  | xrfdisplay           | GUI       | Display XRF Spectra                   |
  +----------------------+-----------+---------------------------------------+
  | 1D XRD Viewer        | GUI       | Display and work with XRD diffraction |
  |                      |           | patterns (beta).                      |
  +----------------------+-----------+---------------------------------------+
  | 2D XRD Viewer        | GUI       | Display and work with XRD diffraction |
  |                      |           | images (beta).                        |
  +----------------------+-----------+---------------------------------------+
  | feff6l               | CLI       | Feff 6 EXAFS calculations             |
  +----------------------+-----------+---------------------------------------+
  | feff8l               | CLI       | Feff 8 EXAFS calculations - no XANES  |
  +----------------------+-----------+---------------------------------------+

Larch is under active and open development, and has support from the U. S. National Science
Foundation.


.. toctree::
   :maxdepth: 1

   getting_started.rst
   installation.rst
   community.rst
   overview.rst
   guis/index.rst
   tutorial/index.rst
   data/index.rst
   plotting/index.rst
   fitting/index.rst
   xafs/index.rst
   xray/index.rst
   xrf/index.rst
   devel/index.rst
   biblio.rst
