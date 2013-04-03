.. xraylarch documentation master file

=====================================
Larch
=====================================

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/
.. _h5py: http://code.google.com/p/h5py/

Larch is a scientific data processing language.  Initially designed for
x-ray spectroscopic and scattering data collected at modern synchrotrons
and x-ray sources, it can also be used for general-purpose processing of
scientific data.  Larch is intended to be very easy to use for novices,
while also being complete enough for advanced data processing and
analysis. Larch provides a wide range of functionality for dealing with
arrays of scientific data, and basic tools to make it easy to use and
organize complex data.  Written in Python, and making heavy use of the
wonderful libraries `numpy`_, `scipy`_, `h5py`_, and `matplotlib`_, Larch
has syntax very close to Python, and can be easily extended with Python.

Larch has several related target application areas:

  * XAFS analysis, becoming version 2 of the Ifeffit Package.
  * Visualizing and analyzing micro-X-ray fluorescence maps.
  * Quantitative X-ray fluoresceence analysis.
  * X-ray standing waves and surface scattering analysis.
  * Data collection software for synchrotron data.

The essential idea is that having these different areas connected by a
common *macro language* will strengthen the analysis tools available for
all of them.

Currently, Larch provides a complete set of XAFS Analysis tools (replacing
all of the Ifeffit package), has some support for visualizing and analyzing
XRF maps and spectra, and has many extra tools for X-ray spectral analysis,
data handling, and general-purpose data modeling.

.. toctree::
   :maxdepth: 3

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
