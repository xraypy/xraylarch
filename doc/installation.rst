====================================
Downloading and Installation
====================================

Prerequisites
~~~~~~~~~~~~~~~

Larch requires Python version 2.6 or higher.  Support for Python 3.X is
partial, in that the core of Larch does work but is not well-tested, and
numpy, and scipy are ported to Python 3.X.  The graphical system, based on
wxWidgets has not yet been ported to Python 3.X.

In addition, numpy, matplotlib, and wxPython are required.  These are
simply installed as standard packages on almost all platforms.

.. _larch github repository:   http://github.com/xraypy/xralarch

All development is done through the `larch github repository`_.  To get a
read-only copy of the atest version, use::

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


