.. xraylarch documentation master file

=====================================
Larch
=====================================

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.sourceforge.net/
.. _h5py: http://code.google.com/p/h5py/

Larch is a scientific data processing language that is designed to be easy
to use for novices while also being complete enough complete enough for
advanced data processing and analysis Larch provides a wide range of
functionality for dealing with arrays of scientific data, and basic tools
to make it easy to use and organize complex data.  Written in Python, and
making heavy use of the wonderful libraries `numpy`_, `scipy`_, `h5py`_,
and `matplotlib`_, Larch has syntax very close to Python, and can be easily
extended with Python.

Larch has been primarily developed for dealing with x-ray spectroscopic and
scattering data, especially the kind of data collected at modern
synchrotrons and x-ray sources. It has several related target application areas:

  * XAFS analysis, becoming version Ifeffit Version2.
  * tools for micro-XRF mapping visualization and analysis.
  * quantitative XRF analysis.
  * X-ray standing waves and surface scattering analysis.
  * Data collection software for the above.

The idea is that having these different problem areas connected by a common
*macro language* will strengthen the analytic tools for all of them.

.. toctree::
   :maxdepth: 1

   contents
   overview
   installation
   tutorial/index.rst
   developers
   fitting
   xafs/index.rst
   xray/index.rst
