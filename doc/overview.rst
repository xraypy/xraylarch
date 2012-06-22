==================================================
Larch: Motivation and Overview
==================================================

Larch is a scientific data processing language.  Though technically
"general purpose", it has been developed for and aimed especially at the
problems of processing and analyziing x-ray spectroscopic and scattering
data collected at modern synchrotrons and x-ray sources.  Thus, Larch has
several related target application areas, including XAFS, XRF, and X-ray
standing waves.  The initial movitation is to replace the Ifeffit package
for XAFS analysis.

Motivation
==============

Many scientific data collection, visualization, and analysis programs have
a *macro language* built into them.  These *macro languages* often have
built-in commands and datastructures important for the problems being
solved.  They typically allow customization, automation, scripting, and
extension of the fundamental operations needed to get the data collection,
visualization, and analysis work done.  Some analysis programs have
full-fledged languages or are simply built on top of a framework such as
Matlab, IDL, Mathematica, R, Eclipse, or Emacs, while many other programs
have very simplistic (often buggy) and limited languages.

While *Domain Specific Languages* (the term *macro language* often implies
that they are implemented by string substitutions, which may be true, but
is sort of beside the point here) can be a very efficient way to provide
flexible interaction and customization of complex software, there are a
great many of them in use, making communication and sharing data between
programs very hard.

Larch is an attempt to make a domain specific language that can be the
basis for x-ray data collection and analysis programs, so that the
algorithms and techniques for visualization and analysis can be better
shared between different programs and fields.  In this respect, Larch is
meant to be the foundation or framework upon which data collection,
visualization, and analysis programs can be written.  By having a common,
extensible language and analysis environment, the hope is that it will be
easier to make data collection, visualization, and analysis programs
interact.



Overview
==========

Larch is written in Python, has syntax that is quite closely related to
Python.  This allows Larch to build upon many great efforts in Python,
especially for scientific computing, including numpy, scipy, h5py, and
matplotlib.  It also turns out to make implementing Larch simpler.  In
fact, Larch is so closely related to Python that a few key points should be
made:


  1. All data items in Larch are really Python objects.

  2. All Larch code is translated into Python and then run using builtin
     Python tools.

This means that an understanding Larch and Python are close to one
another.

 Why Python?
 Why not use Python for everything -- including the DSL?

Design Principles
====================

Since Larch is intended for processing scientific data, organization of
data is a key consideration.  The main feature that Larch uses to help the
user with organizing data is deceptively simple and useful -- the
**Group**.  This is simply an empty container into which any sort of data
can be placed, including other Groups.  This provides a heirarchical
structure of data that can be accessed and manipulated easily via
attributes, as with::

     my_group = group(x = 0.1*arange(101), title='group 1')
     my_group.y = sqrt(my_group.x)
     plot(my_group.x, my_group.y, title=my_group.title)

That is to say, the Group 'my_group' here holds data in a convenient
namespace.


Since much of what Larch is used for is modeling or fitting small data
sets, another key organizing principle is the **Parameter**.  This holds a
value that you might want to be optimized in a least-squares fit.   Thus, a
Parameter can be flagged as a variable, or fixed to not be varied.  In
addition, it can be given a mathematical expression in terms of other
Parameters to determine its value as a constrained value.


Capabilities
=================

At this writing, Larch is capable of doing most data processing and
analysis of XAFS data.  This includes:

   * pre-edge background subtraction and normalization
   * background subtraction for isolating chi(k)
   * XAFS Fourier transforms
   * reading and manipulating Feff Path files
   * fitting Feff Paths to XAFS data
   * general-purpose minimization and curve-fitting.



