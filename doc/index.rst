.. xraylarch documentation master file,


=====================================
Larch
=====================================

Larch is a scientific data processing language that is designed to be

    * easy to use for novices.
    * complete enough for intermediate to advanced data processing.
    * data-centric, so that arrays of data are easy to manage and use.
    * easily extensible with python.

Larch is targeted at tools and algorithms for analyzing x-ray spectroscopic
and scattering data, especially the sets of data collected at modern
synchrotrons.  It has several related target applications, all meant to be
better connected through a common *macro language* for dealing with
scientific data sets.

Many data collection, visualization, and analysis programs have an ad-hoc
macro languages built in that allow some amount of customization,
automation, scripting, and extension of the fundamental operations
supported by the programs.  These macro languages are rarely used in more
than one program, making communication and sharing data between programs
very hard.

Larch is an attempt to make a macro language that can be used for many such
applications, so that the algorithms and techniques for visualization and
analysis can be better shared between different programs and fields.  In
this respect, Larch is meant to be the foundation or framework upon which
data collection, visualization, and analysis programs can be written.  By
having a common, extensible macro language and analysis environment, the
hope is that it will be easier to make data collection, visualization, and
analysis programs interact.

Larch is written in Python, has syntax that is quite closely related to
Python, and makes use of many great efforts in Python, especially for
scientific computing.  These include numpy, scipy, and matplotlib.

The initial target application areas for Larch are

  * XAFS analysis, becoming Ifeffit verversio 2
  * tools for micro-XRF mapping visualization and analysis.
  * quantitative XRF analysis.
  * X-ray standing waves and surface scattering analysis.

Contents:

.. toctree::
   :maxdepth: 3

   installation
   tutorial
   developers
   language
   xafs
   xrf

Indices and tables
~~~~~~~~~~~~~~~~~~~~~~

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


