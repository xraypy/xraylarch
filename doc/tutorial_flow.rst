=======================================================
Larch Tutorial: Conditional Execution and Flow Control
=======================================================


Two important needs for a full-featured language are the ability to run
different statements under different conditions, and to repeat certain
calculations.  These are generally called 'flow control', as these
statements control how the program will flow through the text of the
script.  Here we introduce a few new concepts, and discuss


Conditional Execution and Control-Flow
===========================================

So far all the stuff written to the Larch command line has been a single
line of text that is immediately run, either printing output to the
terminal or assigning a value to a variable.  These are both examples of
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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Here, two statements will be run if x is equal to 0 -- there is no
restriction on how many statements can be run.


An 'else' statement can be added to execute code if the test is False::

    if x == 0:
        print 'x is equal to 0!'
        x = 1
    else
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
~~~~~~~~~~~~~


Dealing With Errors
=======================
