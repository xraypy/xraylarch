.. xraylarch documentation master file

=====================================
Larch
=====================================

.. _scipy: https://scipy.org/
.. _numpy: https://numpy.scipy.org/
.. _matplotlib: https://matplotlib.org/
.. _h5py: https://code.google.com/p/h5py/
.. _Dioptqs: https://github.com/Dioptas/Dioptas

Larch is an open-source library and set of applications for processing and
analyzing X-ray spectroscopic, imaging, and scattering data collected at
synchrotron sources.  Larch is written in Python, making heavy use of many
scientific python libraries (`numpy`_, `scipy`_, `h5py`_, `matplotlib`_,
and many more).  It providing a Python package for processing and analyzing
X-ray absorption and fluorescence spectra and X-ray fluorescence and
diffraction image data, as well as having some support for processing X-ray
diffraction data.  In addition to providing a Python package for
programmers, Larch comes with several GUI applications for visualizing,
processing, and analyzing X-ray absorption spectroscopy and fluorescence
and diffraction imaging data.


Larch has several related target application areas:

  * XAFS analysis, replacing and extending the Ifeffit Package for EXAFS analysis.
  * Visualizing and analyzing micro-X-ray fluorescence and X-ray diffraction maps.
  * Quantitative X-ray fluorescence analysis.
  * Data collection software for synchrotron data.
  * Providing simple access to tabulated X-ray properties of the elements
    and materials.

By using the scientific Python suite of software, these otherwise different
application areas can share many components and algorithms.

While Larch is intended to be used as a Python library, it also comes with
a built-in Python-like macro language that aims to be very easy to use for
novices while also being complete enough for advanced data processing and
analysis.  This macro language is available in all the GUI applications for
automating analysis tasks and to help the GUI user transition from GUI-only
analyses to scripted and programmatic analysis of larger data sets.

The following table lists the main Larch applications.  New and
in-development features and application will be explicitly described as
"beta".

.. _larch_app_table:

**Table of Larch Applications and Programs**

	These applications installed with Larch. Here, GUI = Graphical User
	Interface, CLI = Command Line Interface, and `beta` indicates a work in
	progress.  The `Dioptas`_ program is written and maintained by Clemens
	Prescher and included with Larch.


  +----------------------+-----------+---------------------------------------------------------+
  | Application Name     | GUI / CLI | Description                                             |
  +======================+===========+=========================================================+
  | larch                | CLI & GUI | simple 'shell' command-line interface, or enhanced      |
  |                      |           | enhanced command-line interface with data browser       |
  +----------------------+-----------+---------------------------------------------------------+
  | xas_viewer           | GUI       | XAFS Processing and Analysis: XANES pre-edge peak       |
  |                      |           | fitting, linear analysis, PCA/LASSO, EXAFS extraction   |
  +----------------------+-----------+---------------------------------------------------------+
  | gse_mapviewer        | GUI       | XRF Map Viewer for GSECARS X-ray microprobe data.       |
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
  | feff8l               | CLI       | Feff 8 EXAFS calculations (no XANES)                    |
  +----------------------+-----------+---------------------------------------------------------+
  | qtrixs               | `beta`    | Display RIXS planes, take profiles                      |
  +----------------------+-----------+---------------------------------------------------------+


Larch is under active and open development, and has support from the U. S. National Science
Foundation.


.. toctree::
   :maxdepth: 2

   installation.rst
   getting_started.rst
   guis.rst
   xasviewer/index.rst
   gsemapviewer/index.rst
   qtrixs/index.rst
   tutorial/index.rst
   data/index.rst
   plotting/index.rst
   fitting/index.rst
   xafs/index.rst
   xray/index.rst
   xrf/index.rst
   devel/index.rst
   biblio.rst
