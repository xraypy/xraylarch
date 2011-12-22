============================
Larch for Developers
============================

This chapter describes details of Larch language for developers and
programmers wanting to extend Larch.  This document will assume you have
some familiarity with Python.

Larch vs Python
==================

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
  

These are discussed in more detail below


Code Blocks with 'end*'
~~~~~~~~~~~~~~~~~~~~~~~~~
Larch does not use significant whitespace to define blocks.  There, that
was easy.   Instead, Larch uses "end blocks", of the form::

   if test:
      <block>
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

Larch can import modules written in Larch (with a '.lar' extension) or
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

In addition, all functions to be added to Larch need to be *registered*,
by defining a function call :func:`registerLarchPlugin` that returns a
tuple containing the name of the group containing the added functions, and
a dictionary of Larch symbol names and functions.   Thus a simply plugin
module would look like::

    def _f1(x, y, larch=None):
        if larch is None: return
	group = larch.symtable.create_group(name='created by f1')
        setattr(group, 'x', x)
        setattr(group, 'y', y)
	return group

    def registerLarchPlugin():
        return ('mymod', {'f1': _f1})

If this is placed in a file called 'myplugin.py' in the larch plugins
folder (say, $HOME/.larch/plugins/ on Unix), then::

   larch> add_plugin('myplugin')

will add a top-level group 'mymod' with an 'f1' function, so that::

   larch> g1 = mymod.f1(10, 'yes')
   larch> print g1
   <Group created by f1!>
   larch> print g1.x, g1.y
   (10, 'yes')

Of course the point is that you can do much more complicated work in the
plugin function.
