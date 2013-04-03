====================================
Downloading and Installation
====================================

.. _larch-0.9.19.tar.gz (sf.net): http://sourceforge.net/projects/xraylarch/files/larch-0.9/larch-0.9.19.tar.gz/download
.. _larch-0.9.19.tar.gz (CARS):   http://cars.uchicago.edu/xraylarch/downloads/larch-0.9.19.tar.gz

.. _LarchInstaller_0.9.19.exe (sf.net): http://sourceforge.net/projects/xraylarch/files/larch-0.9/LarchInstaller_0.9.19.exe/download
.. _LarchInstaller_0.9.19.exe (CARS):   http://cars.uchicago.edu/xraylarch/downloads/LarchInstaller_0.9.19.exe
.. _larch github repository:      http://github.com/xraypy/xraylarch


Larch is still in active development, and all releases should be considered
**beta** releases.  That is, these **beta** releases are working, but have
not been rigorously or extensively tested, and probably contain some bugs
and unintended features.

Downloads are available from the  
`xraylarch project <http://sourceforge.net/projects/xraylarch>`_  
at sourceforge.net or from 
`CARS.uchicago.edu <http://cars.uchicago.edu/xraylarch>`_  
Recommended download options are:

  +---------+-----------------+-----------+-------------------------------------------------------+
  | Status  | Download Type   | Platforms |   Download / Command                                  |
  +=========+=================+===========+=======================================================+
  | Beta    | Source tarball  | All       |  `larch-0.9.19.tar.gz (CARS)`_  or                    |
  |         |                 |           |  `larch-0.9.19.tar.gz (sf.net)`_                      |
  +---------+-----------------+-----------+-------------------------------------------------------+
  | Beta    | Win32 Installer | Windows   |  `LarchInstaller_0.9.19.exe (CARS)`_  or              |
  |         |                 |           |  `LarchInstaller_0.9.19.exe (sf.net)`_                |
  +---------+-----------------+-----------+-------------------------------------------------------+
  | Devel   | Source kit      | All       | git clone http://github.com/xraypy/xraylarch.git      |
  +---------+-----------------+-----------+-------------------------------------------------------+


Binary Installation (Windows)
================================

The binary Windows installer provides working executables for the Larch
command-line program and primitive Larch GUI onto your system.  To date,
testing of this GUI has been fairly minimal.  If you try this out, please
send positive and negative feedback to the Ifeffit mailing list.


Source Installation
=========================

Installation from Source is necessary for Linux and Mac OS X, and is
recommended for people interested in programming with Larch on Windows.


Prerequisites
~~~~~~~~~~~~~~~

Larch requires Python version 2.6.4 or higher.  Support for Python 3.X is partial, in
that the core of Larch does work, and numpy, and scipy, and matplotlib have all been
ported to Python 3.X.  But the testing for Python 3.X has been minimal, and the
graphical interfaces, based on wxWidgets, has not yet been ported to Python 3.X.

Numpy, scipy, matplotlib, and wxPython are all required for Larch.  These are best
installed as standard packages on almost all platforms.

You can either download the tarball above, or use the development version from the
`larch github repository`_.  To get a read-only copy of the latest version, use::

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


.. literalinclude:: ../../COPYING
