==================================================
Larch: Motivation and Overview
==================================================

Larch is a scientific data processing language.  Though having pretty
general capabilities, it has been developed especially for processing and
analyziing x-ray spectroscopic and scattering data collected at modern
synchrotrons and x-ray sources.  Thus, Larch has several related target
application areas, including XAFS, XRF, and X-ray standing waves.  The
initial movitation for Larch was to replace the Ifeffit package for XAFS
analysis, with the the ability to add XRF capabilites and to use it as a
macro language for data collection and initial data processing and
visualization were quickly added to the list of goals.

Larch gives a simple command-line interface (a Read-Eval-Print Loop), but
can also be scripted in "batch mode".  GUIs can be built upon Larch by
simply generating the commands, making it easy to separate the layout from
the actual processing steps, so that the processing steps might be recorded
and used to make a "batch script".  In addition you can use Larch with
remote-procedure calls, so that it can be run as a service, and called from
a variety of languages and from different machines.


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

In a sense, Larch is a dialect of Python.  Thus an understanding Larch and
Python are close to one another.  This in itself can be seen as an
advantage -- Python is a popular, open-source, language that any programmer
can easily learn.  Books and web documentation about Python are plentiful.
If you known Python, Larch will be very easy to use, and vice versa.


Design Principles, Key Concepts
====================================

Since Larch is intended for processing scientific data, organization of
data is a key consideration.  The main feature that Larch uses to help the
user with organizing data is **Group**.  This is simply a container into
which any sort of data can be placed, including other Groups.  This allows
nested structures of data that can be accessed and manipulated easily via
attributes, as with::

     larch> my_group = group(x = range(11), scale=10.2, title='group 1')
     larch> my_group.y = my_group.x*my_group.x
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
      y: array<shape=(11,), type=dtype('int32')>

which shows that this group has 4 components, and lists the components.
As the ``x`` and ``y`` members hold array, the size and datatype of the
array is shown.  Doing::

    larch> print my.group.y
    [  0   1   4   9  16  25  36  49  64  81 100]

will show the array elements.   The :func:`plot` function will show a graph
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


For XAFS analysis in particular, Larch is able to do most data processing
and analysis steps needed, including:

   * pre-edge background subtraction and normalization
   * background subtraction for isolating chi(k)
   * XAFS Fourier transforms
   * reading and manipulating Feff Path files
   * fitting Feff Paths to XAFS data
   * general-purpose minimization and curve-fitting.



