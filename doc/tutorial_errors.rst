=======================================================
Tutorial: Dealing With Errors
=======================================================

When an error exists in the syntax of your script, or an erro happens when
running your script, an *Error* or *Exception* is generated, and the
execution of your script is stopped.

Syntax Errors
===============

Syntax errors result from incomplete or ill-formed larch syntax.


Exceptions
=================

Even if the syntax of your script is correct, it might cause an error at
run time::

   larch> n = 1
   larch> print 4.0 / ( n - 1)
   ZeroDivisionError: float division
   <StdInput>
       print 4.0/(n-1)
             ^^^

which is saying that you can't divide by 0.


try and except
==================
