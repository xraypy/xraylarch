.. xraylarch documentation master file

=====================================
Larch
=====================================

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/
.. _h5py: http://code.google.com/p/h5py/

Larch is an open-source library and toolkit for processing and analyzing
X-ray spectroscopic and scattering data collected at synchrotron sources.
It provides a wide range of tools for organizing complex data sets
and processing and analyzing arrays of scientific data.

Larch is written in Python and relies heavily on the many scientific python
libraries including `numpy`_, `scipy`_, `h5py`_, and `matplotlib`_.  The
Larch Python package provides tools for manipulating and analyzing X-ray
absorption and fluorescence spectroscopy data, and X-ray fluoresnce and
diffraction imaging data. As well as providing a Python library, Larch
comes with a few GUI applications specifically for visualizing and
analyzing X-ray absorption spectroscopy and fluorescence and diffrction
imaging data.  While Larch can be used as a Python library, it also uses
its own Python-like macro language that aims to be very easy to use for
novices while also being complete enough for advanced data processing and
analysis.

Larch has several related target application areas:

  * XAFS analysis, replacing and extending the Ifeffit Package for EXAFS analysis.
  * Visualizing and analyzing micro-X-ray fluorescence and X-ray diffraction maps.
  * Quantitative X-ray fluorescence analysis.
  * Data collection software for synchrotron data.
  * Providing simple access to tabulated X-ray properties of the elements
    and materials.

A key idea is that these otherwise different application areas can share
many components and algorithms.  Connecting these through a common library
will strengthen the tools available for all of these areas.  In addition,
providing a very high-level *macro language* can allow a very shallow
barrier to scripting or batch-processing data analysis in a reproducible
and extensible way that can be used as the foundation of new and more
comprehensive analysis tools.

Currently, Larch provides a complete set of XAFS Analysis tools (replacing
all of the Ifeffit package), supports the visualization and analysis of XRF
and XRD maps, and has many extra tools for X-ray spectral analysis, data
handling, and general-purpose data modeling.  Larch includes a full
scientific Python environment and several applications.

The following table lists the main Larch applications.  New and
in-development features and application will be explicitly described as
"beta".

.. _larch_app_table:

**Table of Larch Applications and Programs**
	The applications installed with Larch. Here, GUI = Graphical User
	Interface, CLI = Command Line Interface, and `beta` indicates a
	work in progress.


  +----------------------+-----------+---------------------------------------------------------+
  | Application Name     | GUI / CLI | Description                                             |
  +======================+===========+=========================================================+
  | larch                | CLI       | simple command-lne interface                            |
  +----------------------+-----------+---------------------------------------------------------+
  | larch_gui            | GUI       | enhanced command-lne interface with data browser        |
  +----------------------+-----------+---------------------------------------------------------+
  | gse_mapviewer        | GUI       | XRF Map Viewer for GSECARS X-ray microprobe data.       |
  +----------------------+-----------+---------------------------------------------------------+
  | xas_viewer           | GUI       | Display XANES data, and Pre-edge Peak Fitting.          |
  +----------------------+-----------+---------------------------------------------------------+
  | xrfdisplay           | GUI       | Display and analyze XRF Spectra.                        |
  +----------------------+-----------+---------------------------------------------------------+
  | Dioptas              | GUI       | Display XRD images, calibrate to XRD patterns.          |
  +----------------------+-----------+---------------------------------------------------------+
  | 1D XRD Viewer        | GUI       | Display and work with 1-D XRD patterns (beta).          |
  +----------------------+-----------+---------------------------------------------------------+
  | 2D XRD Viewer        | GUI       | Display  XRD images (beta)                              |
  +----------------------+-----------+---------------------------------------------------------+
  | feff6l               | CLI       | Feff 6 EXAFS calculations                               |
  +----------------------+-----------+---------------------------------------------------------+
  | feff8l               | CLI       | Feff 8 EXAFS calculations - no XANES                    |
  +----------------------+-----------+---------------------------------------------------------+

Larch is under active and open development, and has support from the U. S. National Science
Foundation.


.. toctree::
   :maxdepth: 1

   getting_started.rst
   installation.rst
   community.rst
   overview.rst
   guis.rst
   xasviewer/index.rst
   gsemapviewer/index.rst
   tutorial/index.rst
   data/index.rst
   plotting/index.rst
   fitting/index.rst
   xafs/index.rst
   xray/index.rst
   xrf/index.rst
   devel/index.rst
   biblio.rst
