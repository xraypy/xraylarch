.. xraylarch documentation master file

=====================================
Larch
=====================================

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/
.. _h5py: http://code.google.com/p/h5py/

Larch is an open-source library and analysis toolkit for processing
scientific data.  Initially designed for x-ray spectroscopic and scattering
data collected at modern synchrotrons and x-ray sources, Larch also
provides many general-purpose processing and analysis tools for dealing
with arrays of scientific data and organize complex data sets.

Larch is written in Python, making heavy use of the wonderful `numpy`_,
`scipy`_, `h5py`_, and `matplotlib`_ libraries, and can be used directly as
a Python library or extended using Python.  In addition, Larch provides a
Python-like language (a *macro language*, or *domain specific language*)
that is intended to be very easy to use for novices while also being
complete enough for advanced data processing and analysis.

Larch has several related target application areas, including:

  * XAFS analysis, becoming version 2 of the Ifeffit Package.
  * Visualizing and analyzing micro-X-ray fluorescence maps.
  * Quantitative X-ray fluorescence analysis.
  * X-ray standing waves and surface scattering analysis.
  * Data collection software for synchrotron data.

The essential idea is that having these different areas connected by a
common *macro language* will strengthen the analysis tools available for
all of them, and provide a very shallow barrier for those interested in
scripting the manipulation and analysis of their data.

Currently, Larch provides a complete set of XAFS Analysis tools (replacing
all of the Ifeffit package), has some support for visualizing and analyzing
XRF maps and spectra, and has many extra tools for X-ray spectral analysis,
data handling, and general-purpose data modeling.

.. toctree::
   :maxdepth: 1

   downloads/index.rst
   overview/index.rst
   tutorial/index.rst
   data/index.rst
   plotting/index.rst
   fitting/index.rst
   xafs/index.rst
   xray/index.rst
   xrf/index.rst
   devel/index.rst

