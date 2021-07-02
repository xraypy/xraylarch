.. xraylarch documentation master file

.. _scipy: https://scipy.org/
.. _numpy: https://numpy.scipy.org/
.. _matplotlib: https://matplotlib.org/
.. _h5py: https://code.google.com/p/h5py/
.. _Demeter: https://bruceravel.github.io/demeter/
.. _Dioptas: https://github.com/Dioptas/Dioptas
.. _Feff Project: https://feff.phys.washington.edu/

=====================================
Larch
=====================================

Larch is a open-source library and set of :ref:`applications
<larch_app_table>` for processing and analyzing X-ray absorption and
fluorescence spectroscopy data and X-ray fluorescence and diffraction image
data from synchrotron beamlines.  It aims to be a complete analysis toolkit
for X-ray absorption fine-structure spectroscopy (XAFS) including X-ray
absorption near-edge spectroscopy (XANES) and extended X-ray absorption
fine-structure spectroscopy (EXAFS). It also supports visualization and
analysis tools for X-ray fluorescence (XRF) spectra and XRF and X-ray
diffraction (XRD) images as collected at scanning X-ray microprobe
beamlines.

Larch is written in Python, making heavy use of the excellent scientific
python libraries including `numpy`_, `scipy`_, `h5py`_, `matplotlib`_, and
provides a Python library for processing and analyzing X-ray spectroscopy
and imaging data.  There are a few GUI applications written using this
library for common data visualization and analysis tasks, notably :ref:`XAS
Viewer <xasviewer_app>`, :ref:`GSE Map Viewer <mapviewer_app>`, and
:ref:`XRF Viewer <xrfviewer_app>` as described in more detail below.

While Larch can be used as a Python library, the applications built with
Larch use a Python-like macro language - the "Larch language" - for
interactive and batch processing.  This macro language is available from an
interactive command-line interface through either :ref:`larch
<larchcli_app>` or :ref:`Larch GUI <larchgui_app>` and intended to be very
easy to use for novices while also being complete enough to automate data
processing and analysis.  Most of the GUIs can generate and save "Larch
code" for an analysis session to make reproducible analysis sessions, and
to encourage and facilitate a gentle transition to transition from GUI-only
analyses to scripted and programmatic analysis of larger data sets.  This
macro language also allows Larch to be run as a background service that
other processes can use Larch as the analysis engine.  The popular
`Demeter`_ XAFS application suite can use Larch in this way.

Larch is distribute under an open-source license that is nearly identical
to the BSD license.  It is under active and open development centered at
the GeoScoilEnviroCARS sector of Center for Advanced Radiation Sources at
the University of Chicago has been supported by the US National Science
Foundation - Earth Sciences (EAR-1128799), and Department of Energy
GeoSciences (DE-FG02-94ER14466).  In addition, funding specifically for
Larch was granted by the National Science Foundation - Advanced
CyberInfrastructure (ACI-1450468).

.. _larch_app_table:

**Table of Larch Applications**

    These applications installed with Larch, in addition to a basic Python
    library. Here, GUI = Graphical User Interface, CLI = Command Line
    Interface, and `beta` indicates a work in progress. The Feff6L and
    Feff8L codes are the open-source versions of Feff6 and Feff8, written
    by the `Feff Project`_, and included with Larch by permission and with
    license to redistrubute.

  +---------------------------------------+------------+---------------------------------------------------------+
  | Application Name                      | GUI/CLI    | Description                                             |
  +=======================================+============+=========================================================+
  | :ref:`XAS Viewer <xasviewer_app>`     | GUI        | XAFS Processing and Analysis: XANES pre-edge peak       |
  |                                       |            | fitting, linear analysis, PCA/LASSO, EXAFS extraction   |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`larch <larchcli_app>`           | CLI        | simple shell command-line interface                     |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`Larch GUI <larchgui_app>`       | GUI        | enhanced command-line interface with data browser       |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`GSE Map Viewer <mapviewer_app>` | GUI        | XRF Map Viewer for GSECARS X-ray microprobe data.       |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`XRF Viewer <xrfviewer_app>`     | GUI        | Display and Analyze XRF Spectra.                        |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`feff6l <feff6l_app>`            | CLI        | Feff 6 EXAFS calculations                               |
  +---------------------------------------+------------+---------------------------------------------------------+
  | :ref:`feff8l <feff8l_app>`            | CLI        | Feff 8 EXAFS calculations (no XANES)                    |
  +---------------------------------------+------------+---------------------------------------------------------+
  | 1D XRD Viewer                         | GUI `beta` | Display and work with 1-D XRD patterns                  |
  +---------------------------------------+------------+---------------------------------------------------------+
  | 2D XRD Viewer                         | GUI `beta` | Display  XRD images                                     |
  +---------------------------------------+------------+---------------------------------------------------------+
  | qtrixs                                | GUI `beta` | Display RIXS planes, take profiles                      |
  +---------------------------------------+------------+---------------------------------------------------------+

Note that the `Dioptas`_ program for viewing and calibrating 2-D XRD
patterns, written and maintained by Clemens Prescher has been included with
earlier versions of Larch. It is no longer included, but we recommend
downloading and installing that for working with XRD image data.

.. _contents:

Table of Contents
============================

.. toctree::
   :maxdepth: 2
   :numbered:

   installation.rst
   getting_started.rst
   overview.rst
   guis.rst
   wxxas_viewer.rst
   wxmap_viewer.rst
   qtrixs.rst
   python.rst
   larchlang.rst
   data.rst
   plotting.rst
   fitting
   xafs.rst
   xray.rst
   xrf.rst
   bibliography.rst
