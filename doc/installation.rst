.. _install-chapter:

====================================
Downloading and Installation
====================================

.. _Larch Repository (github.com): https://github.com/xraypy/xraylarch
.. _Anaconda Python:               https://www.continuum.io/
.. _PyPI:                          https://pypi.org
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

Larch is in active and continuing development.  We do not use a strict
schedule, but for the past few years, new versions have typically been
released every 2 months or so.


There are three ways to install Larch. Which of these is right for you will
depend on your operating system and your familiarity with the Python
programming language and environment:

   1. :ref:`install-binary`.  Use these to get started with XAS Viewer or
      other Larch GUI applications, or if you are not familiar with Python.
   2. :ref:`install-scripts`. Use these if your comfortable with the
      command-line or want to customize your installation.
   3. :ref:`install-conda`. Use this if you already have an Anaconda Python
      environment that you want to use.

There will not be any difference in the resulting code or packages when using
these different methods.  Each of these will result in a Python environment
from which you can either use Larch and its GUI applications, or develop code
with Larch.  We recommend using the Binary installer on Windws, and the
installation scripts on macOS or Linux, unless you know that  you want to
install into an existing Python environment.

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
  | macOSX  (64 bit)    | `Larch for MacOSX`_    | :ref:`Notes <install-mac>`  |
  +---------------------+------------------------+-----------------------------+

Binary installers for Windows and macOSX are available at `Larch Binary
Installers`_.  These are fairly large (400 to 600 Mb files) self-contained
files that will install a complete Anaconda Python environment with all of
libraries needed by Larch.  Normally, this installation will create a folder
called `xraylarch` in your home folder -- see platform-specific notes below.


.. note::

   There can be no spaces in your username or the path in which Larch is
   installed.

   If you have a space in your Windows username, you can probably install
   to ``C:\Users\Public`` - that has worked for some people!


Installing with these installer programs should write to files only to
folders owned by the user account. It should not require administrative
privilege and should not interfere with any thing else on your system (such
as system Python).

These installers will also create a folder called `Larch` on your desktop
that contains links (or shortcuts or Apps) to many of the Larch GUI
applications listed in :ref:`Table of Larch Applications and Programs
<larch_app_table>`.  This includes tools for X-ray Absorption spectroscopy,
X-ray fluorescence spectroscopy, and working with X-ray diffraction images.

.. _install-win:

Windows Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For Windows, download the `Larch for Windows`_ binary installer above and
run it to install Larch.  This will be installed to
``C:\Users\<YourName>\xraylarch`` for most individual Windows installations
or to ``C:\Users\<YourName>\AppData\Local\xraylarch`` if your machine is
part of a Windows Workgroup or Domain. As mentioned above, if your user
name has a space in it, you will probably need to install to
``C:\Users\Public``.


.. note: If you get prompted for an administrative password during the
   installation process, you should make sure you are installing to a
   folder that is writable by the user.


Alternatively you can download the `GetLarch.bat`_ script, and run that by
double-clicking on it. This will download, install, and configure the Larch
package, with a result that is nearly identical to the binary installer.


.. _install-mac:

MacOS Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


For Mac OS, download the `Larch for MacOSX`_ package installer above and click
it to install Larch.  There are two important notes:

.. note::

   With MacOS 10.15 (Catalina), Apple will not install non-signed 3rd party
   packages by default.  You may need to go into General Settings part of the
   **Security & Privacy** section of **System Preferences** and explicitly
   allow this package to be installed. You probably will be prompted for an
   Administrative password.

.. note::

   You need to explicitly click on "Install only for me" during the
   installation process.  If you get prompted for an Administrative password
   by the installer, go back and explicitly choose "Install only for me".

Alternatively you can download the `GetLarch.sh`_ script, and run that in a
Terminal session (Applications->Utilities->Terminal). This will download,
install, and configure the Larch package, with a result that is nearly
identical to the binary installer.  If you run into any problems with
permissions or administrative privileges or "unauthorized application" with
the package installer, running this installer script actually avoids all of
those issues since your user account will simply be running the commands to
write files to your home directory.


.. _install-lin:

Linux Notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


For Linux, use the `GetLarch.sh`_ script and run that in a Terminal session.

Desktop shortcuts as ``.desktop`` files will be created on all Linux
platforms, but whether these actually appear on your desktop depends on the
Windowing system used: they will appear on the desktop with KDE and many other
systems, but not with Gnome.  Clickable icons should also show up in the
Applications selection of the "Start Menu" or Applications list.


.. _install-scripts:

Installing with the `GetLarch.sh` and `GetLarch.bat` scripts
======================================================================

This method is recommended on Linux, and for those who are relatively
comfortable using a command-line, and is helpful for debugging cases where the
binary installer has failed.  The approach here is basically to run a script
that follows the steps that the binary installer should follow, but is likely
to give more useful error messages if something goes wrong.  To install with
this method, download and execute one of the following:

   - `GetLarch.sh`_ for Linux and Mac OSX
   - `GetLarch.bat`_ for Windows

Open a Shell or Terminal, find the location of this script and run that.
On Windows, that would be launching the `cmd` program, and doing something
like::

   cd C:\Users\<YOURNAME>\Downloads
   GetLarch


On macOS on Linux, open a Terminal (from Applications->Utilities->Terminal on
macOS), and then type::

  cd Downloads
  sh GetLarch.sh


If this script fails, report it to the `Larch Github Issues`_ (including
the error trace and the `GetLarch.log` file).

The scripts will download and install `Mambaforge Python` which uses Anaconda
Python and the `conda-forge` channel as the basis of an installation that will
be essentially identical to the environment installed by the binary installers,
that is, the whole environment is stored in a folder called `xraylarch` in your
home folder. In case of problems, simply remove this folder to clean the
installation.


.. _install-conda:

Installing into an existing Anaconda Python environment
================================================================

If you are already using an `Anaconda Python`_  environment, you may want to
install Larch into that environment or create a new environment for it.
Larch uses many of the common "scipy ecosystem" packages. The main packages
that you may need to install that may not be installed are:

   * `wxpython`: needed for all plotting, graphics and GUI applications.
   * `pymatgen`: needed for handling CIF files and running FEFF calculations.
   * `tomopy`: needed only for reconstructing X-ray fluorescence tomography.
   * `epicsapps`: applications using the Epics control system.

To be clear, much of the core Larch functionality can be used as a library
without these packages installed, but especially `wxpython` and `pymatgen` are
heavily used and should be installed.

There is a `conda-forge` package for X-ray Larch, so from a shell it may be
that all you need to do is run


.. code:: bash

   conda install -yc conda-forge xraylarch


To create a dedicated environment, can either use the `conda-forge` package or
try something like this to first create a dedicated "scipy ecosystem"
infrastructure and then install xraylarch with pip:

.. code:: bash

   conda create -y --name xraylarch python=>3.10
   conda activate xraylarch
   conda install -y -c conda-forge wxpython pymatgen scipy h5py matplotlib
   pip install xraylarch



Since the `PyPI_` packages are the main release package, this method may better
ensure that you get the latest version.


Finally, no matter how you install Larch, you can run

.. code:: bash

   larch -m


to create the Larch desktop application launchers or shortcuts.


Updating a previous installation
==================================

As new versions of X-ray Larch are released, they will be announced and pushed
to `PyPI`_, so that updating can be done with:

    pip install --upgrade xraylarch


For versions up to 0.9.68, XAS Viewer and other Larch Applications would
notify users as updates became available and prompt them to install the latest
version.

.. note::

   Automatic updates using XAS Viewer have been unreliable for a long time,
   and can cause a non-working system, especially on Windows.


With version 0.9.70,these notifications about updates are now informational
and do not prompt for an immediate update. In addition, there is now a desktop
shortcut called "Larch Updater" which will run the update `pip` command above.


Installing the development version
=========================================

For the brave, a nightly build of the latest development version can be downloaded and installed with

.. code:: bash

   python -m pip install https://millenia.cars.aps.anl.gov/xraylarch/downloads/xraylarch-latest-py3-none-any.whl


We try to keep this working, but as this is an automated snapshot it might
catch the development in the middle of trying to fix something tricky.

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
ref:`install-binary`, ref:`install-script`, or ref:`install-conda`.  That
gives you a base starting Python environment that we can all be pretty sure is
working.  With that in place, to install `Larch` from source, you can clone
the source repository with::

   git clone https://github.com/xraypy/xraylarch.git

and then install with::

    pip install -e .

This use of `pip` will install any requirements and Larch itself, but those
should have been installed already when you installed.  Depending on your
platform and version of Python you are installing to, you may need elevated
permissions as from `sudo` to install Larch to a system folder.


Optional Python Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While most of the packages required for Larch will be installed automatically
(and are listed in the `requirements.txt` file in the source tree), there are
a few packages that are useful for some functionality but somewhat less easy
to have as a hard dependency (usually because they are not readily available
on `PyPI`_ for all platforms).  These optional packages are listed in the
table below.  Note that most of these will be installed with Larch whether you
install from a binary installer with `pip install xraylarch`.


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
