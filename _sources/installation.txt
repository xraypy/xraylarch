====================================
Downloading and Installation
====================================

.. _larch-0.9.17.tgz (github):  http://xraypy.github.com/xraylarch/downloads/larch-0.9.17.tgz
.. _larch-0.9.17.exe (github):  http://xraypy.github.com/xraylarch/downloads/larch-0.9.17.exe
.. _larch-0.9.17.tgz (CARS):    http://cars.uchicago.edu/xraylarch/downloads/larch-0.9.17.tgz
.. _larch-0.9.17.exe (CARS):    http://cars.uchicago.edu/xraylarch/downloads/larch-0.9.17.exe
.. _larch github repository:    http://github.com/xraypy/xraylarch


Downloads
================

+-----------------+------------+----------------------------------------------+
|  Download Type  | Platformsn |   Location                                   |
+=================+============+==============================================+
| Source tarball  | All        |  `larch-0.9.17.tgz (CARS)`_  or              |
|                 |            |  `larch-0.9.17.tgz (github)`_                |
+-----------------+------------+----------------------------------------------+
| Win32 Installer | Windows    |  `larch-0.9.17.exe (CARS)`_  or              |
|                 |            |  `larch-0.9.17.exe (github)`_                |
+-----------------+------------+----------------------------------------------+
|  Development    | All        |  `larch github repository`_                  |
+-----------------+------------+----------------------------------------------+

Binary Installation (Windows)
==================================

The binary installer for Windows installs a working version of the larch
command-line program and primitive Larch GUI onto your system.  To date,
testing has been fairly minimal.  If you try this out, please send positive
and negative feedback to the Ifeffit mailing list.


Source Installation
=========================

Installation from Source is necessary for Linux and Mac OS X, and is
recommended for people interested in programming with Larch on Windows.


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


You can either download the tarball above, or use the development version
from the `larch github repository`_.  To get a read-only copy of the latest
version, use::

   git clone http://github.com/xraypy/xraylarch.git


Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Installation from source on any platform is::

   tar xvzf larch-0.9.XX.tgz
   cd larch-0.9.XX/
   python setup.py install

License
============

Except where explicitly noted in the indivdidal files, the code,
documentation, and all material associated with Larch are distributed under
the BSD License:


.. literalinclude:: ../COPYING
