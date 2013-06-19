====================================
Downloading and Installation
====================================

.. _larch-0.9.20.tar.gz (sf.net):    http://sourceforge.net/projects/xraylarch/files/larch-0.9/larch-0.9.20.tar.gz/download
.. _larch-0.9.20.tar.gz (CARS):      http://cars.uchicago.edu/xraylarch/downloads/larch-0.9.20.tar.gz

.. _LarchInstaller_0.9.20.exe (sf.net): http://sourceforge.net/projects/xraylarch/files/larch-0.9/LarchInstaller_0.9.20.exe/download
.. _LarchInstaller_0.9.20.exe (CARS):   http://cars.uchicago.edu/xraylarch/downloads/LarchInstaller_0.9.20.exe
.. _larch github repository:            http://github.com/xraypy/xraylarch


Larch is still in active development, and all releases should be considered
**beta** releases.  That is, these **beta** releases are working, but have
not been rigorously or extensively tested, and probably contain some bugs
and unintended features.

Downloads are available from the
`xraylarch project <http://sourceforge.net/projects/xraylarch>`_
at sourceforge.net or from
`cars.uchicago.edu <http://cars.uchicago.edu/xraylarch>`_
Recommended download options are:

  +---------+-----------------+-----------+-------------------------------------------------------+
  | Status  | Download Type   | Platforms |   Download / Command                                  |
  +=========+=================+===========+=======================================================+
  | Beta    | Source tarball  | All       |  `larch-0.9.20.tar.gz (CARS)`_  or                    |
  |         |                 |           |  `larch-0.9.20.tar.gz (sf.net)`_                      |
  +---------+-----------------+-----------+-------------------------------------------------------+
  | Beta    | Win32 Installer | Windows   |  `LarchInstaller_0.9.20.exe (CARS)`_  or              |
  |         |                 |           |  `LarchInstaller_0.9.20.exe (sf.net)`_                |
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


Acknowledgements
==================

Larch was mostly written by and is maintained by Matt Newville
<newville@cars.uchicago.edu>.  Bruce Ravel has had an incalculable
influence on the design and implementation of this code and has provided
countless fixes for serious problems in design and execution in the early
stages.  More than that, Larch would simply not exist without the long and
fruitful collaboration we've enjoyed.  Tom Trainor had a very strong
influence on the original design of Larch, and helped with the initial
version of the python implementation.  Yong Choi wrote the code for X-ray
standing wave and reflectivity analysis and graciously allowed it to be
included and modified for Larch.

Having begun as a rewrite of the Ifeffit XAFS Analysis Package, Larch also
references and builds on quite a bit of code developed for XAFS over many
years at the University of Chicago and the University of Washington.  The
existence of the code and a great deal of its initial design therefore owes
a great thanks to Edward Stern, Yizhak Yacoby, Peter Livens, Steve
Zabinsky, and John Rehr.  More specifically, code written by Steve Zabinsky
and John Rehr for the manipulation of results from FEFF and for the
calculation of thermal disorder parameters for XAFS are included in Larch
with little modification.  A great many people have provided excellent bug
reports, feedback, in depth conversations, and suggestions for making
Ifeffit better, including on the ifeffit mailing list.  Many of these
contributions have found their way into Larch.

Larch includes calculations for anomalous cross-sections based on the work
of Cromer and Libermann, as implemented by Sean Brennan and Paul L. Cowen.
Their code is included in Larch with only minor changes.  Code to store and
read the X-ray Scattering data from the Elam Tables was modified from code
originally written by Darren S. Dale.  Refined values for anomalous
scattering factors have been provided directly by Christopher T. Chantler.
Further details of the origin of much of the tabularized X-ray data is
given in :ref:`xraydb-chapter`.

As Larch depends on the fantastic scientific librarie written and
maintained in python, especially the numpy, scipy, and matplotlib, the
entire scientific python community deserves a hearty thanks.  In
particular, Larch includes code from Jonathan J. Helmus to implement robust
setting of Parameter bounds as described in the MINUIT User's guide.  Till
Stensitzki wrote the code for improved, brute-force estimates of confidence
intervals, and Christopher Deil provided many valuable suggestions for
improving the parameterized fitting used in Larch.  Eric O. Lebigot's
uncertainty package for automated calculation and propagation of
uncertainties is also included in Larch, with slight modification.


License
============

Except where explicitly noted in the individual files, the code,
documentation, and all material associated with Larch are distributed under
the BSD License:


.. literalinclude:: ../../COPYING
