
Larch:  Data Analysis for X-ray Spectroscopies and More
======================================

.. image:: https://travis-ci.org/xraypy/xraylarch.png
   :target: https://travis-ci.org/xraypy/xraylarch

.. _scipy: http://scipy.org/
.. _numpy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/
.. _h5py: http://code.google.com/p/h5py/

* Documentation: http://xraypy.github.io/xraylarch
* Code: http://github.com/xraypy/xraylarch


Larch is an open-source analysis and visualization toolkit and library for
processing scientific data.  The primary emphasis is on X-ray spectroscopic
and scattering data, especially that collected at modern synchrotrons and
X-ray sources.  But, Larch also provides many general-purpose processing,
analysis, and visualization tools for dealing with arrays of scientific
data.  

Larch is written in Python, making heavy use of the wonderful `numpy`_,
`scipy`_, `h5py`_, and `matplotlib`_ libraries.  For interactive and batch
processing, Larch provides a Python-like and Python-derived language (a
*macro language*, or *domain specific language*) that is intended to be
very easy to use for novices while also being complete enough for advanced
data processing and analysis.  In addition, Larch can be used as a Python
library, used within Python scripts, and extended using Python.  Finally,
Larch can be run as a service, interacting with other processes via
XML-RPC. 

Larch: An X-ray Analysis Toolkit with Plugins
===============================

Larch has several related target application areas, including:

  * XAFS analysis, becoming version 2 of the Ifeffit Package.
  * Visualizing and analyzing micro-X-ray fluorescence maps.
  * Quantitative X-ray fluorescence analysis.
  * X-ray standing waves and surface scattering analysis.
  * Data collection software for synchrotron data.

The initial goal was to rewrite the older Ifeffit XAFS Analysis package,
and this is largely complete.  Other application areas are nearly complete
or in early stages of development.

All the scientific domain-specific code is exposed through a plugin
mechanism.  Plugins are written in Python (which can use compiled code and
3rd party Python libraries), and are loaded from Python source at runtime,
making development very easy.  Plugins do not need to know much about the
internals of Larch.  Adding a small amount of  Larch-awareness to a Plugin
can make functions defined in Plugins work very easily with Larch's
interactive macro language.

Larch: A macro language for scientific programming 
======================================

Larch provides a dialect of Python for interactive use.  The intention is
to provide a very easy and complete macro language for data processing.
By building Larch with Python, Larch has many important similarities to
Python:

1.  All variables in Larch are real Python objects.

2.  Existing Python libraries can be imported and used from Larch.

3.  Syntax for lists, dictionaries, array slicing, and so on are identical to python.

4. Control flow syntax (if, while, for, try) are nearly identical to Python (see below).
    
  
The Larch macro language differs from Python in a few significant ways:

1. Larch does not use indentation level to define blocks of  code. Rather,  a block is ended with one of::

            if X:        
               do_something()
            endif
            if Y: 
               do_another_thing()
           #endif

and similarly   for/endfor, while/endwhile, def/enddef, and   try/endtry.

Properly indenting and using the '#end' version allows code to be both  
valid larch and python, and is strongly encouraged.

2.  "Command" syntax -- not requiring parentheses for function calls --   is 
supported in many cases.  If the first word of an expression typed at the
command prompt is a word that is a valid symbol name (and not a reserved
word) and the second word that is either a valid name or a number, and if
the line does not end with a ')', the first word is taken as a function
name and parentheses are added, so that::

           command arg1, arg2   

is converted to ``command(arg1, arg2)`` and so on.

3.  Larch has a nested namespace and a deeper level of name resolution.
This is more complex than Python's simple and elegant model, but allows
more functionality and data to be readily available at an interactive
prompt.

4.  While the Larch macro language is a com a Larch does not support many
important Python constructs.  These include

       *  ``class``     -- creating a new object class
       *  ``lambda``  -- anonymous functions.
       *   generators, ``yield`` -- deferred generation of sequences.
       *   decorators   --  function modifiers
            
For the sensitive Python-lovers, please note that I am not saying that I
think these changes from Python are in anyway shortcomings of Python that
are being fixed by Larch.  Rather, the changes (and omissions) are to make
Larch a simple scientific macro language.  The fact that the macro language
is close to Python is a strong benefit, but it is still a domain-specific
language. 

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



