.. xraylarch documentation master file

.. _scipy: https://scipy.org/
.. _numpy: https://numpy.scipy.org/
.. _matplotlib: https://matplotlib.org/
.. _h5py: https://code.google.com/p/h5py/
.. _Demeter: https://bruceravel.github.io/demeter/
.. _Dioptas: https://github.com/Dioptas/Dioptas
.. _Feff Project: http://feff.phys.washington.edu/

=====================================
Larch
=====================================

Larch is a open-source library and set of :ref:`applications <larch_app_table>`
for processing and analyzing X-ray absorption and fluorescence spectroscopy data
and X-ray fluorescence and diffraction image data from synchrotron beamlines.
It is especially focussed on X-ray absorption fine-structure spectroscopy (XAFS)
including X-ray absorption near-edge spectroscopy (XANES) and extended X-ray
absorption fine-structure spectroscopy (EXAFS). It also supports visualization
and analysis tools for X-ray fluorescence (XRF) spectra and XRF and X-ray
diffraction (XRD) images as collected at scanning X-ray microprobe beamlines.

Larch is written in Python, making heavy use of the excellent scientific python
libraries (`numpy`_, `scipy`_, `h5py`_, `matplotlib`_,and many more). Larch can
be used as a Python library for processing and analyzing X-ray spectroscopy and
imaging data. In addition, the applications built with it also use a built-in
Python-like macro language for interactive and batch processing.  This
domain-specific language is intended to be very easy to use for novices while
also being complete enough to automate data processing and analysis and to
encourage and facilitate a gentle transition to transition from GUI-only
analyses to scripted and programmatic analysis of larger data sets.  This macro
language also allows Larch to be run as a service, interacting with other
processes or languages via XML-RPC, and so be used by the popular `Demeter`_
XAFS application suite.

Larch is distribute under an open-source license that is nearly identical to the
BSD license.  It is under active and open development centered at the
GeoScoilEnviroCARS sector of Center for Advanced Radiation Sources at the
University of Chicago has been supported by the US National Science Foundation -
Earth Sciences (EAR-1128799), and Department of Energy GeoSciences
(DE-FG02-94ER14466).  In addition, funding specifically for Larch was granted by
the National Science Foundation - Advanced CyberInfrastructure (ACI-1450468).

.. _larch_app_table:

**Table of Larch Applications**

    These applications installed with Larch, in addition to a basic Python library. Here, GUI =
    Graphical User Interface, CLI = Command Line Interface, and `beta` indicates a work in
    progress.  The `Dioptas`_ program is written and maintained by Clemens Prescher, and included
    with Larch.  The Feff6L and Feff8L codes are written by the `Feff Project`_, and included with
    Larch by permission.

  +---------------------------------------+------------+---------------------------------------------------------+
  | Application Name                      | GUI/CLI    | Description                                             |
  +=======================================+============+=========================================================+
  | :ref:`larch <larchcli_app>`           | CLI        | simple shell command-line interface                     |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`Larch GUI <larchgui_app>`       | GUI        | enhanced command-line interface with data browser       |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`XAS Viewer <xasviewer_app>`     | GUI        | XAFS Processing and Analysis: XANES pre-edge peak       |
  |                                       |            | fitting, linear analysis, PCA/LASSO, EXAFS extraction   |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`GSE Map Viewer <mapviewer_app>` | GUI        | XRF Map Viewer for GSECARS X-ray microprobe data.       |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`XRF Viewer <xrfviewer_app>`     | GUI        | Display and Analyze XRF Spectra.                        |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`feff6l <feff6l_app>`            | CLI        | Feff 6 EXAFS calculations                               |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`feff8l <feff8l_app>`            | CLI        | Feff 8 EXAFS calculations (no XANES)                    |
  +---------------------------------------+------------+---------------------------------------------------------+
  | `Dioptas`_                            | GUI        | Display XRD images, calibrate to XRD patterns.          |
  +---------------------------------------+------------+---------------------------------------------------------+
  | 1D XRD Viewer                         | GUI `beta` | Display and work with 1-D XRD patterns                  |
  +---------------------------------------+------------+---------------------------------------------------------+
  | 2D XRD Viewer                         | GUI `beta` | Display  XRD images                                     |
  +---------------------------------------+------------+---------------------------------------------------------+
  | qtrixs                                | GUI `beta` | Display RIXS planes, take profiles                      |
  +---------------------------------------+------------+---------------------------------------------------------+

.. _contents:

Table of Contents
============================

.. toctree::
   :maxdepth: 3
   :numbered:

   installation.rst
   getting_started.rst
   overview.rst
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
