=======================================================
Tutorial: Writing Functions or Procedures
=======================================================

Any moderately complex script will eventually include calcluations that
need to be repeated.  The preferred way to do this is write your own
function or **procedure**, which can be called exactly as the built-in
functions.  For maximum clarity in this section we tend use the word
**procedure** for a function written in Larch, leaving **function** to
imply a Python function.  In fact, as we will see, there is very little
difference in practical use, and the rest of the documentation will be more
lax about referring to functions written in Larch as functions.

Once you're ready to write procedures, you'll almost certainly want to read
about running Larch scripts and modules in the next section of this tutorial.


Def statement
=================

To define a procedure, you use the **def** statement, and write a block of
code.  This looks much like the **if**, **for**, and **while** blocks
discussed earlier. A simple example would be::

    def sayhello():
        print 'hello!'
    enddef

With this definition, one can then run this procedure as you would run any
other built-in function, by writing::

    larch> sayhello()
    hello!

Of course, you can write procedures that take input arguments, such as::

    def safe_sqrt(x):
      if x > 0:
         print sqrt(x)
      else:
         print 'Did you want sqrt(%f) = %f?' % (-x,  sqrt(-x))
      endif
    enddef

Here *x* will hold whatever value is passed to it, so that::

    larch> safe_sqrt(4)
    2.0
    larch> safe_sqrt(-9)
    Did you want sqrt(9.000000) = 3.000000?


Of course, you will most often want a procedure to return a value.  This is
done with the **return** statement.  A **return** statement can be put
anywhere in a procedure definition.  When encountered, it will cause the
procedure to immediately exist, passing back any indicated value(s).  If no
**return** statement is given in a procedure, it will return ``None`` when
the procedure has fully executed.  An example::

    def safe_sqrt(x):
      if x > 0:
         return sqrt(x)
      else:
         return sqrt(-x)
      endif
    enddef

which can now be used as::

    larch> print safe_sqrt(4)
    2.0
    larch> x = safe_sqrt(-10)
    larch> print x
    3.16227766017

**return** can take multiple arguments, separated by a comma, which is to
say a **tuple**.  As an example::

    larch> def sum_diff(x, y):
    .....>    return x + y, x-y
    .....> enddef
    larch> print sum_diff(3., 4.)
    (7.0, -1.0)

This is discussed in more detail below.

The formal definition of a procedure looks like::

   def <procedure_name>(<arguments>):
       <block of statements>
   enddef

..  _tut-namespaces-label:

Namespace and "Scope" inside a Procedure
=================================================

While inside a procedure, and important consideration is "what variables
does this procedure have access to?".  In fact, the question can be
extended beyond procedures and functions to ask "what variables are
available at any time during a Larch session or when a script is running?".
This is known as **scoping**, and there is the notion of a **namespace** in
which all the available variables exist.

In Larch (to be clear, the rules here are slightly different than Python),
every named object (variable, function, etc) exists in a Group.  The
top-level group is `_main`, and all groups descend from it.  There is a
special list ``_sys.searchGroupObjects`` holding the list of Groups to be
searched for names.  There are several related variables listed in
:ref:`Table of Namespace-related Variables <namespace_table>`.

.. index:: _sys variables,  namespace-related variables
.. _namespace_table:

   Table of Namespace-related Variables

   Listed are the name of variables holding information used in the looking
   up of symbol names.

    ========================= =============================================
     *variable*                  *content*
    ========================= =============================================
     _sys.paramGroup           group of Parameters, as for a fit
     _sys.localGroup           group for variables passed into or created
                               in a procedure
     _sys.moduleGroup          group for module-wide variables -- those
                               definied in the same file as the current procedure.
     _sys.searchGroupObjects   current list (ordered) of actual groups searched
     _sys.searchGroups         current list of actual group names searched
     _sys.core_groups          ('_main', '_sys', '_builtin', '_math')
    ========================= =============================================


`_sys.searchGroups` and `_sys.searchGroupObjects` are always kept in sync,
and always contain the groups named in `_sys.core_groups`.  In addition,
they always contain (in order, if not ``None``), `_sys.localGroup`,
`_sys.paramGroup`, `_sys.moduleGroup`.  If not inside a function or module,
`_sys.localGroup` and `_sys.moduleGroup` are set to `_main`.


Thus, inside a procedure, the way names are looked up are:

1. First, variables defined in the current *parameter group*.  This is
meant to be used exclusively for fitting procedures. Only during a fit
should `_sys.paramGroup` have any value other than ``None``.

2. Second, variables defined in the procedure definition (command-line
arguments and created inside the procedure.

3. Third, variable declared at the top-level in the same module in which the
procedure is  defined.

4. Finaly, by going through the list of other search groups, including all
the groups in `_sys.core_groups`, and probably several others brought in
from some plug-in.



In principle, you can alter some of these variables in the `_sys` group.
This is a really bad idea, and you should avoid doing it at all costs.



The return statement, and multiple Return values
======================================================

As seen above, the **return** statement will exit a procedure, and send
back a value to the calling code.    The return value can be either a
single value or a tuple of values, which gives a convenient way to return
multiple values from a single procedure.  Thus::



    larch> def my_divmod(x, y):
    .....>    return (x // y, x % y)  # note use of // for integer division!
    .....> enddef
    larch> print my_divmod(100, 7)
    14, 2

But be careful when assigning the return value to variable(s).  You can
do::

    larch> xdiv, xmod = my_divmod(100, 7)
    larch> print xdiv
    14

or::

    larch> result = my_divmod(100, 7)
    larch> print result[0], result[1]
    14, 2

Because a return value from a procedure can hold many values, it is best to
be careful when writing a procedure that you document what the return value
is, and when using a procedure that you're getting the correct number of
values.

Keyword arguments
=======================

For the procedures defined so far, the arguments have been both required
and in a fixed order.  Sometimes, you'll want to give a procedure optional
arguments, and perhaps allow some flexibility in the order of the
arguments.  Larch allows this with **keyword** arguments.
Keyword arguments offer distinct advantages over positional arguments
in that they have default values, and can be given in any order.
In a procedure definition, you add an argument name with a default value,  like this::

    def xlog(a, base=e):
        """return log(a) with base = base (default=e=2.71828...)
        """
         if base > 1:
            return log(a) /log(base)
        else:
            print 'cannot calculate log base %f' % base
        endif
    enddef

Unless passed in, the value of *base* will take the default value of *e*.
This can then be used as::

    larch> xlog(16)
    2.7725887222397811
    larch> xlog(16, base=10)
    1.2041199826559246
    larch> xlog(16, base=2)
    4.0

You can supply many keyword arguments -- they can be given in any order,
but they must all come *after* the positional arguments.

A procedure can be written to take an unspecified number of positional and
keyword parameters, using a special syntax for unspecified positional
arguments and for unspecified keyword arguments.  To use unspecified
positional arguments, a procedure definition takes an argument preceded by
a '*' after all the named positional arguments, like this::

    def addall(a, b, *args):
        """add all (at least 2!!) arguments given"""
 	out = a + b
        for c in args:
            out = out + c
        endfor
        return out
    enddef

Here, the **'*args'** arguments means to use the variable 'args' to hold
any number of positional arguments beyond those explicitly given.  Inside
the procedure, a tuple named 'args' will hold any positional parameters
included in the call to 'addall' past the first two (which will be held by
'a' and 'b').  Thus, this procedure can be used as::

    larch> addall(2, 3)         # args = ()
    5
    larch> addall(2, 3, 5, 7)   # args = (5, 7)
    17

To add support for unspecified keyword parameters, one adds a named
argument to the procedure definition preceded by two asterisks:
**'**keywords'**.  For example::

    def operate(a, b, **options):
        """perform operation on a and b"""
        debug = options.get('debug', True)
        verbose = options.get('verbose', False)
	op  = options.get('op', 'add')
        if verbose:
           print 'op == %s ' % op
        endif
        if op == 'add':
            return a + b
       elif op == 'sub':
            return a - b
       elif op == 'mul':
            return a * b
       elif op == 'div':
            return a / b
       else:
            if debug:  print 'unsupported operation!'
       endif
    enddef

As you may have figured out, inside the procedure, 'options' will hold a
dictionary of keyword names/values passed into it.  With this (perhaps
contrived) definition, you can call 'operate' many ways to change its
behavior::

    larch> operate(3, 2, op='add')
    5
    larch> operate(3, 2, op='add', verbose=True)
    op == add
    5
    larch> operate(3, 2, op='mul', verbose=True)
    op == mul
    6
    larch> operate(3, 2, op='xxx', verbose=True)
    op == xxx
    unsupported operation!
    larch> operate(3, 2, op='xxx', debug=False)
    op == xxx

As with the **'*args'**, the **'**options'** in the procedure definition must
appear after any named keyword parameters, and will not include the named
keyword parameters.

Documentation Strings
=======================

It is generally a good idea to document your procedures so that you and
others can read what it is meant to do and how to use it.  Larch has a
built-in mechanism for supporting procedure documentaion.  If the first
statement in a procedure is a **bare string** (that is, a string that is
not assigned to a variable), then this will be used as the procedure
documentation.  You can use triple-quoted strings for multi-line
documentation strings.  This doc string will be used by the built-in help
mechanism, or when viewing details of the procedure.  For example::

    def safe_sqrt(x):
      """safe sqrt function:
     returns sqrt(abs(x))
     """
     return sqrt(abs(x))
    enddef


With this definition::

    larch> help(safe_sqrt)
      safe sqrt function:
         returns sqrt(abs(x))

