====================================
Downloading and Installation
====================================

.. _Larch Repository (github.com):               http://github.com/xraypy/xraylarch
.. _Anaconda Python:                             http://www.continuum.io/
.. _Anaconda Downloads:                          http://www.continuum.io/downloads
.. _Larch Releases (github.com):                 https://github.com/xraypy/xraylarch/releases


The latest release version of Larch is |release|.  Larch is in active and
continuing development, and the intention is to tag a new release version
every six months or so.  Of course, there may be bugs and unintended
features, and some missing or incomplete desired features.  Still, most of
what is in Larch is working, stable, and ready for use.


There are several ways to download and install Larch.  Starting with Larch
0.9.27, the **recommended** way to install and run Larch on Windows and Mac
OS X is with `Anaconda Python`_ (version 2.7).  Note that Larch does not yet
work with Python 3. series).  For Windows, a binary installer may be
available soon, though this is not updated as often as the source code or
Anaconda package.  In addition, Larch can be installed from its source
code, which works easily on most modern Linux systems.


Using Anaconda Python
================================

`Anaconda Python`_ provides a free and
well-supported version of Python for scientific work with many useful
packages included.  By default, Anaconda Python installs into your own home
folder and does not require extra permissions to install, upgrade, or
remove components.  Anaconda includes a robust package manager called
*conda* that makes it easy to update to the latest versions of Larch when
you are ready.

So, begin by installing the latest version of Anaconda Python 2.7 from
their `Anaconda Downloads`_ site.  Once that is installed, you can open a
Terminal (on Linux or Mac OSX) or the Anaconda prompt (on Windows) and
type::

    conda install -yc newville xraylarch

    # on Windows or Mac OSX
    larch_makeicons

This will install all the software needed to run Larch and all its
components.  The `larch_makeicons` command will create a Folder called
*Larch* on your desktop that includes shortcuts (Windows) or small Apps (Mac
OSX) to run the following Larch programs:

   * `larch`  -- simplest command-line interface.
   * `larch_gui` -- Enhanced command-line interface with GUI data browser.
   * `xrfdisplay` -- Display XRF Spectrum.
   * `gse_mapviewer` -- XRF Mapviewer for GSECARS XRF Map data.
   * `gse_scanviewer` -- Simple XAFS and Scan viewer for GSECARS data.

An advantage of using Anaconda is that updates can be installed with::

    conda update -yc newville xraylarch


Source Installation
=========================

Larch can be installed from source code.  If not using Anaconda, this is
necessary for Linux, and can be done for other systems as well.

The latest releases of the source code will be available from `Larch
releases (github.com)`_.  In addition, you can use `git` to grab the latest
development version of the source code::

   git clone http://github.com/xraypy/xraylarch.git


Prerequisites
----------------------

Larch requires Python version 2.7.1 or higher.  Support for Python 3.X is
partial, in that the core of Larch does work, and numpy, and scipy, h5py,
and matplotlib have all been ported to Python 3.X.  But the testing for
Python 3.X has been minimal, and the graphical interfaces, based on
wxPython, has not yet been fully ported to Python 3.X.

The following Python packages are all required for Larch: numpy, scipy,
matplotlib, h5py, sqlalchemy, and wxpython.  These are easily installed as
standard packages on almost all platforms.

Installation
---------------------

After unpacking the source distribution kit, installation from source on any platform is::

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
