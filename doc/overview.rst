==================================================
Larch: Motivation and Overview
==================================================

Larch is a scientific data processing language.  Though fairly general
purpose, it has been developed for and aimed especially at the problems of
processing and analyziing x-ray spectroscopic and scattering data collected
at modern synchrotrons and x-ray sources.  Thus, Larch has several related
target application areas, including XAFS, XRF, and X-ray standing waves.
The initial movitation was to replace the Ifeffit package for XAFS
analysis, but the ability to add XRF capabilites and to use it as a
"Spec-like" language for data collection and processing were quickly added
to the list of things Larch should be able to do.

Larch gives a simple command-line interface (a Read-Eval-Print Loop), but
can also be scripted in "batch mode".  GUIs can be built upon Larch by
simply generating the commands, making it easy to separate the layout from
the actual processing steps, so that the processing steps might be recorded
and used to make a "batch script".  Larch is easily called from Python.  In
addition, you can use Larch with remote-procedure calls, so that it can be
run from different languages, or run on different machines.

General Motivation of the Design
====================================

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
that they are implemented by string substitutions, which may sometimes be
true, but is sort of beside the point here) can be a very efficient way to
provide flexible interaction and customization of complex software, there
are a great many of them in use, making communication and sharing data
between programs very hard.

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

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/
.. _h5py: http://code.google.com/p/h5py/

Larch is written in Python, an interpreted (non-compiled) language that has
become quite popular in a range of scientific disciplines.  Python is known
for its very clear syntax and readability, and Larch has syntax that is
built upon, and very closely related to Python's.  Using Python in this way
not only gives a fairly elegant and readable language, but also allows
Larch to build upon many great efforts in Python, especially for scientific
computing, including `numpy`_, `scipy`_, `h5py`_, and `matplotlib`_.  Using
Python also turns out to make implementing Larch and adding complex
functionality such as XAFS analysis capabilities simple.


In fact, Larch is so closely related to Python that a few key points should
be made:

  1. All data items in Larch are really Python objects.

  2. All Larch code is translated into Python and then run using builtin
     Python tools.

In a sense, Larch is a dialect of Python.  This means has a few that an
understanding Larch and Python are close to one another.  This in itself
can be seen as an advantage -- Python is a popular, open-source, language
that any programmer can easily learn, and books and web documentation about
Python are plentiful.  If you known Python, Larch will be very easy to use,
and vice versa.


Design Principles, Key Concepts
====================================

Since Larch is intended for processing scientific data, organization of
data is a key consideration.  The main feature that Larch uses to help the
user with organizing data is deceptively simple and useful -- the
**Group**.  This is simply an empty container into which any sort of data
can be placed, including other Groups.  This provides a heirarchical
structure of data that can be accessed and manipulated easily via
attributes, as with::

     larch> my_group = group(x = 0.1*arange(101), title='group 1')
     larch> my_group.y = sqrt(my_group.x)
     larch> plot(my_group.x, my_group.y, title=my_group.title)

That is to say, the Group 'my_group' holds data in a convenient namespace.
You can see thed contents of a group::

    larch> show(my_group)
    == Group 0x6e15970: 3 symbols ==
      title: 'group 1'
      x: array<shape=(101,), type=dtype('float64')>
      y: array<shape=(101,), type=dtype('float64')>

which shows that this group has 3 components.  Other things to note are
that 'x' and 'y' hold arrays of data, and thatfunctions such as 'sqrt' act
on all elements of the array at once.

Since much of what Larch is used for is modeling or fitting small data
sets, another key organizing principle is the **Parameter**.  This holds a
value that you might want to be optimized in a least-squares fit.   Thus, a
Parameter can be flagged as a variable, or fixed to not be varied.  In
addition, it can be given a mathematical expression in terms of other
Parameters to determine its value as a constrained value.



Capabilities
=================

At this writing, Larch has the following general capabilities:

   * a full suite of mathematical functionality, with array handling
     builtin (so that functions work on full arrays).
   * a general purpose language with flow-control (for and while loops),
     and conditional evaluation (if-then-else).
   * some built-in I/O functionality for ASCII files and HDF5.
   * simple line plots, with customizable line properties.
   * simple 2-D image dispays, with some rudimentary customization.
   * general-purpose minimization and curve-fitting.


For XAFS analysis in particular, Larch is able to do most data processing
and analysis steps needed, including:

   * pre-edge background subtraction and normalization
   * background subtraction for isolating chi(k)
   * XAFS Fourier transforms
   * reading and manipulating Feff Path files
   * fitting Feff Paths to XAFS data
   * general-purpose minimization and curve-fitting.




