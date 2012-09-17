====================================
Downloading and Installation
====================================

Prerequisites
~~~~~~~~~~~~~~~

Larch requires Python version 2.6 or higher.  Support for Python 3.X is
partial, in that the core of Larch does work, and numpy, and scipy, and
matplotlib have all been ported to Python 3.X.  But the testing for Python
3.X has been minimal, and the graphical interfaces, based on wxWidgets, has
not yet been ported to Python 3.X.

Numpy, matplotlib, and wxPython are all required for Larch, and scipy is
strongly encouraged (and some functionality depends on it).  These are
simply installed as standard packages on almost all platforms.

.. _larch github repository:   http://github.com/xraypy/xraylarch

All development is being done through the `larch github repository`_.  To
get a read-only copy of the atest version, use::

   git clone http://github.com/xraypy/xraylarch.git


Installation
~~~~~~~~~~~~~~

Installation from source on any platform is::

   python setup.py install


We'll build and distribute Windows binaries and use the Python Package
Index soon....

License
~~~~~~~~~~~~~~~~~

This code and all material associated with it are distributed under the
BSD License:


.. literalinclude:: ../COPYING
