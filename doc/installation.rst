====================================
Downloading and Installation
====================================

.. _Larch Repository (github.com): http://github.com/xraypy/xraylarch
.. _Anaconda Python:               http://www.continuum.io/
.. _Anaconda Downloads:            http://www.continuum.io/downloads
.. _Larch Releases (github.com):   https://github.com/xraypy/xraylarch/releases


The latest release version of Larch is |release|.  Larch is in active and
continuing development, and the intention is to tag a new release version
every three to six months.  Of course, there may be bugs and unintended
features, and some missing or incomplete desired features.  Still, most of
what is in Larch is working and ready for use.  New and in-development
features and application will be explicitly described as "beta".

Larch is written in Python and requires and existing Python interpreter to be
installed on your computer, along with a handful of common libraries for
scientific computing.

The **recommended** way to install and run Larch is with `Anaconda Python`_
version 2.7.  Larch can be installed from its source code, which can work
fairly easily on most computers and operating systems, but the Anaconda
package is certainly easier to use and comes with the packages that Larch
needs already installed or automatically fetched when installing Larch.

Python Versions: 2.7 or 3.6?
================================

As of this writing (Summer, 2017) there are two main supported versions of
Python: Version 2.7 and Version 3.6.  Larch can now work with either
version of Python.  The GUI toolkit (wxPython) used by Larch is still not
officially released for Python 3, but Larch does work well with the
in-development version of wxPython.  Support for Larch running with Python
3.6 should be considered experimental, and we invite brave users to try it
out.  We are eager to migrate Larch to Python 3.6, and expect to do so
within year or so.


Using Anaconda Python
================================

`Anaconda Python`_ provides a free and well-supported version of Python for
scientific work with many useful packages included.  By default, Anaconda
Python installs into your own home folder (on Windows, it will use the
`APPDATA` location, which is typically something like
`C:\\Users\\YourName\\AppData\\Local\\Continuum\\Anaconda2`).  Installing does
not require extra permissions to install, upgrade, or remove components.
Anaconda includes a robust package manager called *conda* that makes it
easy to update the packages it manages, including Larch.

Begin by installing the latest version of Anaconda Python (as described
above Python 2.7 is currently recommended over Python 3.6 except for the
most adventerous users) from the `Anaconda Downloads`_ site.  Once that is
installed, you can open a Terminal (on Linux or Mac OSX) or the Anaconda
prompt (on Windows) and type these 2 commands::

    conda install -yc GSECARS xraylarch

    larch_makeicons

This will install all the software needed to run Larch and all its
components.  On Windows and Mac OSX, the second command will also create a
Folder called *Larch* on your desktop that includes shortcuts (Windows) or
small Apps (Mac OSX) that you can click on to run the following Larch
applications:

   * `larch`  -- simplest command-line interface.
   * `larch_gui` -- Enhanced command-line interface with GUI data browser.
   * `gse_mapviewer` -- XRF Mapviewer for GSECARS XRF Map data.
   * `gse_scanviewer` -- Simple XAFS and Scan viewer for GSECARS data.
   * `xrfdisplay` -- Display XRF Spectrum.
   * `xyfit` -- Display and Peak Fitting of XANES and other 1D spectra (beta).
   * `1D XRD Viewer` -- Display and work with XRD diffraction patterns (beta).
   * `2D XRD Viewer` -- Display and work with XRD diffraction images (beta).

A key advantage of using Anaconda is that once installed, updates can be
installed with::

    conda update -yc GSECARS xraylarch

As of this writing, some functionality -- notably X-ray diffraction -- may
need additional libraries installed, and some of these libraries may not be
available for Python3.6 or for all platforms.   We're working on this, but
if you need help, please contact us.


Source Installation
=========================

Larch can be installed from source code.  The latest releases of the source
code will be available from `Larch releases (github.com)`_.  In addition, you
can use `git` to grab the latest development version of the source code::

   git clone http://github.com/xraypy/xraylarch.git


Prerequisites
----------------------

Larch requires Python version 2.7 or 3.6. Larch works with Python 3.6 but
requires the not-yet-officially released Phoenix branch of wxPython.  The
following Python packages are all required:

    numpy, scipy, matplotlib, h5py, sqlalchemy, six, lmfit, wxPython,
    wxmplot, wxutils, asteval.

These are all available for Anaconda Python 2.7 and 3.6, either from the
core Anaconda packages or from the GSECARS conda channel, and will be
installed with `conda install -c GSECARS xraylarch`.

If you're installing from source or using a Python distribution other than
Anaconda, all these packages are also available from PyPI and can be
installed with  `pip install`

There are a fair number of packages that are required for some of the
advanced and in-development X-ray diffraction analysis capabilities.  These
include

   fabio, pyfai, pycifrw

For the most part, these are available from Anaconda channels for most
systems and versions.  There may be some missing features or poorly-tested
features.  If you experience problems, please let us know!


Installation from Source
----------------------------

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


.. literalinclude:: ../LICENSE
