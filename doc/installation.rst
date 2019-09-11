.. _install-chapter:

====================================
Downloading and Installation
====================================


.. _Larch Repository (github.com): https://github.com/xraypy/xraylarch
.. _Anaconda Python:               https://www.continuum.io/
.. _Anaconda Downloads:            https://www.continuum.io/downloads
.. _Miniconda Downloads:           https://docs.conda.io/en/latest/miniconda.html
.. _lmfit:                         https://lmfit.github.io/lmfit-py/
.. _Larch Releases (github.com):   https://github.com/xraypy/xraylarch/releases
.. _Larch Binary Installers:       https://millenia.cars.aps.anl.gov/xraylarch/downloads
.. _source code (tar.gz):          https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.45.tar.gz
.. _Larch for 64bit Windows:       https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.45-Windows-x86_64.exe
.. _Larch for MacOSX:              https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.45-MacOSX-x86_64.pkg
.. _Larch for Linux:               https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.45-Linux-x86_64.sh
.. _Larch Docs and Examples:       https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.45-docs-examples.zip

The latest release version of Larch is |release|.

Larch is in active and continuing development, and the intention is to tag a
new release version every three to six months.  Larch's tools for XAFS data
analysis and working with XRF data and XRF maps from X-ray microprobes are
working and ready for general use.  There may be bugs and unintended features,
and some missing or incomplete desired features as we add new functionality.


Single-File Installers
=========================

For Windows, MacOSX, and Linux, Larch provides simple installers, available
at `Larch Binary Installers`_.  These are self-contained files that will
install a complete Python environment from Anaconda Python and all of
libraries needed by X-ray Larch..  Installing Larch this way will be create
a folder in your home folder called `xraylarch` (by default: you can change
it).  On Linux and MacOSX, this folder will be in the top-level of your
home directory, while on Windows this folder will typically be in
`C:\Users\YourName\AppData\Local\Continuum\xraylarch`.  These installers
will also create a folder called `Larch` on your desktop that contains
links (or shortcuts or Apps) to many of the Larch GUI applications listed
above in :ref:`Table of Larch Applications and Programs <larch_app_table>`.
This includes tools for X-ray Absorption spectroscopy, X-ray fluorescence
spectroscopy, and working with X-ray diffraction images.

.. note::

   There can be no spaces in your username or the path in which Larch is installed.

Generally, installing Larch only writes to files owned by the user account and
does not require administrative privilege.  It will not interfere with
anything else on your system (like, say, system Python).  You you can
uninstall simply by removing `xraylarch` folder.  The installers are fairly
large (400 to 600 Mb), but includes an entire scientific python environment.
Installing by the other means described below will not actually take less disk
space, but will involve downloading many more smaller files, which may be an
advantage for some people with poor connectivity.

.. _installers_table:

**Table of Larch Installers**

  +-------------------------+-------------------------------------+
  | Operating System        |   installer                         |
  +=========================+=====================================+
  | Windows (64 bit)        | `Larch for 64bit Windows`_          |
  +-------------------------+-------------------------------------+
  | Mac OSX (64 bit)        | `Larch for MacOSX`_                 |
  +-------------------------+-------------------------------------+
  | Linux (64 bit)          | `Larch for Linux`_                  |
  +-------------------------+-------------------------------------+
  | Source Code             | `source code (tar.gz)`_             |
  +-------------------------+-------------------------------------+
  | Docs and Examples       | `Larch Docs and Examples`_          |
  | (all systems)           |                                     |
  +-------------------------+-------------------------------------+

If you need a versions for 32-bit Windows or Linux, contact the authors.

For Windows, download the executable installer::

    xraylarch-0.9.45-Windows-x86_64.exe

and double-click to run it to install Larch

For Mac OSX, download the package installer::


    xraylarch-0.9.45-MacOSX-x86_64.pkg

and double-click to run it to install Larch.

For Linux, download the shell installer file, then open a Terminal, use
`cd` to move to the download folder (typically `Downloads`) and run::

    bash xraylarch-0.9.45-Linux-x86_64.sh


You will be able to completely uninstall simply by removing the
`xraylarch` folder in your home directory.    Note that for Windows, The
`xraylarch` folder is not typically put in your path, and so you would need
to open a Command or Powershell window and do::

   C:\Users\YourName\AppData\Continuum\xraylarch\Scripts\conda.exe -yc GSECARS xraylarch


Once installed, you may be able to upgrade to future versions of Larch using::

    conda update -yc GSECARS xraylarch

.. note::
   `conda update --all` *will not* work to upgrade from 0.9.42 to 0.9.45,
   but it *will* work to upgrade from 0.9.43 or 0.9.44 to 0.9.45.



Installing with Anaconda Python
======================================

For those familiar with Python, Larch can be installed into an existing
Python environment.  We highly recommended using `Anaconda Python`_ for
Larch.  While Larch can be installed from source code with standard
versions of Python, Anaconda Python makes getting and installing the many
packages needed for Larch.

`Anaconda Python`_ provides a free and well-supported version of Python for
scientific work with many useful packages included.  By default, Anaconda
Python installs into your own home folder (on Windows, this will be the
`APPDATA` location, which is typically something like
`C:\\Users\\YourName\\AppData\\Local\\Continuum\\Anaconda3`).  As with the
single-file installers above, installing Anaconda Python does not require
extra permissions to install, upgrade, or remove components.  Anaconda
includes a robust package manager called *conda* that makes it easy to
update the packages it manages, including Larch.

Start by installing the latest version of Anaconda Python from the `Anaconda
Downloads`_ site.  Python 3.7 is recommended.  Larch should work with Python
3.6, may work with Python 3.5, but will no longer work with Python 2.7.  You
can also download and install Miniconda from `Miniconda Downloads` as a
starting distribution.

Once Anaconda or Miniconda Python is installed, you can open a Terminal (on
Linux or Mac OSX) or the Anaconda prompt (on Windows) and type::

    conda install -yc GSECARS xraylarch

to install Larch.

To make a `Larch` folder on your desktop with shortcuts (Windows or Linux) or
Applications (MacOS) for the main Larch applications, you can then type::

    larch -m

If that complains that it does not find `larch`, you may have to explicitly
give the path to Python and/or Larch::

   $HOME/xraylarch/bin/larch -m

from Linux or MacOSX or::

   %APPDATA%\\Continuuum\xraylarch\Scripts\larch.exe -m

from Windows.


Anaconda Python makes some updates very easy for us to provide and for you to
install.  As new releases of Larch and the required packages are released, you
may be able to upgrade to the latest versions with::

   conda update --all

This approach to updating will not work for all new versions of Larch,
depending on which underlying libraries are used.

.. note::
   `conda update --all` will *not* work to upgrade from 0.9.42 to 0.9.43.


Python Versions:
============================================

As of this writing (April, 2019) there are three main supported versions of
Python: Version 3.7, Version 3.6, and Version 2.7.  Support for Python 2.7
will be ending within a year, and we have moved Larch to be compatible with
Python 3 only.  The installers above use Python 3.7.  Most of the dependencies
and tools will work with Python 3.6, and perhaps even with Python 3.5, though
we are no longer testing with Python 3.5.



Source Installation
=========================

For Python-savvy users, Larch can be installed from source. You can use either
the `source code (tar.gz)`_ or from `Larch releases (github.com)`_.  In
addition, you can use `git` to grab the latest development version of the
source code::

   git clone http://github.com/xraypy/xraylarch.git


With the source kit unpacked using `tar` or `zip`, you should be able to
install Larch using `python setup.py install`.  This should automatically use
`pip` to install any required dependencies as well as Larch itself.  Depending
on your platform and version of Python, you may need elevated permissions as
from `sudo` to install Larch to a system folder.

There are several required packages and a few "highly recommended" packages
for Larch.  These are listed in the next section.


Prerequisites
~~~~~~~~~~~~~~~~~~~

Larch requires Python version 3.6 or higher. In addiion, many Python
packages are required for Larch to work.  These are listed in the table
below.


.. _dependencies_table:

**Table of Larch Dependencies** This lists the packages that are either
required for Larch or required for some portion of Larch functionality to
work. The required packages and several of the recommended packages will
normally be installed by default or are easily available from with `conda` or
`pip`.

  +----------------+-------------+-----------------------------+
  | Package name   | min version | status, notes               |
  +================+=============+=============================+
  | python         | 3.6         | required                    |
  +----------------+-------------+-----------------------------+
  | numpy          | 1.15        | required                    |
  +----------------+-------------+-----------------------------+
  | scipy          | 1.1         | required                    |
  +----------------+-------------+-----------------------------+
  | six            | 1.10        | required                    |
  +----------------+-------------+-----------------------------+
  | matplotlib     | 3.0         | required                    |
  +----------------+-------------+-----------------------------+
  | sqlalchemy     | 0.9         | required                    |
  +----------------+-------------+-----------------------------+
  | h5py           | 2.8         | required                    |
  +----------------+-------------+-----------------------------+
  | scikit-learn   | 0.18        | required                    |
  +----------------+-------------+-----------------------------+
  | pillow         | 3.4         | required                    |
  +----------------+-------------+-----------------------------+
  | peakutils      | 1.3.0       | required                    |
  +----------------+-------------+-----------------------------+
  | requests       | 2.1         | required                    |
  +----------------+-------------+-----------------------------+
  | asteval        | 0.9.13      | required                    |
  +----------------+-------------+-----------------------------+
  | lmfit          | 0.9.13      | required                    |
  +----------------+-------------+-----------------------------+
  | uncertainties  | 3.0.3       | required                    |
  +----------------+-------------+-----------------------------+
  | pyyaml         |             | required                    |
  +----------------+-------------+-----------------------------+
  | psutil         |             | required                    |
  +----------------+-------------+-----------------------------+
  | termcolor      |             | required                    |
  +----------------+-------------+-----------------------------+
  | wxpython       | 4.0.3       | required for GUIs, plotting |
  +----------------+-------------+-----------------------------+
  | wxmplot        | 0.9.34      | required for plotting       |
  +----------------+-------------+-----------------------------+
  | wxutils        | 0.2.3       | required for GUIs           |
  +----------------+-------------+-----------------------------+
  | scikit-image   |             | needed for tomography maps  |
  +----------------+-------------+-----------------------------+
  | tomopy         | 1.3.0       | recommended for tomography  |
  +----------------+-------------+-----------------------------+
  | silx           | 0.9.0       | needed to read Spec files   |
  +----------------+-------------+-----------------------------+
  | pyFAI          |             | needed for XRD              |
  +----------------+-------------+-----------------------------+
  | fabio          | 0.9.0       | needed for XRD              |
  +----------------+-------------+-----------------------------+
  | PyCifRW        | 4.3         | needed for XRD              |
  +----------------+-------------+-----------------------------+
  | pyepics        | 3.3.3       | needed for using Epics      |
  +----------------+-------------+-----------------------------+

All of these modules are available from PyPI (the Python Package Index),
and for Anaconda Python 3.7 and 3.6.  The packages not included with core
Anaconda packages are available on the GSECARS conda channel, and will be
installed with `conda install -c GSECARS xraylarch`.  If you're installing
from source or using a Python distribution other than Anaconda, all these
packages are also available from PyPI and can be installed with `pip
install <packagename>` or `conda install -c GSECARS <packagename>`.

Optional Modules
~~~~~~~~~~~~~~~~~~~~~~~~~~

There are a few packages that are required only for some more specialized
uses of Larch that may not be important for everyone using Larch. For
example, the advanced and in-development X-ray diffraction analysis
capabilities require the following packages:

   fabio, pyFAI, PyCifRw

Some x-ray computed tomography capabilities are available, and require the
packages:

   tomopy, scikit-image

These are generally supported and available with Python 3.6, and are
included with the binary installers above, or on the GSECARS anaconda.org
channel.

Some Epics-based data collection tools use Larch and require:

   pyepics, psycopg2, epicsscan

As with the other packages listed above, these are either available from the
GSECARS anaconda channel or from PyPI.

To be clear, most of Larch will work fine without these modules installed,
but the corresponding functionality will not be available.

Installation from Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If installing from source, first unpack the source distribution kit, move
into the created xraylarch-VERSION directory, and type::

    python setup.py install




Documentation and Examples
================================

The source kit includes sources for documentation in the `docs` folder
and several examples (including all those shown in this documentation)
in the `examples` folder.  These are also available separately at
`Larch Docs and Examples`_.


Citing Larch
========================

Currently, the best citation for Larch is M. Newville, *Larch: An Analysis
Package For XAFS And Related Spectroscopies*. Journal of Physics:
Conference Series, 430:012007 (2013).  :cite:`larch2013`


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
<newville@cars.uchicago.edu>.  Bruce Ravel has an incalculable influence on
the design and implementation of this code and has provided countless fixes
for serious problems in design and execution in the early stages.  More
importantly, Larch would simply not exist without the long and fruitful
collaboration we've enjoyed.  Margaret Koker wrote most of the X-ray
diffraction analysis code, and much of the advanced functionality of the
GSECARS XRF Map Viewer.  Mauro Rovezzi has provided the spec-data reading
interface.  Tom Trainor had a very strong influence on the original design
of Larch, and helped with the initial version of the python implementation.
Yong Choi wrote the code for X-ray standing wave and reflectivity analysis
and graciously allowed it to be included and modified for Larch.  Tony
Lanzirotti and Steve Sutton have provided wonderful and patient feedback on
many parts of Larch, espcially for XANES processing and testing of the XAS
Viewer GUI.

Because Larch began as a rewrite of the Ifeffit XAFS Analysis Package, it
also references and builds on quite a bit of code developed for XAFS over
many years at the University of Chicago and the University of Washington.
The existence of the code and a great deal of its initial design therefore
owes a great thanks to Edward Stern, Yizhak Yacoby, Peter Livens, Steve
Zabinsky, and John Rehr.  More specifically, code written by Steve Zabinsky
and John Rehr for the manipulation of results from FEFF and for the
calculation of thermal disorder parameters for XAFS are included in Larch
with little modification.  Both Feff6l and Feff8l, the product of many man
years of effort by the Feff group led by John Rehr, are included in Larch.
A great many people have provided excellent bug reports, feedback, in depth
conversations, and suggestions for making Ifeffit better, including on the
ifeffit mailing list.  Many of these contributions have found their way
into Larch.

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
particular, Larch uses the `lmfit`_ library, which began as part of Larch
but was spun off into a standalone, general purpose fitting library that
became useful for application areas other than XAFS, and has benefited
greatly from numerous collaborators and added many features that Larch, in
turn, has been able to depend on.


License
============

Except where explicitly noted in the individual files, the code,
documentation, and all material associated with Larch are distributed under
the BSD License:


.. literalinclude:: ../LICENSE
