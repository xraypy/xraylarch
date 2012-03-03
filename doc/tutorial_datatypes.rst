==============================================
Larch Tutorial: Basic and Complex Data Types
==============================================

This section of the Larch tutorial describes the types of data that Larch
has, and how to use them.


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
including other Groups.  In this way, Groups have a heirarchical structure,
much like a directory of files.  Each Larch variable belongs to a Group,
and can be accessed by its full Group name.  The top-level Group is called
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
different groups.  The top-level '_main' group begins with 3 principle
subgroups, '_builtin', '_sys', and '_math' for basic functionality.  For
almost all uses of Larch, several additional groups are created for more
specific functionality are created on startup by Larch plugins.  The
principle starting groups are describe in
:ref:`Table of Basic Larch Groups <tutor_topgroups_table>`

.. _tutor_topgroups_table:

   Table of Basic Larch Groups.  These groups are listed in order of how
   they will be searched for functions and data.

  ==================== =================================================
   **Group Name**       **description**
  ==================== =================================================
    _builtin             basic builtin functions.
    _math                mathematical and array functions.
    _sys                 larch sstem-wide variables.
    _io                  file input/output functions.
    _plotter             plotting and image display functions.
    _xafs                XAFS-specific functions.
  ==================== =================================================

The functions in '_builtin'  are mostly inherited from Python's own
built-in functions.  The functions in '_math' are mostly inherited from
Numpy, and contain basic array handling and math.


How Larch finds variable names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With several builtin groups, and even more groups created to store your own
data to be processed, Larch ends up with a complex heirarchy of data.  This
gives a good way of organizing data, but it also leads to a question of how
variable names are found.  Of course, you can always access a function or
data object by its full name::

   larch> print _math.sin(_math.pi/2)
   1.0

but that's too painful to use, and of course, one needs to be able to do::

   larch> print sin(pi/2)
   1.0

and have Larch know that when you say :func:`sin`, you mean
:func:`_math.sin`.  The way this look-up of names works is that Larch keeps
a list of groups that it will search through for names.  This list is held
in the variable :data:`_sys.searchGroups`, and can be viewed and modified
during a Lach session.  On startup, this list has the groups listed in
:ref:`Table of Basic Larch Groups <tutor_topgroups_table>`, in the order
shown.  To be clear, if there was a variable named :data:`_sys.something`
and a :data:`_math.something`, typing 'something' would resolve to
:data:`_sys.something`, and to access :data:`_math.something` you would
have to give the full name.   For the builtin functions and variables, such
clashes are not so likely, but they are likely if you read in many data
sets as groups, and want to access the contents of the different groups.


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

A final important property of lists, and of basic variable creation in
Larch (and Python) is related to the discussion above about variable
creation and assignment.  There we said that 'creating a variable'::

    larch> my_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']

was best thought of as creating a value (here, the
literal list "['a', 'b', ..., 'j']") and then assigning the name 'my_list'
to point to that value.  Here's why we make that distinction.   If you
now say::

    larch> your_list = my_list

the variable 'your_list' now points to the same value -- the same list.
That is, it does not make a copy of the list. Since the list is mutable,
changing 'your_list' will also change 'my_list'::

    larch> your_list[0] = 500
    larch> print my_list[:3]
    [500, 'b', 'c']                # changed!!

You can make a copy of a list, by selecting a full slice::

    larch> your_list = my_list[:]
    larch> your_list[0] = 3.2444
    larch> print my_list[:3]
    [500, 'b', 'c']                 # now unchanged

    larch> your_list[0] == my_list[0]
    False

Note that this behavior doesn't happen for immutable data types, including
the more primitive data types such as integers, floats and strings.  This
is essentially because you cannot assign to parts of those data types, only
set its entire value.

As always, consult the Python documentation for more details.

Tuples
~~~~~~~~

Like lists, tuples are sequences of heterogenous objects.  The principle
difference is that tuples are **immutable** -- they cannot be changed once
they are created.  Instead, tuples are a simple ordered container of data.
The syntax for tuples uses comma separated values inside (optional!)
parentheses in place of brackets::

     larch> my_tuple = (1, 'H', 'hydrogen')

Like lists, tuples can be indexed and sliced::

     larch> my_tuple[:2]
     (1, 'H')
     larch> my_tuple[-1]
     'hydrogen'

Due to their immutability, tuples have only a few methods ('count' and
'index' with similar functionality as for list).

Though tuples they may seem less powerful than lists, and they are actually
used widely with Larch and Python.  In addition to the example above using
a tuple for a short, fixed data structure, many functions will return a
tuple of values.  For this case, the simplicity an immutability of tuples
is a strength becaues, once created, a tuple has a predictable size and
order to its elements, which is not true for lists.  That is, if a larch
procedure (which we'll see more of below) returns two values as a tuple::

    larch> def sumdiff(x, y):
    .....>     return x+y, x-y
    .....> enddef
    larch> x = sumdiff(3, 2)
    larch> print x[0], x[1]
    5 1

Because the returned tuple has a fixed structure, you can also assign
the it directly to a set of (the correct number of) variables::

    larch> plus, minus = sumdiff(10, 3)
    larch> print plus, minus
    13 7


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

Strings have many methods -- over 30 of them, in fact.  To convert a string
to lower case, use its :meth:`lower` method, and so on::

    larch> 'Here is a String'.lower()
    'here is a string'
    larch> 'Here is a String'.upper()
    'HERE IS A STRING'
    larch> 'Here is a String'.title()
    'Here Is A String'

This aslo shows that the methods are associated with strings themselves --
even literal strings, and simply with variable names.

Strings can be split into words with the :meth:`split` method, which splits
a string on whitespace by default, but can take an argument to change the
character (or substring) to use to split the string::

    larch> 'Here is a String'.split()
    ['Here', 'is', 'a', 'String']

    larch> 'Here is a String'.split('i')
    ['Here ', 's a Str', 'ng']


As above, this is really only touching the tip of the iceberg of string
functionality, and consulting standard Python documentation is recommended
for more information.

Arrays
~~~~~~~

Whereas lists are sequences of heterogeneous objects that can grow and
shrink, and included deeply nested structures, they are not well suited for
holding numerical data.  Arrays are sequences of the same primitive data
type, and so are much closer to arrays in C or Fortran.  This makes them
much more suitable for numeric calculations, and so are extremely important
in Larch.  There are many ways to create arrays, including the builtin
:func:`array` function which will attempt to convert a list or tuple of
numbers into an Array.  You can also use the builtin :func:`arange`
function to create an ordered sequence of indices ([1, 2, 3, ...]), and
several other methods listed in

:ref:`Table of Array Creation Functions <tutor_arraycreate_table>`

.. _tutor_arraycreate_table:

   Table of Array Creation Functions.  These functions can all be used to
   create arrays in Larch.

  ==================== ========================= ===========================
   **Function Name**     **description**           **example**
  ==================== ========================= ===========================
    array                array from list          arr = array([1,2,3])
    arange               indices 0, N-1           arr = arange(10)
    zeros                fill with N zeros        arr = zeros(10)
    ones                 fill with N ones         arr = ones(10)
    linspace             fill with bounds and N   arra = linspace(0, 1, 11)
  ==================== ========================= ===========================

Some examples of using these functions are needed::

    larch> i = arange(10)
    larch> i
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    larch> f = arange(10, dtype='f8')
    larch> f
    array([0., 1., 2., 3., 4., 5., 6., 7., 8., 9.])
    larch> c = arange(10, dtype='c16')
    larch> c
    array([ 0.+0.j,  1.+0.j,  2.+0.j,  3.+0.j,  4.+0.j,  5.+0.j,  6.+0.j,
            7.+0.j,  8.+0.j,  9.+0.j])


Here, the **dtype** argument sets the data type for the array members -- in
this case 'f8' means '8 byte floating point' and 'c16' means '16 byte
complex' (i.e, double precision, and double precision complex,
respectively).

The :func:`linspace` function is particularly useful for creating arrays,
as it takes a starting value, ending value, and number of points between
these::

    larch> s = linspace(0, 10, 21)
    larch> s
    array([  0. ,   0.5,   1. ,   1.5,   2. ,   2.5,   3. ,   3.5,   4. ,
             4.5,   5. ,   5.5,   6. ,   6.5,   7. ,   7.5,   8. ,   8.5,
             9. ,   9.5,  10. ])

Several variants are possible.  For more information, consult the numpy
tutorials, or use the online help system within Larch (which will print out
the documentation string from the underlying numpy function)::

    larch> help(linspace)

        Return evenly spaced numbers over a specified interval.

        Returns `num` evenly spaced samples, calculated over the
        interval [`start`, `stop` ].

        The endpoint of the interval can optionally be excluded.

        Parameters
        ----------
        start : scalar
            The starting value of the sequence.
        stop : scalar
            The end value of the sequence, unless `endpoint` is set to False.
            In that case, the sequence consists of all but the last of ``num + 1``
            evenly spaced samples, so that `stop` is excluded.  Note that the step
            size changes when `endpoint` is False.
        num : int, optional
            Number of samples to generate. Default is 50.
        endpoint : bool, optional
            If True, `stop` is the last sample. Otherwise, it is not included.
            Default is True.
        retstep : bool, optional
            If True, return (`samples`, `step`), where `step` is the spacing
            between samples.

	....


Dictionaries
~~~~~~~~~~~~~~

Our final basic data-structure is the dictionary, which is a container that
maps values to keys.  This is sometimes called a hash or associative array.
Like a list, a dictionary holds many heterogeneous values, and can be
altered in place.  Unlike a list, the elements of a dictionary have no
guaranteed order, and are not selected by integer index, and multiple
values cannot be selected by a slice.  Instead, the elements of a
dictionary are accessed by key, which is normally a string, but can also be
an integer or floating point number, or even a tuple or some other objects
-- any **immutable** object can be used.   Dictionaries are delimited by
curly braces, with colons (':') separating key and value, and commas
separating different elements::

    larch> atomic_weight = {'H': 1.008, 'He': 4.0026, 'Li': 6.9, 'Be': 9.012}
    larch> print atomic_weight['He']
    4.0026

You can also add more elements to a dictionary by assigning to a new key::

    larch> atomic_weight['B']  = 10.811
    larch> atomic_weight['C']  = 12.01

Dictionaries have several methods, such as to return all the keys or all
the values, with::

    larch> atomic_weight.keys()
    ['Be', 'C', 'B', 'H', 'Li', 'He']
    larch> atomic_weight.values()
    [9.0120000000000005, 12.01, 10.811, 1.008, 6.9000000000000004, 4.0026000000000002]

Note that the keys and values are not in the order they were entered in,
but do have the same order.

As with lists, dictionaries are mutable, and the values in a dictionary can
be any object, including other lists and dictionaries, so that a dictionary
can end up with a very complex structure.  Dictionaries are quite useful,
and are in fact used throughout python.

