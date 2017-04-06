.. _programming_chapter:

============================
Programming with Larch
============================

This chapter describes some of the key concepts for programming with Larch.
Larch is a fairly complete programming language for data analysis, but it
is also easy to extend Larch with new functionality.  There are two
distinct ways to do this.  First, ``modules`` are files of Larch or Python
code that can be imported and used from Larch.  These are primarily
intended to organize programming text, and to allow re-usable code.
Second, ``plugins`` are Python modules that have special methods to export
the functionality to Larch.  Whereas modules run from within the Larch
interpreter, plugins are run in Python, and can closely interact with a
running Larch interpreter to add or manipulate the existing session.
Plugins should be the main approach for extending the capabilities of
Larch, and indeed essentially all the real scientific code in Larch is
implemented as plugins.  As an important note, the functions defined in the
Larch can be accessed from Python, without relying on the syntax of the
Larch language at all.

The reader here is assumed to be familiar with computer programming, and to
have some exposure to working with Larch and/or Python, at least from the
:ref:`Tutorial <tutorial_chapter>` (Chapter :ref:`tutorial_chapter`).
While the present chapter is aimed primarily at developers and advanced
users, Larch (and Python) makes such developments easy enough that neither
extensive effort nor training are required to begin writing programs with
Larch.

.. toctree::
   :maxdepth: 2

   notpython
   modules
   plugins
   frompython
