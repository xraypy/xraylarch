.. _install-chapter:

====================================
Downloading and Installation
====================================

.. _Larch Repository (github.com): https://github.com/xraypy/xraylarch
.. _Anaconda Python:               https://www.continuum.io/
.. _Pip:                           https://pypi.org
.. _Conda:                         https://conda.io
.. _Python.org:                    https://python.org/
.. _Anaconda Downloads:            https://www.continuum.io/downloads
.. _Miniconda Downloads:           https://docs.conda.io/en/latest/miniconda.html
.. _lmfit:                         https://lmfit.github.io/lmfit-py/
.. _xraydb:                        https://xraypy.github.io/XrayDB/
.. _Larch Releases (github.com):   https://github.com/xraypy/xraylarch/releases
.. _Larch Installer Scripts:       https://github.com/xraypy/xraylarch/tree/master/installers
.. _GetLarch.sh:                   https://raw.githubusercontent.com/xraypy/xraylarch/master/installers/GetLarch.sh
.. _GetLarch.bat:                  https://raw.githubusercontent.com/xraypy/xraylarch/master/installers/GetLarch.bat
.. _Larch Binary Installers:       https://millenia.cars.aps.anl.gov/xraylarch/downloads
.. _source code:                   https://github.com/xraypy/xraylarch/releases/latest
.. _Larch for Windows:             https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-2022-04-Windows-x86_64.exe
.. _Larch for MacOSX:              https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-2022-04-MacOSX-x86_64.pkg
.. _Larch for Linux:               https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-2022-04-Linux-x86_64.sh
.. _Docs and Examples:             https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-2022-04_docs-examples.zip

.. _Ifeffit Mailing List: https://millenia.cars.aps.anl.gov/mailman/listinfo/ifeffit/
.. _Demeter: https://bruceravel.github.io/demeter/
.. _Larch Github Pages: https://github.com/xraypy/xraylarch
.. _Larch Github Issues: https://github.com/xraypy/xraylarch/issues

The latest release version of Larch is |release|.

Larch is in active and continuing development.  The goal is to release
versions every six months, but we don't use a strict schedule, and
typically release more often than that.

There are three ways to install Larch. Which of these is right for you will
depend on your operating system and your familiarity with the Python
programming language and environment:

   1. :ref:`install-binary`.  Use these to get started with XAS Viewer or
      other Larch GUI applications, or if you are not familiar with Python.
   2. :ref:`install-scripts`. Use these if your comfortable with the
      command-line or want to customize your installation.
   3. :ref:`install-conda`. Use this if you already have an Anaconda Python
      environment that you want to use.

There should not be any difference in the resulting code or packages when
using these different methods.  One is not "more right" or even "more
preferred".  In short, use the Binary installer unless you know that you
want to install into an existing Python environment.  If that doesn't work,
try the installation script.

.. _install-binary:

Installing from a Binary installers
=====================================================

.. _installers_table:

**Table of Larch binary installers**

  +---------------------+------------------------+-----------------------------+
  | Operating System    | Binary Installer File  | Installation Notes          |
  +=====================+========================+=============================+
  | Windows (64 bit)    | `Larch for Windows`_   | :ref:`Notes <install-win>`  |
  +---------------------+------------------------+-----------------------------+
  | Mac OSX (64 bit)    | `Larch for MacOSX`_    | :ref:`Notes <install-mac>`  |
  +---------------------+------------------------+-----------------------------+
  | Linux (64 bit)      | `Larch for Linux`_     | :ref:`Notes <install-lin>`  |
  +---------------------+------------------------+-----------------------------+

Binary installers for Windows, Mac OSX, and Linux, are available at
`Larch Binary Installers`_.  These are fairly large (400 to 600 Mb files)
self-contained files that will install a complete Anaconda Python
environment with all of libraries needed by Larch.  Normally, this
installation will create a folder called `xraylarch` in your home folder --
see platform-specific notes below.


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

For Windows, download the `Larch for Windows`_ binary installer above and run it to
install Larch.  This will be installed to ``C:\Users\<YourName>\xraylarch`` for most
individual Windows installations or to
``C:\Users\<YourName>\AppData\Local\xraylarch`` if your machine is part of a
Windows Workgroup or Domain.

.. note:   If you get prompted for an administrative password during the installation process, you
   should make sure you are installing to a folder that is writable by the user.


Alternatively you can download the `GetLarch.bat`_ script, and run that by double-clicking
on it. This will download, install, and configure the Larch package, with a result that
is nearly identical to the binary installer.


.. _install-mac:

MacOS Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


For Mac OS, download the `Larch for MacOSX`_ package installer above and click it to
install Larch.  There are two important notes:

.. note::

   With MacOS 10.15 (Catalina), Apple will not install non-signed 3rd party packages by default.
   You may need to go into General Settings part of the **Security & Privacy** section of **System
   Preferences** and explicitly allow this package to be installed. You probably will be prompted for
   an Administrative password.

.. note::

   You need to explicitly click on "Install only for me" during the installation process.  If you
   get prompted for an Administrative password by the installer, go back and explicitly choose
   "Install only for me".

Alternatively you can download the `GetLarch.sh`_ script, and run that in a Terminal
session (Applications->Utilities->Terminal). This will download, install, and configure
the Larch package, with a result that is nearly identical to the binary installer.  If you
run into any problems with permissions or administrative privileges or "unauthorized
application" with the package installer, running this installer script actually avoids all
of those issues since your user account will simply be running the commands to write files
to your home directory.


.. _install-lin:

Linux Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

   There have been reports of the binary installation not working well on
   all Linux systems.  We recommend using GetLarch.sh on Linux

For Linux, download the `Larch for Linux`_ shell installer file, then open a Terminal, use `cd` to
move to the download folder (typically `$HOME/Downloads`) and run::

    ~> bash ./xraylarch-2022-04-Linux-x86_64.sh

Desktop shortcuts as ``.desktop`` files will be created on all Linux platforms, but whether these
actually appear on your desktop depends on the Windowing system used:  they will appear on the
desktop with KDE and many other systems, but not with Gnome.  Clickable icons should also show up
in the Applications selection of the "Start Menu" or Applications list.

Alternatively you can download the `GetLarch.sh`_ script, and run that in a Terminal
session. This will download, install, and configure the Larch package, with a result that
is nearly identical to the binary installer.

Larch uses a relatively large number of Python packages (**dependencies**),
and these also evolve.  We try keep up with the latest versions of these
packages, but changes in those sometimes complicate the installation of
Larch.  We also try to keep these installation instructions up-to-date, but
strategies we use may change (slowly, we hope). Your feedback, bug reports,
and patience are greatly appreciated.



.. _install-scripts:

Installing with the `GetLarch.sh` and `GetLarch.bat` scripts
======================================================================

This method is recommended for those who are relatively comfortable using a
command-line, and is helpful for debugging cases where the binary installer
has failed.  The approach here is basically to run a script that follows
the steps that the binary installer should follow, but is likely to give
more useful error messages if something goes wrong.  On Linux and MacOS,
there are also command-line options.

To install with this method, download and execute one of the following:

   - `GetLarch.sh`_ for Linux and Mac OSX
   - `GetLarch.bat`_ for Windows

Open a Shell or Terminal, find the location of this script and run that.
On Windows, that would be launching the `cmd` program, and doing something
like::

   cd C:\Users\<YOURNAME>\Downloads
   GetLarch


On MacOS on Linux, open a Terminal (from Applications -> Utilities on
MacOS), and then type::

  cd Downloads
  sh GetLarch.sh


If this script fails, report it to the `Larch Github Issues`_ (including
the error trace and the `GetLarch.log` file).

The scripts will download and install `Miniforge Python` which uses Anaconda
Python and the `conda-forge` channel as the basis of an installation that will
be essentially identical to the environment installed by the binary installers,
that is, the whole environment is stored in a folder called `xraylarch` in your
home folder. In case of problems, simply remove this folder to clean the
installation.

.. note::2

   **Optional/expert** You may execute `GetLarch.sh --devel` to install the latest development version instead of the latest release.

You can also read these scripts and modify them for your needs (or maybe suggest ways
we could maintain that for others to use too).


.. _install-conda:

Installing into an existing Anaconda Python environment
================================================================

The following procedure is recommended for those who are familiar with `Anaconda
Python`_ / `Conda`_ and have already installed it in their system.


.. note::

   Some packages that Larch uses are not currently (January 2022) handled
   by the standard Python package manager `Pip`_.  For this reason, we use
   a `Conda`_ environment and "conda forge" for installing them.  These
   packages include:

   * `pymatgen`: needed for handling CIF files and running FEFF calculations.
   * `wxpython`: needed for all plotting, graphics and GUI applications.
   * `tomopy`: needed for reconstructing X-ray fluorescence tomography.
   * `python.app`: needed (from conda-forge) for Anaconda-based Python on MacOS.
   * `epicsapps`: applications using the Epics control system.

   Most of Larch functionality can be used as a library without these
   packages installed.

Within a shell:

1. activate your conda environment (called `base` by default) and update it:

.. code:: bash

   conda activate
   conda update -y conda python pip

2. **(optional/expert)** create a dedicated environment for Larch and activate it:

.. code:: bash

   conda create -y --name xraylarch python==3.9
   conda activate xraylarch
   conda update --all

3. install main dependencies:

.. code:: bash

   conda install -y "numpy=>1.20" "scipy=>1.6" "matplotlib=>3.0" scikit-learn pandas
   conda install -y -c conda-forge wxpython pymatgen tomopy pycifrw

4. install Larch (latest release):

.. code:: bash

   pip install xraylarch

5. if anything of the above fails, report it to the `Larch Github Issues`_



Notes on Anaconda
~~~~~~~~~~~~~~~~~~

By default, Anaconda Python installs into your own home folder (on Windows, this
will be the `APPDATA` location, which is typically something like
``C:\\Users\<YourName>\Anaconda3`` or
``C:\\Users\<YourName>\AppData\Local\Anaconda3``).  As with the single-file
installers below, installing Anaconda Python does not require extra permissions
to install, upgrade, or remove components.  Anaconda includes a robust package
manager called *conda* that makes it easy to update the packages it manages,
including Larch.

Start by installing the latest version of Anaconda Python from the
`Anaconda Downloads`_ site.  Python 3.8 or Python 3.9 is recommended.  As
of this writing, some testing has been done with Python 3.10: this requires
a "bleeding edge" versions of wxPython, which we hope is resolved soon.  We
no longer test with Python 3.7 or earlier: Python 3.7 might work, Python
3.6 and earlier will not.  You can also download and install Miniconda from
`Miniconda Downloads` as a starting distribution.


Updating a previous installation
==================================

Updating  with `conda` is no longer supported. The best i to use `pip` to
update, even when using Anaconda Python::

    pip install --upgrade xraylarch


Installing the development version
=========================================

For the brave, a nightly build of the latest development version can be downloaded and installed with

.. code:: bash

   python -m pip install https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-latest-py3-none-any.whl


Making Desktop shortcuts to Link to the Applications
=======================================================

To make a `Larch` folder on your desktop with shortcuts (Windows or Linux) or
Applications (MacOS) for the main Larch applications, you can then type::

    larch -m

If that complains that it does not find `larch`, you may have to explicitly
give the path to Python and/or Larch::

   $HOME/xraylarch/bin/larch -m

from Linux or MacOSX or::

   %APPDATA%\\Local\\xraylarch\Scripts\larch.exe -m

from Windows.



Larch for developers (source installation)
===============================================


For developers, Larch is an open-source project, with active development
happening at the `Larch Repository (github.com)`_.  There, you will find
the latest source code and pages for submit bug reports.

To get started, we recommend following the installation instructions for or
ref:`install-binary`, ref:`install-script`, or ref:`install-conda`.  Then
to install `Larch` from source, you can clone the source repository with::

   git clone https://github.com/xraypy/xraylarch.git

and then install with::

    pip install -e .

This use of `pip` will install any requirements and Larch itself, but those
should have been installed already when you installed.  Depending on your
platform and version of Python you are installing to, you may need elevated
permissions as from `sudo` to install Larch to a system folder.


Optional Python Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While most of the packages required for Larch will be installed
automatically (and are listed in the `requirements.txt` file in the source
tree), there are a few packages that are useful for some functionality but
somewhat less easy to have as a hard dependency (usually because they are
not readily available on PyPI for all platforms).  These optional packages
are listed in the table below.  Note that most of these will be
installed with Larch whether you install from a binary installer,
with `conda install xraylarch`, with `pip install xraylarch`, or with
`python setup.py install`


Getting Help
============================

For questions about using or installing Larch, please use the `Ifeffit Mailing List`_.

For reporting bugs or working with the development process, please submit an issue at the `Larch Github Pages`_.

.. _install-exa:

Docs and Examples
================================

The source kit includes sources for documentation in the `docs` folder
and several examples (including all those shown in this documentation)
in the `examples` folder.

These are also available separately in the zip file at `Docs and Examples`_
that contains a `doc` folder with this full documentation, and an
`examples` folder with all of the Larch examples.


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
interface and the RIXS viewer.  Tom Trainor had a very strong influence on
the original design of Larch, and helped with the initial version of the
python implementation.  Yong Choi wrote the code for X-ray standing wave
and reflectivity analysis and graciously allowed it to be included and
modified for Larch.  Tony Lanzirotti and Steve Sutton have provided
wonderful and patient feedback on many parts of Larch, especially for XANES
processing and testing of the XAS Viewer GUI.

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

Larch uses X-ray scattering factors and cross-sections fro the `xraydb`_
library.  This uses code to store and read the X-ray Scattering data from
the Elam Tables was modified from code originally written by
Darren S. Dale.  Refined values for anomalous scattering factors there have
been provided directly by Christopher T. Chantler.  Further details of the
origin of much of the tabularized X-ray data is given in
:ref:`xraydb-chapter`.

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
