============================
Larch for Developers
============================

This chapter describes details of Larch language for developers and
programmers wanting to extend Larch.  This document will assume you have
some familiarity with Python.

.. _python_diffs_section:

Differences between Larch and Python
=============================================

Larch is very similar to Python but there are some very important
difffernces, especially for someone familiar with Python.  These
differences are not because we feel Python is somehow inadequate or
imperfect, but because Larch is a domain-specific-language.  It is really
something of an implementation detail that Larch's syntax is so close to
Python.   The principle differences with Python are:

  1. Using 'end*' instead of significant white-space for code blocks.
  2. Groups versus Modules
  3. Changing the lookup rules for symbol names
  4. Not implementing several python concepts, notably Class, and lambda.

Each of these is discussed in more detail below.

Some background and discussion of Larch implementation may help inform the
discussion below, and help describe many of the design decisions made in
Larch.  First and foremost, Larch is designed to be a domain-specific macro
language that makes heavy use of Python's wonderful tools for processing
scientific data.  Having a macro language that was similar to Python was
not the primary goal.  The first version of Larch actually had much weaker
correspondance to Python.  It turned out that the implementation was much
easier and more robust when using syntax close to Python.

When larch code is run, the text is first *translated into Python code* and
then parsed by Python's own  *ast* module which parses Python code into an
*abstract syntax tree* that is much more convenient for a machine to
execute.   As a brief description of what this module does, the statement::

    a*sin(2*b)+c

will be parsed and translated into something like::

   Add(Name('c'), Mult(Name('a'), Call(Name('sin'), Args([Mult(Num(2), Name('b'))]))))

Larch then walks through this tree, executing each Add, Mult, etc on its
arguments.  If you've ever done any text processing or thought about how a
compiler works, you'll see that having this translation step done by proven
tools is a huge benefit.  For one thing, using Python's own interpreter
means that Larch simply does not having parsing errors -- any problem would
be translation of Larch code into Python, or in executing the compiled code
above.  This also makes the core code implementing Larch much easier (the
core functionality is fewer than 3000 lines of code).

Given this main implementation feature of Larch, you can probably see where
and how the differences with Python arise:

   * The Larch-to-Python translation step converts the 'end*' keywords into
     significant whitespace ('commenting out 'endif' etc if needed).
   * The lookup for symbols in **Name('c')** is done at run-time, allowing
     changes from the standard Python name lookup rules.
   * Unimplemented Python constructs (class, lambda, etc) are parsed, but

You can also see that Python's syntax is followed very closely, so that the
translation from Larch-to-Python is minimal.


.. _code-block-ends:

Code Block Ends
~~~~~~~~~~~~~~~~~~~~~~~

Larch does not use significant whitespace to define blocks.  There, that
was easy.   Instead, Larch uses "end blocks", of the form::

   if test:
      <block of statements>
   endif

Each of the Keywords *if*, *while*, *for*, *def*, and *try* must be matched
with a corresponding 'end' keyword: *endif*, *endwhile*, *endfor*,
*enddef*, and *endtry*.  You do not need an *endelse*, *endelif*,
*endexcept*, etc, as this is not ambiguous.

As a special note, you can place a '#' in front of 'end'. Note that this
means exactly 1 '#' and exactly in front of 'end', so that '#endif' is
allowed but not '####endif' or '# endfor'.  This allows you to follow
Python's indenting rules and write code that is valid Larch and valid
Python, which can be useful in translating code.

Groups vs Modules
~~~~~~~~~~~~~~~~~~~~~~~~~

This is at least partly a semantic distinction.  Larch organizes data and
code into Groups -- simple containers that hold data, functions, and other
groups.  These are implemented as a simple, empty class that is part of the
symbol table.


Symbol Lookup Rules
~~~~~~~~~~~~~~~~~~~~~~~~~

The name lookups in Python are quite straightforward and strict: local,
module, global.  They are also fairly focused on *code* rather than *data*.
There is a tendency with Python scripts to use something like::

    from numpy import *

in quick-and-dirty scripts, though many experienced developers will tell
you to avoid this like the plague.

In Larch, there is a list of Groups
namespaces that are




Unimplemented features
~~~~~~~~~~~~~~~~~~~~~~~~~

A domain-specific-language like Larch does not need to be as full-featured
as Python, so we left a few things out.  These include (this may not be an
exhaustive list):

    * eval -- Larch *is* sort of a Python eval
    * lambda
    * class
    * global
    * generators, yield
    * decorators



Modules
==================

Larch can import modules either written in Larch (with a '.lar' extension) or
Python (with a '.py' extension).  When importing a Python module, the full
set of Python objects is imported as a module, which looks and acts exactly
like a Group.

Plugins
================

Plugins are a powerful feature of Larch that allow it to be easily extended
without the requiring detailed knowledge of all of Larch's internals.  A
plugin is a specially written Python module that is meant to add
functionality to Larch at run-time.  Generally speaking, plugins will be
python modules which define new or customized versions of functions to
create or manipulate Groups.

Plugins need access to Larch's symbol table and need to tell Larch how to
use them.  To do this, each function to be added to Larch in a plugin
module needs a `larch` keyword argument, which will be used to pass in the
instance of the current larch interpreter.  Normally, you will only need
the `symtable` attribute of the `larch` variable, which is the symbol table
used.

In addition, all functions to be added to Larch need to be *registered*, by
defining a function call :func:`registerLarchPlugin` that returns a tuple
containing the name of the group containing the added functions, and a
dictionary of Larch symbol names and functions.  A simple plugin module
would look like::

    def _f1(x, y, larch=None):  # Note:  larch instance passed in with keyword
        if larch is None: return
	group = larch.symtable.create_group(name='created by f1')

        setattr(group, 'x', x) # add symbols by "setting attributes"
        setattr(group, 'y', y)

	return group

    def registerLarchPlugin(): # must have a function with this name!
        return ('mymod', {'f1': _f1})

This is a fairly trivial example, simply putting data into a Group.  Of
course, the main point of a plugin is that you can do much more complicated
work inside the function.

If this is placed in a file called 'myplugin.py' in the larch plugins
folder (either $HOME/.larch/plugins/ or /usr/local/share/larch/plugins on
Unix, or C:\\Users\\ME\\larch\\plugins or C:\\Program Files\\larch\\plugins on
Windows), then::

   larch> add_plugin('myplugin')

will add a top-level group 'mymod' with an 'f1' function, so that::

   larch> g1 = mymod.f1(10, 'yes')
   larch> print g1
   <Group created by f1!>
   larch> print g1.x, g1.y
   (10, 'yes')

For commonly used plugins, the :func:`add_plugin` call can be added to your
startup script.
