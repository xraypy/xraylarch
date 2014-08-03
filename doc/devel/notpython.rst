
.. _python_diffs_section:

Differences between Larch and Python
=============================================

Larch is based on and very similar to Python, but there are some very
important differences that need to be noted, especially for those familiar
with Python.  These differences are not here because we feel Python is
somehow inadequate or imperfect, but because Larch is intended as a
domain-specific-language.  The fact that Larch's syntax is so close to
Python is really something of an implementation detail, so straying from
the "purity" of Python shouldn't be seen as an allegation of imperfection
on either Larch's or Python's parts -- they have different goals.  The
principle differences with Python are:

  1. Using 'end*' instead of significant white-space for code blocks.
  2. Groups versus Modules
  3. Changing the lookup rules for finding symbol names
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

Unlike Python, Larch does not use significant whitespace to define blocks.
There, that was easy.  Instead, Larch uses "end blocks", of the form::

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
Python, which can be useful in translating code::

    for i in range(5)
        print(i, i/2.0)
    #endfor

This code is both valid Larch and valid Python.


Groups vs Modules
~~~~~~~~~~~~~~~~~~~~~~~~~

This is at least partly a semantic distinction.  Larch organizes data and
code into Groups -- simple containers that hold data, functions, and other
groups.  These are implemented as a simple, empty class that is part of the
symbol table.


Symbol Lookup Rules
~~~~~~~~~~~~~~~~~~~~~~~~~

Looking up symbol names is a key feature of any language.  Python and Larch
both allow *namespaces* in which symbols can be nested into a heirarchy,
using a syntax of **parent.child**, with a dot ('.') separating the
components of the name.   Such parent/child relationships for symbol names
are used for modules (files of code), and object attributes.   Thus, one
could have data objects named::

    cu_01.data.chi
    cu_02.path1.chi
    cu_03.model.chi

Where the name *chi* is used repeatedly, but with different (and multiple)
parents.  The issue of name lookups is how to know what (if any) to use if
*chi* is specified without its parents names.

In Python, name lookups are quite straightforward and strict: "*local,
module*". Here, *local* means "inside the current function or method" and
*module* means "inside the current module (file of code text)".  More
specifically, each function or method and each module is given its own
namespace, and symbols are looked for first in the local namespace, and
then in the module namespace.  These rules are focused on *code* rather
than *data*, and leads to having a lot of "import" statements at the top of
python modules.  For example, to access the :func:`sqrt` function from the
numpy module, one typically does one of these::

    import numpy

    def sqrt_array(npts=10):
        x = np.arange(npts)/2.
        return numpy.sqrt(x)

or::

    import numpy as np

    def sqrt_array(npts=10):
        x = np.arange(npts)/2.
        return np.sqrt(x)


In both of these examples the numpy module is brought into the *module*
level namespace, either named as 'numpy' or renamed to 'np' (a common
convention in scientific python code).  Inside the function
:func:`sqrt_array`, the names 'npts' and 'x' are in the local namespace --
they are not available outside the function.  The functions :func:`arange`
and :func:`sqrt` are taken from the module-level namespace, using the name
as defined in the import statement.  A third alternative would be to
import only the names 'sqrt' and 'arange' into the modules namespace::

    from numpy import sqrt, arange

    def sqrt_array(npts=10):
        x = arange(npts)/2.
        return sqrt(x)

For quick and dirty Python scripts, there is a tendency to use `import *`, as in::

    from numpy import *
    def sqrt_array(npts=10):
        x = arange(npts)/2.
        return sqrt(x)

which imports several hundred names into the module level namespace.  Many
experienced developers will tell you to avoid this like the plague.

In Larch, the general problem of how to lookup the names of objects
remains, but the rules are changed slightly.  Since Group objects are used
extensively throughout Larch exactly to provide namespaces as a way to
organize data, we might as well use them.  Instead of using `import *`,
Larch has a top-level group '_math' in which it stores several hundred
names of functions, mostly from the numpy module.  It also uses top-level
groups '_sys' and '_builtin', which hold non-mathematical builtin functions
and data, and many plugins will add top-level groups (such as '_plotter',
'_xafs', and '_xray').  So, to access :func:`sqrt` and :func:`arange` in
Larch, you could write `_math.sqrt()` and `_math.arange()`.  But you don't
have to.

Symbol lookup in Larch uses a list of Groups which is searched for names.
This list of groups is held in _sys.searchGroups (which holds the group
names) and _sys.searchGroupObjects (which holds references to the groups
themselves).  These will be changed as the program runs.  They can be
changed dynamically, this is not encouraged (and can lead to Larch not
being able to work well).

Larch also has 3 special variables that it uses to hold references to
groups that are *always* included in the search of names.  These are
'_sys.localGroup', which holds the group for a currently running function
while it is running; '_sys.moduleGroup', which holds the namespace for a
module associated with a currently running function; and '_sys.paramGroup',
which holds a group of Parameters used during fits (more on this, and why
it is needed here in the section on Parameters).



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


