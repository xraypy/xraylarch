.. _tutorial_chapter:

===============================
Larch Macro Language Tutorial
===============================

Larch provides both a Python programming library and Python-like
programming or macro language (which we'll call *Larch macro language*
here) for processing of scientific data.  You can use either of these to
interact with the X-ray analysis functions described throughout this
document.  If you already know Python or are interested in learning and
using Python, we definitely encourage to use the Python interface.

Here, the *Larch macro language* is described in some detail. This macro
language is a dialect of Python and is used for the Larch command-line
shell program.  This macro language is also used for communication between
the Larch server process and Athena/Artemis.  Perhaps most importantly, it
is also embedded in the Larch GUI applications so that you can "open the
Larch buffer" and use the Larch/Python functions on the data that has been
loaded into the GUI.  The *XAS Viewer* program really does all of its work
with the Larch buffer so that you can see the complete (if somewhat)
verbose list of commands and functions it is running when processing your
data.  You can take these commands as documentation of the processing steps
or use them as examples for writing batch processing scripts or more
complex programs.


This chapter describes the Larch language and using it for data processing.
An important goal of Larch is to make writing and modifying data analysis
scripts as simple as possible.  Although aimed at the novice programmer,
this tutorial does make a few assumptions about the readers experience with
scientific programming.  For example, the reader is expected to have a
technical background and some familiarity with using scientific data
analysis programs.  Some understanding of the concepts of how scientific
data is stored on computers and of the basics of programming will greatly
help the reader.

The Larch language is implemented in Python, and heavily based upon it.
Knowledge of Python will greatly simplify learning Larch, and vice versa.
This shared syntax is intentional, so that as you learn Larch, you will
also be learning Python, which can be used to extend Larch.  Alternatively,
knowledge of Python will make Larch easy to learn.  For further details on
Python, including tutorials, see the Python documentation at
http://python.org/

If you are familar with Python and want to use the `larch` module from
Python, skip ahead to :ref:`programming_chapter`.

Contents:

.. toctree::
   :maxdepth: 2

   start
   datatypes
   arrays
   flow
   errors
   procedures
   modules
   builtins
