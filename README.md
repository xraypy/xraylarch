## Larch:  Data Analysis Tools for X-ray Spectroscopy and More


[![A](https://github.com/xraypy/xraylarch/actions/workflows/test-ubuntu.yml/badge.svg)](https://github.com/xraypy/xraylarch/actions/workflows/test-ubuntu.yml)
[![B](https://github.com/xraypy/xraylarch/actions/workflows/test-windows.yml/badge.svg)](https://github.com/xraypy/xraylarch/actions/workflows/test-windows.yml)
[Documentation](http://xraypy.github.io/xraylarch)
.. _scipy: https://scipy.org/
.. _numpy: https://numpy.scipy.org/
.. _matplotlib: https://matplotlib.org/
.. _h5py: https://code.google.com/p/h5py/
.. _Demeter: https://bruceravel.github.io/demeter/



Larch is an open-source library and set of applications for processing and
analyzing X-ray absorption and fluorescence spectroscopy data and X-ray
fluorescence and diffraction image data from synchrotron beamlines.  It is
especially focussed on X-ray absorption fine-structure spectroscopy (XAFS)
including X-ray absorption near-edge spectroscopy (XANES) and extended
X-ray absorption fine-structure spectroscopy (EXAFS). It also supports
visualization and analysis tools for X-ray fluorescence (XRF) spectra and
XRF and X-ray diffraction (XRD) images as collected at scanning X-ray
microprobe beamlines.

Larch is written in Python, making heavy use of the excellent scientific
python libraries (`numpy`_, `scipy`_, `h5py`_, `matplotlib`_, and many
more). Larch can be used as a Python library for processing and analyzing
X-ray spectroscopy and imaging data. In addition, the applications built
with it also use a built-in Python-like macro language for interactive and
batch processing.  This embedded "miniPython" language is intended to be very
easy to use for novices while also being complete enough to automate data
processing and analysis and to encourage and facilitate a gentle transition
to transition from GUI-only analyses to scripted and programmatic analysis
of larger data sets, and allows Larch to be run as a
service, interacting with other processes or languages via XML-RPC, and so
be used by the popular `Demeter`_ XAFS application suite.


Larch is distributed under an open-source license that is nearly identical
to the BSD license.  It is under active and open development centered at
the GeoScoilEnviroCARS sector of the Center for Advanced Radiation Sources at
the University of Chicago has been supported by the US National Science
Foundation - Earth Sciences (EAR-1128799), and Department of Energy
GeoSciences (DE-FG02-94ER14466).  In addition, funding specifically for
Larch was granted by the National Science Foundation - Advanced
CyberInfrastructure (ACI-1450468).

The best citable reference for Larch is M. Newville, *Larch: An Analysis
Package For XAFS And Related Spectroscopies*. Journal of Physics:
Conference Series, 430:012007 (2013).

## Larch Applications

These applications installed with Larch, in addition to a basic Python
library. Here, GUI = Graphical User Interface, CLI = Command Line
Interface, and `beta` indicates a work in progress.


| Application Name  | GUI/CLI    | Description                                            |
| ----------------- |----------- | ------------------------------------------------------ |
| larch             | CLI        | simple shell command-line interface                    |
| Larch GUI         | GUI        | enhanced command-line interface with data browser      |
| Larix             | GUI        | XAFS Processing and Analysis: XANES pre-edge peak      |
| (was XAS Viewer)  |            | fitting, linear analysis, PCA/LASSO, EXAFS processing  |
|                   |            | Running Feff, fitting EXAFS data to Feff paths.        |
| GSE Map Viewer    | GUI        | XRF Map Viewer for GSECARS X-ray microprobe data.      |
| larch_xrf         | GUI        | Display and analyze XRF Spectra.                       |
| larch_xrd1d       | GUI        | Display and work with 1-D XRD patterns, integrate XRD  |
|                   |            | images, search for XRD patterns of known structures    |
| feff6l            | CLI        | Feff 6 EXAFS calculations                              |
| feff8l            | CLI        | Feff 8 EXAFS calculations (no XANES)                   |
| qtrixs            | GUI `beta` | Display RIXS planes, take profiles                     |
