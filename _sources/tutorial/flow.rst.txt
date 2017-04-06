=======================================================
Tutorial: Conditional Execution and Flow Control
=======================================================

Two important needs for a full-featured language are the ability to run
different statements under different conditions, and to repeat certain
calculations.  These are generally called 'flow control', as these
statements control how the program will flow through the text of the
script.  In the discussion here,  we will also introduce a few new concepts
and Larch statements.

So far in this tutorial, all the text written to the Larch command line has
been a single line of text that is immediately run, either printing output to
the terminal or assigning a value to a variable. These are both examples of
**statements**, which are the basic pieces pf text you send to the program.
So far we've seen three types of statements:

  1.  simple statements or expressions, such as::

         larch> 1+sqrt(3)

      or::

         larch> atomic_weight.keys()

      where we have an expression evaluated.  At the command line, these
      values are printed -- in a script they would not be printed.

  2.  print statements, such as::

         larch> print sqrt(3)

      where we explicitly command larch to print the evaluated
      expression -- this would print if run from a script.

  3.  assignment statements, such as::

         larch> x = sqrt(3)

      where we assign the name 'x' to hold the evaluated expression.

In fact, though these are the most common types of statements, there are
many more types of statements.  We will introduce a few more statement
types here, including compound statements that take up more than one line
of test.

Conditional Evaluation with if and else
==========================================

A fundamental need is to be able to execute some statement(s) when some
condition is met.  This is done with the **if** statement, an example of
which is::

    larch> if x == 0: print 'x is 0!'

Which will print 'x is 0!' if the value of *x* is equal to 0.  The `x == 0`
in this if statement is called the **test**.  A test is a Boolean
mathematical expression.  While most usual mathematical expressions use
operators such as '+', '-', a Boolean expression uses the operators listed
in :ref:`Table of Boolean Operators <tut_boolop_table>` to evaluate to a
value of ``True`` or ``False``.

A single-line if statement as above looks like this::
    if <test>:  statement

The 'if' and ':' are important, while '<test>' can be any Boolean
expression.  If the test evaluates to ``True``, the statement is executed.

If statements can execute multiple statements by putting the statements
into a "block of code"::

    if x == 0:
        print 'x is equal to 0!'
        x = 1
    endif

Which is to say that the multiple-line form of the if statement looks like
this::

    if <test>:
      <statements>
    endif

where '<statements>' here means a list of statements, and the 'endif' is
required (see :ref:`code-block-ends`). For the above, two statements will
be run if x is equal to 0 -- there is no restriction on how many statements
can be run.

An 'else' statement can be added to execute code if the test is False::

    if x == 0:
        print 'x is equal to 0!'
        x = 1
    else:
        print 'x is not 0'
    endif

Multiple tests can be chained together with the 'elif' (a contraction of
'else if')::

    if x == 0:
        print 'x is equal to 0!'
    elif x > 0:
        print 'x is positive'
    elif x > -10:
        print 'x is a small negative number'
    else:
        print 'x is negative'
    endif

Here the 'x > 0' test will be executed if the 'x == 0' test fails, and the
'x > -10' test will be tried if that fails.

.. _tut_boolop_table:

**Table of Boolean Operators**  The operators here all take the form
*right OP left* where OP is one of the operators below.  Note the
distinction between '==' and 'is'.  The former compares *values* while the
latter compares the identity of two objects.

  +-------------------+----------------------------+
  | boolean operator  | meaning                    |
  +===================+============================+
  |     ==            | has equal value            |
  +-------------------+----------------------------+
  |     !=            | has unequal value          |
  +-------------------+----------------------------+
  |     >             | has greater value          |
  +-------------------+----------------------------+
  |     >=            | has greater or equal value |
  +-------------------+----------------------------+
  |     <             | has smaller value          |
  +-------------------+----------------------------+
  |     <=            | has smaller or equal value |
  +-------------------+----------------------------+
  |     is            | is identical to            |
  +-------------------+----------------------------+
  |     not           | is not ``True``            |
  +-------------------+----------------------------+
  |     and           | both operands are ``True`` |
  +-------------------+----------------------------+
  |     or            | either operand is ``True`` |
  +-------------------+----------------------------+



Note that in Larch, as in Python, any value can be used as a test, not just
values that are ``True`` or ``False``.  As you might expect, for example,
the value 0 is treated as ``False``.  An empty string is also treated as
``False``, as is an empty list or dictionary.  Most other values are
interpreted as ``True``.

For loops
=============

It is often necessary to repeat a calculation multiple times.  A common
method of doing this is to use a **loop**, including using a loop counter
to iterate over some set of values.  In Larch, this is done with a **for
loop**.  For those familiar with other languages, a Larch for loop is a bit
different from a C for loop or Fortran do loop.  A for loop in Larch
iterates over an ordered set of values as from a list, tuple, or array, or
over the keys from a dictionary.   Thus a loop like this::

    for x in ('a', 'b', 'c'):
        print x
    endfor

will go through values 'a', 'b', and 'c',  assigning each value to *x*,
then printing the value of x, which will result in printing out::

    a
    b
    c

Similar to the *if* statement above, the for loop has the form::

   for <varlist> in <sequence>:
       <statements>
   endfor

Compared to a C for loop or Fortran do loop, the Larch for loop is much
more like a  *foreach* loop.  The common C / Fortran use case of interating
over a set of integers can be emulated using the builtin :func:`range`
function which generates a sequence of integers.   Thus::

   for i in range(5):
      print i, i/2.0
   endfor

will result in::

   0, 0.0
   1, 0.5
   2, 1.0
   3, 1.5
   4, 2.0

Note that the builtin :func:`range` function generates a sequence of
integers, and can take more than 1 argument to indicate a starting value
and step.  It is important to note that the sequence that is iterated order
does not be generated from the :func:`range` function, but can be any list,
array, or Python sequence.  Importantly, this includes strings(!) so that::

    for char in 'hello':  print char

will print::

    h
    e
    l
    l
    o

This can cause a common sort of error, in that you might expect some
variabe to hold a list of string values, but it actually holds a single
string.   Notice that::

    filelist = ('file1', 'file2')
    for fname in filelist:
        fh = open(fname)
        process_file(fh)
        fh.close()
    endfor

would act very differently if filelist was changed to 'file1'!

Multiple values can be assigned in each iteration of the for loop.  Thus,
iterating over a sequence of equal-length tuples, as in::

   for a, b in (('a', 1), ('b', 2), ('c', 3)):
       print a, b
   endfor

will print::

   a 1
   b 2
   c 3

This may seem to be mostly of curious interest, but can be extremely useful
especially when dealing with dictionaries or with arrays or lists of equal
length.   For a dictionary *d*, *d.items()* will return a list of
two-element tuples as above of key, value.  Thus::

   mydict = {'a':1, 'b':2, 'c':3, 'd':4}
   for key, val in mydict.items():
       print key, val
   endfor

will print (note that dictionaries do no preserve order, but the (key, val)
pairs match)::

   a 1
   c 3
   b 2
   d 4

The builtin :func:`zip` function is similarly useful, turning a sequence of
lists or arrays into a sequence of tuples of the corresponding elements of
the lists or arrays.  Thus::

   larch> a = range(10)
   larch> b = sin(a)
   larch> c = cos(a)
   larch> print zip(a, b, c)
   [(0, 0.0, 1.0), (1, 0.8414709848078965, 0.54030230586813977),
    (2, 0.90929742682568171, -0.41614683654714241), ....]

(Note that for arrays or lists of unequal length, :func:`zip` will return
tuples until any of its arguments runs out of elements).   Thus a for loop
can make use of the :func:`zip` function to iterate over multiple arrays::

   larch> a = arange(101)/10.0
   larch> print 'X   SIN(X)  SIN(Y)\n================\n'
   larch> for a, sval, cval in zip(a, sin(a), cos(a)):
   .....>     print '%.3f, %.5f, %.5f' % (a, sval, cval)
   .....> endfor

will print a table of sine and cosine values.

A final utility of note for loops is :func:`enumerate` which will return a
tuple of (index, value) for a sequence.   That is::

   larch> for i, a in enumerate('a', b', 'c'):
   .....>     print i, a
   .....> endfor

will print::

   0 a
   1 b
   2 c


It is sometimes useful to jump out of a for loop, or go onto the next value
in the sequence.   The *break* statement will exit a for loop immediately::

   for fname in filelist:
       status = get_status(fname)
       if status < 0:
          break
       endif
       more_processing(fname)
   endfor
   print 'processed up to i = ', i

may jump out of the loop before the sequence generated by 'range(10)' is
complete.  The variable 'i' will have the final used value.

To skipover an iteration of a loop but continue on, use the *continue*
statement::

   for fname in filelist:
       status = get_status(fname)
       if status < 0:
          continue
       endif
       more_processing(fname)
   endfor


While loops
=============

While a for loop generally walks through a pre-defined set of values, a
*while* loop executes as long as some test is ``True``.   The basic form
is::

   while <test>:
      <statements>
   endwhile

Here, the test works as for *if* -- it is a Boolean expression, evaluated at
each iteration of the loop. Generally, the expression will test something
that has been changed inside the loop (even if implicitly).   The classic
while loop increases a counter at each iteration::

   counter = 0
   while counter < 10:
      do_something(counter)
      counter = counter + 1
   endwhile

A while loop is easily turned into an infinite loop, simply by not
incrementing the counter.   Then again, the above loop would easily be
converted into a for loop, as the counter is incremented by a fixed amout at
each iteration.   A more realistic use would be::

   n = 1
   while n < 100:
      n = (n + 0.1) * n
      print n
   endwhile

An additional use for a while loop is to use an implicit or external
condition, such as time::

   now = time.time() # return the time in seconds since Unix epoch
   while time.time() - now < 15:   # That is 'for 15 seconds'
      do_someting()
   endwhile

The *break* and *continue* statements also work for while loops, just as they
do with for loops.   These can be used as ways to exit an other-wise infinite
while loop::

   while True:  # will never exit without break!
      answer = raw_input('guess my favorite color>')
      if answer == 'lime':
          break
      else:
          print 'Nope, try again'
      endif
   endwhile
