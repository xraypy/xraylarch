.. xraylarch documentation master file

=====================================
Larch
=====================================

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/
.. _h5py: http://code.google.com/p/h5py/

Larch is an open-source library and toolkit for processing and analyzing
scientific data.  Initially designed for X-ray spectroscopic and scattering
data collected at modern synchrotron sources, Larch provides a wide
selection of algorithms for processing such X-ray data.  It also provides
many tools for organizing complex data sets and general-purpose tools for
processing and analyzing arrays of scientific data.

Larch is written in Python, relies heavily on the wonderful `numpy`_,
`scipy`_, `h5py`_, and `matplotlib`_ libraries. It can be used directly as
a Python library, and it can be extended using Python.  In addition, Larch
provides a Python-like language (a *macro language*, or *domain specific
language*) that is intended to be very easy to use for novices while also
being complete enough for advanced data processing and analysis.

Larch has several related target application areas, including:

  * XAFS analysis, becoming version 2 of the Ifeffit Package for EXAFS analysis.
  * Visualizing and analyzing micro-X-ray fluorescence maps.
  * Quantitative X-ray fluorescence analysis.
  * X-ray standing waves and surface scattering analysis.
  * Data collection software for synchrotron data.

The central idea is that having these otherwise different application areas
connected by a common *macro language* will strengthen the tools available
for all of them.  The macro language can provide a very shallow barrier for
those interested in scripting the manipulation and analysis of their data,
and become the framework upon which new analysis tools can be built.

Currently, Larch provides a complete set of XAFS Analysis tools (replacing
all of the Ifeffit package), has some support for visualizing and analyzing
XRF maps and spectra, and has many extra tools for X-ray spectral analysis,
data handling, and general-purpose data modeling.

.. toctree::
   :maxdepth: 1

   installation.rst
   community.rst
   overview.rst
   tutorial/index.rst
   data/index.rst
   plotting/index.rst
   fitting/index.rst
   xafs/index.rst
   xray/index.rst
   xrf/index.rst
   devel/index.rst
