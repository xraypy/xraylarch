====================================
Downloading and Installation
====================================

.. _Larch Repository (github.com): http://github.com/xraypy/xraylarch
.. _Anaconda Python:               http://www.continuum.io/
.. _Anaconda Downloads:            http://www.continuum.io/downloads
.. _Larch Releases (github.com):   https://github.com/xraypy/xraylarch/releases
.. _Larch Installers (cars.uchicago.edu): http://cars.uchicago.edu/xraylarch/downloads
.. _Larch for 64bit Windows:  http://cars.uchicago.edu/xraylarch/downloads/xraylarch-0.9.35-Windows-x86_64.exe
.. _Larch for 32bit Windows:  http://cars.uchicago.edu/xraylarch/downloads/xraylarch-0.9.35-Windows-x86.exe
.. _Larch for Mac OSX :       http://cars.uchicago.edu/xraylarch/downloads/xraylarch-0.9.35-MacOSX-x86_64.sh
.. _Larch for Linux:          http://cars.uchicago.edu/xraylarch/downloads/xraylarch-0.9.35-Linux-x86_64.sh


The latest release version of Larch is |release|.  Larch is in active and
continuing development, and the intention is to tag a new release version every
three to six months.  Of course, there may be bugs and unintended features, and
some missing or incomplete desired features as we add new functionality.  Still,
most of what is in Larch for XAFS data analysis and working with XRF maps from
X-ray microprobes is working and ready for use.






Single-File Installers
=========================

For Windows, Mac OSX, and Linux, Larch now comes with simple installers,
available at `Larch Installers (cars.uchicago.edu)`_.  These are
self-contained files that will install a complete Python environment from
Anaconda Python and all of X-rayLarch onto your computer.  Installing Larch
this way will be create a folder in your home folder called `xraylarch` by
default (you can change it).  This does not require administrative
privilege and will not interfere with anything on your system -- you can
uninstall simply by removing this folder.  The installers are fairly large
(300 to 500 Mb), but includes an entire scientific python environment.
Installing by the other means described below will not take less disk
space.

.. _installers_table:

**Table of Larch Installers**

  +----------------------+----------------------------------------+
  | Operating System     |   installer                            |
  +======================+========================================+
  | Windows (64bit)      | `Larch for 64bit Windows`_             |
  +----------------------+----------------------------------------+
  | Windows (32bit)      | `Larch for 32bit Windows`_             |
  +----------------------+----------------------------------------+
  | Mac OSX (64bit)      | `Larch for Mac OSX`_                   |
  +----------------------+----------------------------------------+
  | Linux (64bit)        | `Larch for Linux`_                     |
  +----------------------+----------------------------------------+

For Windows, download the appropriate executable installer corresponding to
the architecture of your OS, and run it.  Most modern computers (including
Windows 10) will be running 64-bit Windows, but a 32-bit version is
provided for older systems.

For Mac OSX or Linux, download the appropriate file then open a Terminal
(Applications->Utilities->Terminal on Mac OSX), use `cd` to move to the
download folder (typically `cd Downloads`) and run::

    bash xraylarch-0.9.35-MacOSX-x86_64.sh

or::

    bash xraylarch-0.9.35-Linux-x86_64.sh

Once installed, you will be able to upgrade to future versions of Larch using::

    conda update xraylarch

and you will be able to completely uninstall simply by removing the
`xraylarch` folder in your home directory.

On Windows and Mac OSX, the installer will create a *Larch* folder on your
Desktop containing links to many of the Larch GUI applications listed above in
:ref:`Table of Larch Applications and Programs <larch_app_table>`.

A key advantage of using Anaconda is that once installed, updates can be
installed with::

    conda update -yc GSECARS xraylarch

As of this writing, some functionality -- notably X-ray diffraction -- may
need additional libraries installed, and some of these libraries may not be
available for Python3.6 or for all platforms.   We're working on this, but
if you need help, please contact us.


Installing with Anaconda Python
======================================

For those familiar with Python, Larch can be installed into an existing
Python environment.  We highly recommended using `Anaconda Python`_ for
Larch.  While Larch can be installed from source code with standard
versions of Python, Anaconda Python makes getting and installing the many
packages needed for Larch.

`Anaconda Python`_ provides a free and well-supported version of Python for
scientific work with many useful packages included.  By default, Anaconda Python
installs into your own home folder (on Windows, this will be the `APPDATA`
location, which is typically something like
`C:\\Users\\YourName\\AppData\\Local\\Continuum\\Anaconda2`).  As with the
single-file installers above, installing Anaconda Python does not require extra
permissions to install, upgrade, or remove components.  Anaconda includes a
robust package manager called *conda* that makes it easy to update the packages
it manages, including Larch.

Begin by installing the latest version of Anaconda Python -- either Python 2.7
or 3.6 should work (though Python 3.6 may have undiscovered bugs) from the
`Anaconda Downloads`_ site.  Once that is installed, you can open a Terminal (on
Linux or Mac OSX) or the Anaconda prompt (on Windows) and type::

    conda install -yc GSECARS xraylarch

to install Larch.  On Windows or Mac OSX, then type::

    larch_makeicons

to make a `Larch` folder on your desktop with shortcuts (Windows) or
Applications (Mac OSX) for the main Larch applications.


Python Versions: 2.7 or 3.6?
================================

As of this writing (October, 2017) there are two main supported versions of
Python: Version 2.7 and Version 3.6.  Larch works with both versions of Python.
We invite Python-savvy users to try out Larch with Python 3.6, but warn that
there may be undiscovered bugs.  We are eager to migrate Larch so that it works
only with Python 3.6 and higher so that we can take advantage of many language
features not available in earlier versions.  Following the schedule of many
scientific Python libraries and tools, we expect to make this transition in
early 2019.

Source Installation
=========================

For Python-savvy users, Larch can be installed from source code.  The latest
releases of the source code will be available from `Larch releases
(github.com)`_.  In addition, you can use `git` to grab the latest development
version of the source code::

   git clone http://github.com/xraypy/xraylarch.git


Prerequisites
~~~~~~~~~~~~~~~~~~~

Larch requires Python version 2.7 or 3.6. In addiion, the following Python
packages are all required for Larch to work:

    numpy, scipy, matplotlib, h5py, sqlalchemy, six, lmfit, wxPython,
    wxmplot, wxutils, asteval.

These are all widely available, either from PyPI or for Anaconda Python 2.7 and
3.6.  Those packages not included with core Anaconda packages can be installed
from the GSECARS conda channel, and will be installed with `conda install -c
GSECARS xraylarch`.  If you're installing from source or using a Python
distribution other than Anaconda, all these packages are also available from
PyPI and can be installed with `pip install`

There are a few packages that are required for some of the advanced and
in-development X-ray diffraction analysis capabilities.  These include

   fabio, pyfai, pycifrw

As with the other packages listed above, these are either available from the
GSECARS anaconda channel or from PyPI.


Installation from Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If installing from source, first unpack the source distribution kit, move
into the created xraylarch-VERSION directory, and type::

    python setup.py install


Documentation and Examples
================================

The source kit includes sources for documentation in the `docs` folder and
several examples (including all those shown in this documentation) in the
`examples` folder.


Funding and Support
=======================

Larch development at the GeoScoilEnviroCARS sector of Center for Advanced
Radiation Sources at the University of Chicago has been supported by the US
National Science Foundation - Earth Sciences (EAR-1128799), and Department
of Energy GeoSciences (DE-FG02-94ER14466).  In addition, funding
specifically for Larch was granted by the National Science Foundation -
Advanced CyberInfrastructure (ACI-1450468).


Acknowledgements
==================

Larch was mostly written by and is maintained by Matt Newville
<newville@cars.uchicago.edu>.  Bruce Ravel has had an incalculable influence on
the design and implementation of this code and has provided countless fixes for
serious problems in design and execution in the early stages.  More than that,
Larch would simply not exist without the long and fruitful collaboration we've
enjoyed.  Margaret Koker wrote most of the X-ray diffraction analysis code, and
much of the advanced functionality of the GSECARS XRF Map Viewer.  Tom Trainor
had a very strong influence on the original design of Larch, and helped with the
initial version of the python implementation.  Yong Choi wrote the code for
X-ray standing wave and reflectivity analysis and graciously allowed it to be
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


.. literalinclude:: ../LICENSE
