============================
Larch Reference
============================

This chapter describes further details of Larch language, intending to act
as a reference manual.  As discussed elsewhere, the single most important
fact about Larch is that it implemented with and closely related to Python.
Of course, Python is very well documented, and much of the Python
documentation can be applied to Larch.  Thus the discussion here focuses on
the differences betwen Larch and Python, and on the functionality unique to
Larch.

Much of the discussion here will expect a familiarity with programming and
a willingness to consult the on-line Python documentation when necessary.

Needed here:

  1. buit in functions
  2. namespace layout (_main, _sys, _math, _builtin,...)



.. toctree::
   :maxdepth: 2

   developers

Overview
===================

Larch requires Python version 2.6 or higher.  Support for Python 3.X is
partial, in that the core of Larch does work but is not particularly
well-tested.  Importantly, wxPython, the principle GUI toolkit used by
Larch, has not yet been ported to Python 3.X, and so no graphical or
plotting capabilities are available yet for Larch using Python 3.

