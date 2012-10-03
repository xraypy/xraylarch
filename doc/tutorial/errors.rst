=======================================================
Tutorial: Dealing With Errors
=======================================================

When an error exists in the syntax of your script, or an error happens when
running your script, an *Error* or *Exception* is generated, and the
execution of your script is stopped.

Syntax Errors
===============

Syntax errors result from incomplete or ill-formed larch syntax.  For
example::

    larch> x = 3 +
    SyntaxError: invalid syntax
    x = 3 +

        x = 3  +

This indicates that the Larch interpreter could not understand the meaning
of the statement 'x = 3 +', because it excepts a value after the '+'.
Syntax errors are spotted and raised before the interpreter tries to
evaluate the expression.  That is because Larch first fully parses any
statements (or block of statements if you're entering multiple statements
or loading a script from a file) into a partially compiled, executable form
before executing.  Because of this two-step approach (first parse to intermediate
form, then execute that intermediate form), syntax errors are sometimes
referred to as a parsing errors.


Exceptions
=================

Even if the syntax of your script is correct, the logic might not be.  In addition,
even if the logic is correct for most cases, it might not be correct for
all.  For example, certain values might cause an error run time::

   larch> n = 1
   larch> print 4.0 / ( n - 1)
   ZeroDivisionError('float division')
   <StdInput>
       print 4.0/(n-1)
             ^^^

which is saying that you can't divide by 0.  This is known as a **Runtime
Exception**.  It might indicate a programming error, for example that you
didn't test if the denominator was 0 before doing the division.

Larch (as inherited from Python) has many different types of exceptions, so
that dividing by zero, as above, is detected as a different exception from,
say, trying to open a file that doesn't exist::

    larch> fh = open('foo', 'r')
    Error running <built-in function open>
    IOError(2, 'No such file or directory')
    <StdInput>
        fh = open('foo', 'r')
             ^^^

or trying to add an integer and a string together::

    larch> 4 + 'a'
    TypeError("unsupported operand type(s) for +: 'int' and 'str'")
    <StdInput>
        4 + 'a'

Though they are called exceptions, such problems are fairly common when
developing programs or writing scripts.  Having a built-in way to test for
and handle different kinds of exceptions is an important part of many
modern computer languages, and Larch has this capability with
its **try** and **except** statements.


Try and Except
==================

The **try** statement will execute a block of code and look for certain
types of exceptions.  One or more **except** statements can be added to
specify blocks of code to execute if the specified exception occurs.
As a simple example::

    try:
        x = a/b
    except ZeroDivisionError:
        print 'saw a divide by zero!
        x = 0
    endtry

If b is not 0, x is set to the value of a/b.  If b is 0, executing *x =
a/b* will cause a ZeroDivisionError (as we saw above), so the block with
the print statement and setting x to 0 will be executed.  In either of
these cases (no exception, or a handled exception), execution will continue
as normal.  If a different problem occurs -- an "unhandled exception" --
such as the case if *a* holds a string value with *b* holds an integer, then
execution will stop and the corresponding exception will be raised.

There can be several **except** statements for each **try** statement,
to check for multiple types of problems.  These will be checked in order.  For example::

    try:
        x = a/b
    except ZeroDivisionError:
        print 'saw a divide by zero!
        x = 0
    except TypeError:
        print "a and b are of different types -- can't divide"
    endtry
    <more statements>

It is sometimes useful to run certain code only when a looked-for error has
not occurred.  For example, it is often agood idea to test when opening a
file for IOError (which covers a range of issues such as the file not being
found), and only reading that file if it actually opened.  For example, to
read in a file into a list of lines, the recommended practice is to do::

    try:
        fh = open(filename, 'r')
    except IOError:
        print 'cannot open file %s!' % filename
        datalines = []
    else:
        datalines = fh.readlines()
        fh.close()
    endtry
    <operate on datalines>

There is a very large number of exception types built into Larch, all
inherited from Python.   See the standard Python documentation for more
details.

Raising your own exceptions
=============================

In certain cases, you may want to cause an exception to occur.  This need is
most likely to happen when writing your own procedures, and want to ensure
that the input arguments can be handled correctly.

To cause an exception, you use the **raise** statement, and you are said to
be "raising an exception"::

    larch> raise TypeError("wrong data type")


