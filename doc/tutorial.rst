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
``False``.  These are equal to 1 and 0, respectively, but are mostly used
in logical operations, which include operators 'and', 'or', and 'not', as
well as comparison operators '>', '>=', '<', '<=', '==', '!=', and 'is'.
Note that 'is' expresses identity, which is a slightly stricter test than
'==' (equality), and is most useful for complex objects.::

   larch> 2 > 3
   False
   larch> (b > 0) and (b <= 10)
   True

The special value ``None`` is used as a null value throughout Larch and
Python.

Finally, Larch knows about complex numbers, using a 'j' to indicate the
imaginary part of the number::

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

Objects and Groups
======================

Since Larch is built upon Python, an object-oriented programming language,
all named quantities or **variables** in Larch are python objects.  Because
of this, most Larch variables come with built-in functionality derived from
their python objects. Though Larch does not provide a way for the user to
define their own new objects, this can be done with the Python interface.

Objects
~~~~~~~~~~

All Larch variables are Python objects, and so have a well-defined **type**
and a set of **attributes** and **methods** that go with it.   To see the
Python type of any variable, use the builtin :func:`type` function::

   larch> type(1)
   <type 'int'>
   larch> type('1')
   <type 'str'>
   larch> type(1.0)
   <type 'float'>
   larch> type(1+0j)
   <type 'complex'>
   larch> type(sin)
   <type 'numpy.ufunc'>

The attributes and methods differ for each type of object, but are all
accessed the same way -- with a '.' (dot) separating the variable name or
value from the name of the attribute or method.   As above, complex data
have :attr:`real` and :attr:`imag` attributes for the real and imaginary
parts,  which can be accessed::

   larch> x = sin(1+1j)
   larch> print x
   (1.2984575814159773+0.63496391478473613j)
   larch> print x.imag
   0.63496391478473613

Methods are functions that belong to an object (and so know about the data
in that object).  They are also objects themselves (and so have attributes
and methods), but can be called using parentheses '()', possibly with
arguments inside the parentheses to change the methods behavior.  For
example, a complex number has a :meth:`conjugate` method::

   larch> x.conjugate
   <built-in method conjugate of complex object at 0x178e54b8>
   larch> x.conjugate()
   (1.2984575814159773-0.63496391478473613j)

Strings and other data types have many more attributes and methods, as
we'll see below.

To get a listing of all the attributes and methods of a object, use the
builtin :func:`dir` function::

   larch> dir(1)
   ['__abs__', '__add__', '__and__', '__class__', '__cmp__', '__coerce__', '__delattr__', '__div__', '__divmod__', '__doc__', '__float__', '__floordiv__', '__format__', '__getattribute__', '__getnewargs__', '__hash__', '__hex__', '__index__', '__init__', '__int__', '__invert__', '__long__', '__lshift__', '__mod__', '__mul__', '__neg__', '__new__', '__nonzero__', '__oct__', '__or__', '__pos__', '__pow__', '__radd__', '__rand__', '__rdiv__', '__rdivmod__', '__reduce__', '__reduce_ex__', '__repr__', '__rfloordiv__', '__rlshift__', '__rmod__', '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__', '__rxor__', '__setattr__', '__sizeof__', '__str__', '__sub__', '__subclasshook__', '__truediv__', '__trunc__', '__xor__', 'conjugate', 'denominator', 'imag', 'numerator', 'real']
   larch> dir('a string')
   ['__add__', '__class__', '__contains__', '__delattr__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__getnewargs__', '__getslice__', '__gt__', '__hash__', '__init__', '__le__', '__len__', '__lt__', '__mod__', '__mul__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__rmod__', '__rmul__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '_formatter_field_name_split', '_formatter_parser', 'capitalize', 'center', 'count', 'decode', 'encode', 'endswith', 'expandtabs', 'find', 'format', 'index', 'isalnum', 'isalpha', 'isdigit', 'islower', 'isspace', 'istitle', 'isupper', 'join', 'ljust', 'lower', 'lstrip', 'partition', 'replace', 'rfind', 'rindex', 'rjust', 'rpartition', 'rsplit', 'rstrip', 'split', 'splitlines', 'startswith', 'strip', 'swapcase', 'title', 'translate', 'upper', 'zfill']

Again, we'll see properties of objects below, as we look into more
interesting data types, or you can look into Python documentation.

Groups
~~~~~~~~~~

In addition to using basic Python objects, Larch organizes data into
Groups.  A Group is simply a named container for variables of any kind,
including other Groups.  In this way, Groups have a hierarchical structure,
much like a directory of files.   Each Larch variable belongs to a Group,
and can be accessed by its full Group name.   The top-level Group is called
'_main'.  You'll rarely need to use that, but it's there::

   larch> myvar = 22.13
   larch> print _main.myvar
   22.13
   larch> print myvar
   22.13

You can create your own groups and add data to it with the builtin
:meth:`group` function::

    larch> g = group()
    larch> g
    <Group>

You can add variables to your Group 'g', using the '.' (dot) to separate
the parent group from the child object::

    larch> g.x = 1002.8
    larch> g.name = 'here is a string'
    larch> g.data = arange(100)
    larch> print g.x/5
    200.56

(:func:`arange` is a builtin function to create an array of numbers).  As
from the above discussion of objects, the '.' (dot) notation implies that
'x', 'name', and 'data' are attributes of 'g' -- that's entirely correct.
Groups have no other properties than the data attributes (and functions)
you add to them.  Since they're objects, you can use the :func:`dir`
function as above::

    larch> dir(g)
    ['data', 'name', 'x']

(Note that the order shown may vary).  You can also use the builtin
:func:`show` function to get a slightly more complete view of the group's
contents::

    larch> show(g)
    == Group: 3 symbols ==
      data: array<shape=(100,), type=dtype('int32')>
      name: 'here is a string'
      x: 1002.8

The :func:`group` function can take arguments of attribute names and
values, so that this group could have been created with a single call::

    larch> g = group(x=1002.8, name='here is a string', data=arange(100))

Many Larch functions will return groups or take a 'group' argument to
write data into.  That is, a function that reads data from a file will
almost certainly organize that data into a group, and simply return the
group for you to name, perhaps something like::

    larch> cu = read_ascii('cu_150k.xmu')


Builtin Larch Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Larch starts up with several groups, organizing builtin functionality into
different groups.   The top-level '_main' group begins with 3 principle
subgroups::

  _builtin  -- basic builtin functions, mostly inherited from Python
  _math     -- mathematical and array functionality, mostly inherited from numpy.
  _sys      -- larch-specific system-wide variables

In addition, a few groups will be created by standard plugins that will
almost certainly be installed with Larch, including::

  _io  -- file input/output functionality
  _plot  -- plotting and image display functionality


How Larch finds variable names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

More Complex Data Structures:  Lists, Arrays, Dictionaries
===========================================================

Larch has many more data types built on top of the primitive types above.
These are generally useful for storing collections of data, and can be
built up to construct very complex structures.  These are all described in
some detail here.  But as these are all closely related to Python objects,
further details can be found in the standard Python documentation.

Lists
~~~~~~

A list is an ordered sequence of other data types.  They are
**heterogeneous** -- they can be made up of data with different types.  A
list is constructed using brackets, with commas to separate the
individual::

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

As above, lists are python **objects**, and so come with methods for
interacting with them.  For example, you can also change a list by
appending to it with the 'append' method::

    larch> my_list1.append('number 4, the larch')
    larch> my_list1
    ['hello', 2, 3, 'number 4, the larch']


All lists will have an 'append' method, as well as several others:

    * count -- to return the number of times a particular element occurss in the list
    * extend -- to extend a list with another list
    * index -- to find the first occurance of an element
    * insert -- to insert an element in a particular place.
    * pop -- to remove and return the last element (or other specified index).
    * remove -- remove a particular element
    * reverse -- reverse the order of elements
    * sort -- sort the elements.

Note that the methods that change the list do so *IN PLACE* and return
``None``.  That is, to sort a list, do this::

     larch> my_list.sort()

but not this::

     larch> my_list = my_list.sort()  # WRONG!!

as that will set 'my_list' to None.

You can get the length of a list with the built-in :func:`len` function,
and test whether a particular element is in a list with the `in` operator::

    larch> my_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    larch> print len(my_list)
    10
    larch> 'e' in my_list
    True

You can access a sub-selection of elements with a **slice**, giving starting
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




Reading and Writing Data
============================

Plotting and Displaying Data
=================================

Procedures
==============

Dealing With Errors
=======================



