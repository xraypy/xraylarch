============================
Language Reference
============================

This chapter describes further details of Larch language.  An important
point for the discussion here is the fact that Larch is implemented using
Python.  In addition to being implemented in Python, the Larch syntax is 
heavily dependent on Python, and all the data in Larch are Python objects.
In addition, Python is the principle way to extend Larch programs.

Of course, Python is well-documented and much of the Python documentation
can be used for Larch.  Thus the discussion here focusses on the
differences with Python,


Language
==================

Larch requires Python version 2.6 or higher.  Support for Python 3.X is
partial, in that the core of Larch does work but is not well-tested, and
