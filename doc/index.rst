.. xraylarch documentation master file

.. include:: _config.rst


=====================================
Larch
=====================================

Larch is a open-source library and set of :ref:`applications <larch_app_table>`
for processing and analyzing X-ray absorption and fluorescence spectroscopy
data and X-ray fluorescence and diffraction image data from synchrotron
beamlines.  Larch provides a comprehensive set fo analysis tools for X-ray
absorption fine-structure spectroscopy (XAFS), including both X-ray absorption
near-edge spectroscopy (XANES) and extended X-ray absorption fine-structure
spectroscopy (EXAFS).  Larch also provides visualization and analysis tools for
X-ray fluorescence (XRF) spectra and XRF and X-ray diffraction (XRD) images as
collected at scanning X-ray microprobe beamlines.

Larch is written in Python and relies on the excellent scientific
python libraries including `numpy`_, `scipy`_, `h5py`_,
`matplotlib`_. In turn, Larch provides a comprehensive Python library
for processing and analyzing X-ray spectroscopy and imaging data.
Several Python libraries - `xraydb`_, `larixite`_, `lmfit`_,
`asteval`_, `wxmplot`_, and `pyshortcuts`_ - were originally built for
or as a part of Larch and then spun-off as separate libraries that can
be used by the broader X-ray and scientific programming communities.

Larch includes a few GUI applications that provide user-friendly and
interactive data visualization for many common X-ray analysis tasks. The most
notable of these are :ref:`Larix <larix_app>` (was XAS Viewer), :ref:`GSE
Map Viewer <mapviewer_app>`, and :ref:`Larch XRF <larchxrf_app>` (formerly XRF
Viewer).

Larch also provides a Python-like macro language - the "Larch language" - for
interactive and batch processing.  This macro language is an isolated,
restricted "mini-Python" (from `asteval`_), intended to be both easy to use and
complete enough to automate data processing and analysis available as an
interactive command-line interface.  This command-line interface is available
either from the :ref:`larch <larchcli_app>` or :ref:`Larch GUI <larchgui_app>`.
This macro language is not recommended for serious programming, but it is an
important part of the Larch package and can be viewed as the bridge between
using the GUIs for fully interactive, non-coding analysis, and writing
batch-processing analysis scripts.

Most of the GUIs (notably, :ref:`Larix <larix_app>`) work by generating and
executing this "Larch code", with all of the real work done through this macro
language.  This allows for self-documented and reproducible analysis sessions,
and facilitates transitioning from GUI-only analyses to scripting, batch
processing, and programmatic analysis of larger data sets.  That is, with a few
simple changes and added boilerplate code, the Larch macro code saved from a
GUI session becomes a Python program.  This macro language also allows Larch to
be run as a background service so that other processes can use Larch as the
analysis engine - this was the original motivation and is still an important
consideration.  The popular `Demeter`_ XAFS application suite can use Larch in
this way, though the :ref:`Larix <larix_app>` now contains almost all of the
features of `Demeter`_ and is much more actively being developed and
maintained.

Larch is distribute under an open-source license that is nearly
identical to the MIT or 2-clause BSD license.  It is under active and
open development centered at the GeoScoilEnviroCARS sector of Center
for Advanced Radiation Sources at the University of Chicago.  Support
has come from the US National Science Foundation Earth Sciences
Division, currently through *SEES: Synchrotron Earth and Environmental
Science* (EAR-222327), and previously from NSF Earth Sciences Division
(EAR-1128799), and Department of Energy GeoSciences
(DE-FG02-94ER14466).  Funding specifically for Larch was granted by
the National Science Foundation - Advanced CyberInfrastructure
(ACI-1450468).

.. _larch_app_table:

**Table of Larch Applications**

    These applications installed with Larch, in addition to a basic Python
    library. Here, GUI = Graphical User Interface, CLI = Command Line
    Interface, and `beta` indicates a work in progress. The Feff6L and
    Feff8L codes are the open-source versions of Feff6 and Feff8, written
    by the `Feff Project`_, and included with Larch by permission and with
    license to redistribute.

.. csv-table::
    :delim: |
    :header-rows: 1
    :widths: 20 15 65

    Application Name                           | GUI/CLI    | Description
    :ref:`Larix <larix_app>` (was XAS Viewer)  | GUI        | XAFS Processing and Analysis: XANES pre-edge peak fitting, linear analysis, PCA/LASSO, EXAFS background subtraction, running Feff, EXAFS Feff-fitting
    :ref:`larch <larchcli_app>`                | CLI        | simple shell command-line interface
    :ref:`Larch GUI <larchgui_app>`            | GUI        | enhanced command-line interface with data browser
    :ref:`GSE Map Viewer <mapviewer_app>`      | GUI        | XRF Map Viewer for GSECARS X-ray microprobe data.
    :ref:`Larch_XRF <larchxrf_app>`            | GUI        | Display and Analyze XRF Spectra.
    :ref:`Larch_XRD1D <larchxrd1d_app>`        | GUI        | Display and work with 1-D XRD patterns
    :ref:`feff6l <feff6l_app>`                 | CLI        | Feff 6 EXAFS calculations
    :ref:`feff8l <feff8l_app>`                 | CLI        | Feff 8 EXAFS calculations (no XANES)
    qtrixs                                     | GUI `beta` | Display RIXS planes, take profiles


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
   larix.rst
   wxmap_viewer.rst
   xrd1d_viewer.rst
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
