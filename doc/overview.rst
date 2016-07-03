==================================================
Larch: Motivation and Overview
==================================================

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _h5py: http://code.google.com/p/h5py/
.. _matplotlib: http://matplotlib.org/


Larch brings together data processing routines for synchrotron X-ray
techniques and provides high-level scripting tools for data manipulation,
visualization, and analysis.  The initial goal was to replace the Ifeffit
package for XAFS analysis in order to better deal with larger datasets,
make it easier to modify and improve XAFS analysis algorithms, and to
provide more modern data manipulation and visualization tools.
Visualization and analysis of X-ray fluorescence spatial maps and spectra
from X-ray microprobe beamlines was is a key requirement, and incorporating
tools for related techniques like X-ray standing waves and X-ray
diffraction is a high priority.  Larch also makes it easy to bring
visualization, processing, and analysis routines with data collection
processes to give a more seamless workflow that spans data collection and
analysis, using core functionality that can be scripted and GUIs built on
top of these core functions.  While Larch is a work in progress, it has
already met most of these initial goals.

Larch is written in Python, a free, general-purpose interpreted language
known for its clear syntax and readability.  Python has become quite
popular in a range of scientific disciplines due to many well-designed an
supported libraries, including `numpy`_, `scipy`_, `h5py`_, and
`matplotlib`_, and is being adopted by many groups in the synchrotron X-ray
community.  Being able to build on existing tools and tap into a large pool
of scientists who are able and willing to work in Python was seen as a huge
benefit in the development of Larch.

The key design decision for Larch is to build a domain-specific language or
*macro language* as the framework to tie together the various
functionality.  In the synchrotron community, many scientists are familiar
with the Spec program for data collection, which is implemented as an
interactive macro language - a language that is fairly general purpose, but
also has many built in functions for interactively collecting diffraction
data.  Ifeffit was built with a similar approach, though with a much worse
macro language than Spec, though one that was complete and flexible enough
for writing complex analysis scripts, and for GUIs to be built upon this
macro language.  In some sense, Larch is an attempt to make something akin
to *Spec for Data Analysis*, in which high-level analysis and visualization
routines are readily available in a coherent scripting environment.

Thus, Larch provides a macro language that gives a simple command-line
interface (a Read-Eval-Print Loop).  Scripts can be written and be run
"batch mode".  GUIs can be built upon Larch by simply generating the
commands, which makes it easy to separate the GUI controls layout from the
actual processing steps, so that the processing steps might be recorded and
used to make a script to reproduce or refine the steps defined from the
GUI.  In addition you can use Larch with remote-procedure calls, so that it
can be run as a service, and called from a variety of languages and from
different machines.  Finally, Larch can be used as a Python library,
nearly completely side-stepping the Larch macro language.

The Larch macro language is implemented in Python with Python's own
language tools, and is very closely related to Python.  It is designed have
a slightly shallower learching curve and less formal approach.  To be
clear, it is a *worse* general purpose programming language than Python,
but better suited to the tasks needed for manipulating and analyzing X-ray
data.  Since its syntax is so closely related to Python, it is possible to
write code that is both valid Python and Larch.

In fact, the Larch language is so closely related to Python that a few key
points should be made:

  1. All data items in Larch are really Python objects.

  2. All Larch code is translated into Python and then run using builtin
     Python tools.

In a sense, Larch is a dialect of Python.  Thus an understanding Larch and
Python are close to one another.  This in itself can be seen as an
advantage -- Python is a popular, open-source, language that any programmer
can easily learn.  Books and web documentation about Python are plentiful.
If you known Python, Larch will be very easy to use, and vice versa.


Key Concepts of Larch
=================================

Since Larch is intended for processing scientific data, the organization of
data is a key consideration.  There also needs to be some organization of
functions and routines.  The main concept that Larch uses to help the user
with organizing data is **Group**.  This is simply a container into which
any sort of data or function can be placed, including other Groups.  The
data in a Group can be accessed using a syntax of **<Group>.<Member>**,
as with::

     larch> my_group = group(x = range(11), scale=10.2, title='group 1')
     larch> my_group.y = my_group.scale * sin(my_group.x)
     larch> plot(my_group.x, my_group.y, title=my_group.title)

The Group ``my_group`` holds data for ``x``, ``y``, and ``title``.  Here,
the ``range()`` function gives an array of 11 elements ([0, 1, 2, ..., 10])
that will be held by ``my_group.x``.  You can see the contents of a group
with the :func:`show` function::

    larch> show(my_group)
    == Group 0x6e15970: 4 symbols ==
      scale: 10.2
      t: 'group 1'
      x: array<shape=(11,), type=dtype('int32')>
      y: array<shape=(11,), type=dtype('float64')>

which shows that this group has 4 components, and lists the components.
As the ``x`` and ``y`` members hold array, the size and datatype of the
array is shown.  Doing::

    larch> print my_group.y
    [  0.           8.58300405   9.27483375   1.43942408  -7.71938545
      -9.7810276   -2.85003808   6.70126331  10.09145412   4.20360855
      -5.54901533]

will show the array elements.  The :func:`plot` function will show a graph
of y(x).

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

For XAFS analysis in particular, Larch is able to do essentially all the data processing
and analysis steps that Ifeffit can do, including:

   * pre-edge background subtraction and normalization
   * background subtraction for isolating chi(k)
   * XAFS Fourier transforms
   * reading and manipulating Feff Path files
   * fitting Feff Paths to XAFS data
   * general-purpose minimization and curve-fitting.
