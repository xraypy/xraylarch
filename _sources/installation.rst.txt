.. _install-chapter:

====================================
Downloading and Installation
====================================


.. _Larch Repository (github.com): https://github.com/xraypy/xraylarch
.. _Anaconda Python:               https://www.continuum.io/
.. _Python.org:                    https://python.org/
.. _Anaconda Downloads:            https://www.continuum.io/downloads
.. _Miniconda Downloads:           https://docs.conda.io/en/latest/miniconda.html
.. _lmfit:                         https://lmfit.github.io/lmfit-py/
.. _Larch Releases (github.com):   https://github.com/xraypy/xraylarch/releases
.. _Larch Binary Installers:       https://millenia.cars.aps.anl.gov/xraylarch/downloads
.. _source code (tar.gz):          https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.47.tar.gz
.. _Larch for Windows:             https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.47-Windows-x86_64.exe
.. _Larch for MacOSX:              https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.47-MacOSX-x86_64.pkg
.. _Larch for Linux:               https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.47-Linux-x86_64.sh
.. _Larch Docs and Examples:       https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-0.9.47_docs-examples.zip


.. _Ifeffit Mailing List: https://millenia.cars.aps.anl.gov/mailman/listinfo/ifeffit/
.. _Demeter: https://bruceravel.github.io/demeter/
.. _Larch Github Pages: https://github.com/xraypy/xraylarch

The latest release version of Larch is |release|.

Larch is in active and continuing development. The goal is to release a new
version every few months, but without specific timelines.  Larch's tools
for XAFS data analysis and working with XRF data and XRF maps from X-ray
microprobes are working and ready for general use.  There may be bugs and
unintended features, and some missing or incomplete desired features as we
add new functionality.  Your feedback, bug reports, and patience are greatly
appreciated.


Single-File Installers and Source Installation Files
==========================================================

.. _installers_table:

**Table of Larch Installers and Downloads**

  +----------------------+------------------------------+-----------------------------+
  | Operating System     |   Installer File             | Installation Notes          |
  +======================+==============================+=============================+
  | Windows (64 bit)     | `Larch for Windows`_         | :ref:`Notes <install-win>`  |
  +----------------------+------------------------------+-----------------------------+
  | Mac OSX (64 bit)     | `Larch for MacOSX`_          | :ref:`Notes <install-mac>`  |
  +----------------------+------------------------------+-----------------------------+
  | Linux (64 bit)       | `Larch for Linux`_           | :ref:`Notes <install-lin>`  |
  +----------------------+------------------------------+-----------------------------+
  | Source Code          | `source code (tar.gz)`_      | :ref:`Notes <install-src>`  |
  +----------------------+------------------------------+-----------------------------+
  | Docs and Examples    | `Larch Docs and Examples`_   | :ref:`Notes <install-exa>`  |
  | (all systems)        |                              |                             |
  +----------------------+------------------------------+-----------------------------+

Installers for Windows, MacOSX, and Linux, are available at `Larch Binary
Installers`_.  These are fairly large (400 to 600 Mb files) self-contained
files that will install a complete Anaconda Python environment with all of
libraries needed by Larch.  Normally, this installation will be create a folder
called `xraylarch` in your home folder -- see platform-specific notes below.

.. note::

   There can be no spaces in your username or the path in which Larch is installed.

Installing with these installers should write to files only to folders
owned by the user account. It should not require administrative privilege and
should not interfere with any thing else on your system (such as system
Python).

These installers will also create a folder called `Larch` on your desktop
that contains links (or shortcuts or Apps) to many of the Larch GUI
applications listed in :ref:`Table of Larch Applications and Programs
<larch_app_table>`.  This includes tools for X-ray Absorption spectroscopy,
X-ray fluorescence spectroscopy, and working with X-ray diffraction images.


.. _install-win:

Windows Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For Windows, download the `Larch for Windows`_ installer above and run it to install Larch.  This
will be installed to ``C:\Users\<YourName>\xraylarch`` for most individual Windows installations or
to ``C:\Users\<YourName>\AppData\Local\Continuum\xraylarch`` if your machine is part of a Windows
Workgroup or Domain.

.. note::

   If you get prompted for an administrative password during the installation process, you
   should make sure you are installing to a folder that is writable by the user.

.. _install-mac:

MacOS Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


For Mac OS, download the `Larch for MacOSX`_ installer above and click it to install Larch.  There
are two important notes:

.. note::

   With MacOS 10.15 (Catalina), Apple will not install non-signed 3rd party packages by default.
   You may need to go into General Settings part of the **Security & Privacy** section of **System
   Preferences** and explicitly allow this package to be installed. You probably will be prompted for
   an Administrative password.

.. note::

   You need to explicitly click on "Install only for me" during the installation process.  If you
   get prompted for an Administrative password by the installer, go back and explicitly choose
   "Install only for me".


.. _install-lin:

Linux Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For Linux, download the `Larch for Linux`_ shell installer file, then open a Terminal, use `cd` to
move to the download folder (typically `$HOME/Downloads`) and run::

    ~> bash ./xraylarch-0.9.47-Linux-x86_64.sh

Desktop shortcuts as ``.desktop`` files will be created on all Linux platforms, but whether these
actually appear on your desktop depends on the Windowing system used:  they will appear on the
desktop with KDE and many other systems, but not with Gnome.  Clickable icons should also show up
in the Applications selection of the "Start Menu" or Applications list.


.. _install-src:

Install with Python
======================================

For those familiar with Python, Larch can be installed into an existing Python environment.  Larch
requires Python 3.6 or higher.

If you are starting out with Python and interested in Larch, using
`Anaconda Python`_ for Larch is a good option as Anaconda provides and
maintains a free Python distribution than contains many of the scientific
Python packages needed for Larch.

You can also install Larch in other Python environments.

Using Anaconda Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, Anaconda Python installs into your own home folder (on Windows, this will be the
`APPDATA` location, which is typically something like ``C:\\Users\<YourName>\Anaconda3`` or
``C:\\Users\<YourName>\AppData\Local\Continuum\Anaconda3``).  As with the single-file installers
above, installing Anaconda Python does not require extra permissions to install, upgrade, or remove
components.  Anaconda includes a robust package manager called *conda* that makes it easy to update
the packages it manages, including Larch.

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

   %APPDATA%\\Local\\Continuum\xraylarch\Scripts\larch.exe -m

from Windows.

Updating with `conda`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Anaconda Python makes updates very easy for us to provide and for you to
install.  As new releases of Larch and the required packages are released,
you may be able to upgrade to the latest versions with::

   conda update --all

This approach to updating will not work for all new versions of Larch,
depending on which underlying libraries are used.

Note that for Windows, The `xraylarch` folder is not typically put in your
path, and so you would need to open a Command or Powershell window and type::

   C:\Users\<YourName>\xraylarch\Scripts\conda.exe update --all

.. note::
   `conda update --all` *will not* work to upgrade from 0.9.42 to 0.9.47,
   but it *will* work to upgrade from 0.9.43 or higher to 0.9.47.



Using `pip`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starting with Larch version 0.9.46, Larch can be used with Python versions
from `Python.org`_.  That is, you can install one of the installers there,
and install (most of) Larch simply with::

    pip install xraylarch

This will install Larch and all of the required packages. Some of the
"recommended" packages listed below may not be installed and you may have
to forgo thes capabilities or install those packages by hand.


Source Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For developers, Larch is an open-source project, with active development
happening at the `Larch Repository (github.com)`_.  There, you will find
the latest source code and pages for submit bug reports.  To install from
source, you can either clone this repository with::

   git clone http://github.com/xraypy/xraylarch.git

or download and unpack the latest release of the source code package at
`source code (tar.gz)`_ and then do::

    python setup.py install

This will automatically use `pip` to install any requirements and Larch
itself.  Depending on your platform and version of Python, you may need
elevated permissions as from `sudo` to install Larch to a system folder.


Optional Python Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While most of the packages required for Larch will be installed
automatically (and are listed in the `requirements.txt` file in the source
tree), there are a few packages that are useful for some functionality but
somewhat less easy to have as a hard dependency (usually because they are
not readily available on PyPI for all platforms).  These optional packages
are listed in the table below.
Note that most of these will be
installed with Larch whether you install from a binary installer,
with `conda install xraylarch`, with `pip install xraylarch`, or with
`python setup.py install`


.. _recommended_packages_table:

**Table of Recommended Packages for Larch** This is not a complete list of
packages needed for Larch.  Instead, this is a list of packages that may
not be available with `pip install` but are available with `Anaconda
Python`.  None of these are required for using Larch, but may prevent some
functionality from working.

  +----------------+------------------------------------------+
  | Package name   | used for                                 |
  +================+==========================================+
  | dioptas        | XRD image display and integration        |
  +----------------+------------------------------------------+
  | tomopy         | Tomographic reconstruction               |
  +----------------+------------------------------------------+
  | pycifrw        | Reading CIF file                         |
  +----------------+------------------------------------------+
  | psycopg2       | Interacting with PostgresQL database     |
  +----------------+------------------------------------------+

If using Anaconda Python, all of these will be installed with
`conda install -c GSECARS <package_name>`.

To be clear, most of Larch will work fine without these modules installed,
but the corresponding functionality will not be available.


Getting Help
============================

For questions about using or installing Larch, please use the `Ifeffit Mailing List`_.

For reporting bugs or working with the development process, please use the `Larch Github Pages`_.


.. _install-exa:

Docs and Examples
================================

The source kit includes sources for documentation in the `docs` folder
and several examples (including all those shown in this documentation)
in the `examples` folder.

These are also available separately in the zip file at `Larch Docs and
Examples`_ that contains a `doc` folder with this full documentation,
and an `examples` folder with all of the Larch examples.


Citing Larch
========================

Currently, the best citation for Larch is M. Newville, *Larch: An Analysis
Package For XAFS And Related Spectroscopies*. Journal of Physics:
Conference Series, 430:012007 (2013).  :cite:`larch2013`

.. raw:: html

    <span class="__dimensions_badge_embed__"
          data-doi="10.1088/1742-6596/430/1/012007"
          data-style="large_rectangle">
    </span>


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
many parts of Larch, especially for XANES processing and testing of the XAS
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
