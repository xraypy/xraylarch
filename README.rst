Larch:  Data Analysis for X-ray Spectroscopies and More
====================================================

.. image:: https://travis-ci.org/xraypy/xraylarch.png
   :target: https://travis-ci.org/xraypy/xraylarch

.. image:: https://ci.appveyor.com/api/projects/status/weagcmcq6lfclit9
   :target: https://ci.appveyor.com/project/newville/xraylarch

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/
.. _h5py: http://code.google.com/p/h5py/

* Documentation: http://xraypy.github.io/xraylarch
* Code: http://github.com/xraypy/xraylarch

Larch is an open-source toolkit for analyzing X-ray spectroscopy and
scattering data as collected at modern synchrotrons X-ray sources. Larch
provides general-purpose tools for visualization and analysis of numerical
scientific data, and state-of-the-art tools for working with X-ray
absorption and fluorescence spectroscopy data.  These tools include a few
graphical user interfaces for doing the most common visualization and
analysis tasks and a comprehensive library of lower level functionality for
more complicated analysis and for scripting.

Larch is written in Python and makes heavy use of the wonderful `numpy`_,
`scipy`_, `h5py`_, and `matplotlib`_ libraries.  For interactive and batch
processing, Larch can be used either as a Python library or using a
Python-like and Python-derived language (a *macro language*, or *domain
specific language*) that is intended to be very easy to use for novices
while also being complete enough for advanced data processing and analysis.
Finally, Larch can also be run as a service, interacting with other
processes via XML-RPC.

Larch: An X-ray Analysis Toolkit for Python
===========================================

Larch has several related target application areas, including:

  * XAFS analysis, replacing the unsupported Ifeffit Package.
  * Visualizing and analyzing micro-X-ray fluorescence and diffraction maps.
  * Quantitative X-ray fluorescence analysis.
  * Data collection software for synchrotron data.

The initial goal for Larch was to rewrite the older Ifeffit XAFS Analysis
package, and to provide tools for X-ray fluorescence mapping at X-ray
microprobes.  With this initial goal essentially complete, we are now able
to work on improving GUI applications for XAS and XRF mapping, and add more
capabilities for XAFS and XRF analysis.  In addition, other application
areas such as X-ray diffraction mapping and robust X-ray fluorescence
analysis are now in development.



Larch: A macro language for scientific programming
===========================================

While Larch can be used as a Python library, it also provides a dialect of
Python for interactive use at a command-line interface.  The intention is
to provide a very easy and complete macro language for data processing.  By
building Larch with Python, the Larch macro language has many important
similarities to Python:

1. All variables in Larch are real Python objects.
2. Existing Python libraries can be imported and used from Larch.
3. Syntax for lists, dictionaries, array slicing, and so on are identical to python.
4. Control flow syntax (if, while, for, try) are nearly identical to Python (see below).

The Larch macro language differs from Python in a few significant ways:

1. Larch does not use indentation level to define blocks of  code. Rather,  a block is ended with one of::

            if X:
               do_something()
            endif
            if Y:
               do_another_thing()
           #endif

and similarly  for/endfor, while/endwhile, def/enddef, and   try/endtry.

Properly indenting and using the '#end' version allows code to be both
valid larch and python, and is strongly encouraged.

2.  Larch has a nested namespace and a deeper level of name resolution.
This is more complex than Python's simple and elegant model, but allows
more functionality and data to be readily available at an interactive
prompt.

2.  "Command" syntax -- not requiring parentheses for function calls --   is
supported in many cases.  If the first word of an expression typed at the
command prompt is a word that is a valid symbol name (and not a reserved
word) and the second word that is either a valid name or a number, and if
the line does not end with a ')', the first word is taken as a function
name and parentheses are added, so that::

           command arg1, arg2

is converted to ``command(arg1, arg2)`` and so on.

4.  While the Larch macro language provides a complete enough language for
complex scripting of data anlysis work, the Larch macro language does not
include several important Python constructs.  These include

       *  ``class``     -- creating a new object class
       *  ``lambda``  -- anonymous functions.
       *   generators, ``yield`` -- deferred generation of sequences.
       *   decorators   --  function modifiers

For Python programmers, please note that the Larch macro language is
deliberately limited to make a simple yet complete enough macro language
for processing scientific data.

The implementation of the Larch macro language turns out to be rather
simple.  The input Larch program text is converted to valid python code,
and then parsed into Python's own Abstract Syntax Tree (AST).  This AST
representation is then interpreted directly, using a custom symbol table
for name lookup and resolution.  This implementation gives several
benefits:

1.  the intermediate python code can be saved so that code validation and  translation of larch to python are now trivial

2.  the parsed AST tree is guaranteed (at least as far as python itself is) to be correct.

3.  Interpreting the AST tree is very simple, including all loop and control-flow code, and the resulting compiler is very simpler and powerful.

In addition, the symbol table is simplified so that a symbolTable contains
python objects and Groups (simple containers for other objects and
Groups). Namespaces are built simply using attributes of the Group class.
That is, attribute lookup is heavily used, and symbols just python objects.
