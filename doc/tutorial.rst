============================
Larch Tutorial
============================

This chapter describes the Larch language and provides an introduction into
processing data using Larch.  An important goal of Larch is to make writing
and modifying data analysis as simple as possible.  The tutorial here tries
to make few assumptions about your experience with scientific
programming. On the other hand, Larch is a language for processing of
scientific data, the expected audience is expected to have a technical
background, familiarity with using programs for scientific data analysis.
In addition, some understanding of the concepts of how scientific data is
stored on computers and of the basics of programming.

The Larch language is implemented in and heavily based on Python.
Knowledge of Python will greatly simplify learning Larch, and vice versa.
This shared syntax is intentional, so that as you learn Larch, you will
also be learning Python, which can be used to extend Larch.  Alternatively,
knowledge of Python will make Larch easy to learn.  For further details on
Python, including tutorials, see the Python documentation at
http://python.org/

Getting Started
===================

This tutorial expects that you already have Larch installed and can run
either the program larch, basic Larch interpreter, or larch_gui, the enhanced
GUI interpreter::

   C:> larch
     Larch 0.9.7  M. Newville, T. Trainor (2011)
     using python 2.6.5, numpy 1.5.1
   larch>

For Windows and Mac OS X users, executable applications will be available.

Larch as a Basic Calculator
================================

To start with, Larch can be used as a simple calculator::

   larch> 1 + 2
   3
   larch> sqrt(4.e5)
   632.45553203367592
   larch> sin(pi/3)
   0.8660254037844386

You can create your own variables holding values, by assigning names to
values, and then use these in calculations::

   larch> hc = 12398.419
   larch> d = 3.13556
   larch> energy = (hc/(2*d)) / sin(10.0*pi/180)
   larch> print energy
   11385.470119348252
   larch> angle = asin(hc/(10000*2*d))*180/pi
   larch> print angle
   11.402879992850263

Note that parentheses are used to group multiplication and division, and
also to hold the arguments to functions like ``sin``.

Variable names must start with a letter or underscore ('_'), followed by
any number of letters, underscores, or numbers.  You may notice that a dot
('.') may appear to be in many variable names.  We'll get to this in a
later section.


Basic Data Types
======================

As with most programming languages, Larch has several built-in data types
to express different kinds of data.  These include the usual integers,
floating point numbers, and strings common to many programming languages.
A variable name can hold any of these types (or any of the other more
complex types we'll get to later), and does not need to be declared
beforehand or to change its value or type.  Some examples::

   larch> a = 2
   larch> b = 2.50

The normal '+', '-', '*', and '/' operations work on numerical values for
addition, subtraction, multiplication, and division.  Exponentiation is
signified by '**', and modulus by '%'.  Larch uses the '/' symbol for
division or 'true division', giving a floating point value if needed, even
if the numerator and denominator are integers, and '//' for integer or
'floor' division.  Thus::

   larch> 3 + a
   5
   larch> b*2
   5.0
   larch> 3/2
   1.5
   larch> 3//2
   1
   larch> 7 % 3
   1

Several other operators are supported for bit manipulation.

Literal strings are created with either matched closing single or double
quotes::

   larch> s = 'a string'
   larch> s2 = "a different string"

A string can include a '\n' character (for newline) or '\t' (for tab) and
several other control characters as in many languages.  For strings that
may span over more than 1 line, a special "triple quoted" syntax is
supported, so that::

    larch> long_string = """Now is the time for all good men
    .....> to come to the aid of their party"""
    larch> print long_string
    Now is the time for all good men
    to come to the aid of their party


It is important to keep in mind that mixing data types in a calculation may
or may not make sense to Larch.  For example, a string cannot be added to a
integer::

   larch> '1' + 1
   Runtime Error:
   cannot concatenate 'str' and 'int' objects
   <StdInput>
        '1' + 1

but you can add an integer and a float::

   larch> 1 + 2.5
   3.5

and you can multiply a string by an integer::

   larch> 'string' * 2
   'stringstring'

Larch has special variables for boolean or logical operations: ``True`` and
``False``.  These are actually equal to 1 and 0, respectively, but are
mostly used in logical operations, which include operators 'and', 'or', and
'not', as well as comparison operators '>', '>=', '<', '<=', '==', '!=', and
'is'.  Note that 'is' expresses identity, which is a slightly stricter test
than '==' (equality), and is most useful for complex objects.::

   larch> 2 > 3
   False
   larch> (b > 0) and (b <= 10)
   True

The special value ``None`` is used as a null value throughout Larch and
Python.

Finally, Larch knows about complex numbers, using a 'j' to indicate the
imaginary part of the number::

   larch> sin(-1)
   larch> sqrt(-1)
   Warning: invalid value encountered in sqrt
   nan
   larch> sqrt(-1+0j)
   1j
   larch> 1j*1j
   (-1+0j)
   larch> x = sin(1+1j)
   larch> print x
   (1.2984575814159773+0.63496391478473613j)
   larch> print x.imag
   0.63496391478473613


To be clear, all these primitive data types in Larch are derived from the
corresponding Python objects, so you can consult python documentation for
further details and notes.


More Complex Data Structures:  Lists, Arrays, Dictionaries
===========================================================

Larch has many more data types built on top of the primitive types above.
These are generally useful for storing collections of data, and can be
built up to construct very complex structures.  These are all described in
some detail here.  But as these are all closely related to Python objects,
further details can be found in the standard Python documentation.

Here, the word "object" is used frequently.  Each piece of data in Larch is
a Python object, which is to say it has a value and may have specific
functions that go with it.

Lists
~~~~~~

A list is a sequence of other data types.  The data types do not have to be
the same type.  A list is constructed using brackets, with commas to
separate the individual::

    larch> my_list1 = [1, 2, 3]
    larch> my_list2 = [1, 'string', sqrt(7)]

A list can contain a list as one of its elements::

    larch> nested_list = ['a', 'b', ['c', 'd', ['e', 'f', 'g']]]

You can access the elements of a list using brackets and the integer index
(starting from 0)::

    larch> print my_list2[1]
    'string'
    larch> print nested_list[2]
    ['c', 'd', ['e', 'f', 'g']]
    larch> print nested_list[2][0]
    'c'

Lists are **mutable** -- they can be changed, in place.   To do this, you
can replace an element in a list::

    larch> my_list1[0] = 'hello'
    larch> my_list1
    ['hello', 2, 3]

You can also change a list by appending to it with the 'append' method::

    larch> my_list1.append('number 4, the larch')
    larch> my_list1
    ['hello', 2, 3, 'number 4, the larch']


The syntax using a '.' indicates a method -- a function specific to that
object.  All lists will have an 'append' method, as well as several others:

    * count -- to return the number of times a particular element occurss in the list
    * extend -- to extend a list with another list
    * index -- to find the first occurance of an element
    * insert -- to insert an element in a particular place.
    * pop -- to remove and return the last element (or other specified index).
    * remove -- remove a particular element
    * reverse -- reverse the order of elements
    * sort -- sort the elements.

Note that the methods that change the list do so *IN PLACE* and return
``None``.  That is, to sort a list, do::

     larch> my_list.sort()

but not::

     larch> my_list = my_list.sort()  # WRONG!!

as that will set 'my_list' to None.

You can get the length of a list with the built-in :func:`len` function,
and test whether a particular element is in a list with the `in` operator::

    larch> my_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    larch> print len(my_list)
    10
    larch> 'e' in my_list
    True

You can access a sub-selection of elements with a *slice*, giving starting
and ending indices between brackets, separated by a colon.  Of course, the counting
for a slice starts at 0. It also excludesthe final index::

    larch> my_list[1:3]
    ['b', 'c']
    larch> my_list[:4]   # Note implied 0!
    ['a', 'b', 'c', 'd']

You can count backwards, and using '-1' is a convenient way to get the last
element of a list.  You can also add an optional third value to the slice for a step::

    larch> my_list[-1]
    'j'
    larch> my_list[-3:]
    ['h', 'i', 'j']
    larch> my_list[::2]  # every other element, starting at 0
    ['a', 'c', 'e', 'g', 'i']
    larch> my_list[1::2]  # every other element, starting at 1
    ['b', 'd', 'f', 'h', 'j']

As always, consult the Python documentation for more details.

Tuples
~~~~~~~~

Like lists, tuples are sequences of heterogenous objects.  The principle
difference is that tuples are **immutable** -- they cannot be changed once
they are created.  The syntax for tuples uses parentheses in place of
brackets::

     larch> my_tuple = (1, 'H', 'hydrogen')

Like lists, tuples can be indexed and sliced::

     larch> my_tuple[:2]
     (1, 'H')
     larch> my_tuple[-1]
     'hydrogen'

Due to their immutability, tuples have only a few methods ('count' and
'index' with similar functionality as for list).  Though they may seem less
powerful than lists, tuples are actually used widely with Larch and Python,
as once created a tuple has a predictable size and order to its elements.
Thus, as with the example above, it can be used as a simple ordered
container of data.

A second look at Strings
~~~~~~~~~~~~~~~~~~~~~~~~~~

Though discussed earlier in the basic data types, strings are closely
related to lists as well -- they are best thought of as a sequence of
characters.  Like tuples, strings are actually immutable, in that you
cannot change part of a string, instead you must create a new string.
Strings can be indexed and sliced as with lists and tuples::

     larch> name = 'Montaigne'
     larch> name[:4]
     'Mont'

Strings have many methods...


Arrays
~~~~~~~

Dictionaries
~~~~~~~~~~~~~~


Conditional Execution and Control-Flow
===========================================


Object and Groups
======================

Objects
~~~~~~~~~~

Reading and Writing Data
============================

Plotting and Displaying Data
=================================

Procedures
==============

Dealing With Errors
=======================



