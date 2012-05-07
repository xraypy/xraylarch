===================================================
StepScan Downloading and Installation
===================================================


Pre-requisites
~~~~~~~~~~~~~~~~~~

.. _pyepics:             http://github.com/pyepics/pyepics
.. _h5py:                http://code.google.com/p/h5py/
.. _numpy:               http://numpy.scipy.org/
.. _scipy:               http://scipy.org/
.. _sqlalchemy:          http://www.sqlalchemy.org/
.. _wxPython:            http://www.wxpython.org/
.. _hdf5:                http://www.hdfgroup.org/HDF5/
.. _h5py:                http://code.google.com/p/h5py/
.. _Python Setup Tools:  http://pypi.python.org/pypi/setuptools


The StepScan library needs `pyepics`_, a Python library for Epics Channel
Access, and, in fact, is an add-on package to that library.  StepScan also
requires a few near-standard python modules: `numpy`_, `scipy`_,
`sqlalchemy`_, and `wxPython`_.  In order to save data to the HDF5, the
`hdf5`_ library, and the `h5py`_ module are also required.

Downloads
~~~~~~~~~~~~~

.. _stepscan-0.2.tar.gz (CARS): http://cars9.uchicago.edu/software/python/stepscan/src/stepscan-0.2.tar.gz
.. _stepscan-0.2.tar.gz (PyPI): http://pypi.python.org/packages/source/s/stepscan/stepscan-0.2.tar.gz

The latest stable version is available from PyPI or CARS (Univ of Chicago):

+----------------------+------------------+--------------------------------------+
|  Download Option     | Python Versions  |  Location                            |
+======================+==================+======================================+
|  Source Kit          | 2.6, 2.7, 3.2    | -  `stepscan-0.2.tar.gz (PyPI)`_     |
|                      |                  | -  `stepscan-0.2.tar.gz (CARS)`_     |
+----------------------+------------------+--------------------------------------+

Installers for Windows will be made available soon.

If you have `Python Setup Tools`_  installed, you can download and install with::

   easy_install -U stepscan


Development Version
~~~~~~~~~~~~~~~~~~~~~~~~

To get the latest development version, use::

   git clone http://github.com/pyepics/stepscan.git

Installation
~~~~~~~~~~~~~~

To install from source, use::

   python setup.py install

from the StepScan folder.


Running the StepScan GUI
==========================

Soon, this will work:


   python stepscan_gui.py

or click on the icon.

Using StepScan from Python
==============================

To use StepScan from Python scripts, use::

    from epics import stepscan


