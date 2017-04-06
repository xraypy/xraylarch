.. _tutor-datatypes_sec:

============================================
Tutorial: Basic and Complex Data Types
============================================

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

A string can include a '\\n' character (for newline) or '\\t' (for tab) and
several other control characters, as in many languages.  The backslash
character '\\' indicates these *escape sequences*, which includes newline as
tab as well as several other standard escape sequence.  The quote character
and the backslash character themselves can be backslashed.  Thus, to get an
actual backslash character in the string, you would have to use '\\\\', and
to get a single quote, one might say::

   larch> s3 = 'A string with a backslash-> \\ '
   larch> s4 = 'Bob\'s string'

One can also use so-called a *raw string*, in which the backslash character
is **not** used for escape sequences::

   larch s5 = r'A string with backslash \n but not a newline!'

For strings that may span over more than 1 line, a special "triple quoted"
syntax is supported, so that::

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

   larch> b = 5
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
define their own new objects, objects created in Python this can be used by
Larch, so that extensions and plugins for Larch can define new classes of
object types.

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
value from the name of the attribute or method.  As above, complex data
have :attr:`real` and :attr:`imag` attributes for the real and imaginary
parts, which can be accessed::

   larch> x = sin(1+1j)
   larch> print x
   (1.2984575814159773+0.63496391478473613j)
   larch> print x.imag
   0.63496391478473613

Methods are attributes of an object that happen to be callable as a
function.  Since they belong to to an object, they know about the data and
other attributes in that object.  To call a method or function, simply add
parentheses '()' after its name, possibly with arguments inside the
parentheses to change the methods behavior.  For example, a complex number
has a :meth:`conjugate` method::

   larch> x.conjugate
   <built-in method conjugate of complex object at 0x178e54b8>
   larch> x.conjugate()
   (1.2984575814159773-0.63496391478473613j)

Note that just using ``x.conjugate`` returns the method itself, while using
``x.conjugate()`` actually runs the method.  It's fair to ask why ``real``
and ``imag`` are simple attributes of complex number object while
``conjugate`` is a method that must be called.  In general, the idea is
that simple attributes are static data belonging to the object, while a
method is something that has to be computed.  These rules are not fixed,
however, and it is sometimes a matter of knowing which attributes are
callable methods.

Many data types have their own attribues and methods.  As we'll see below,
strings have many attributes and methods, as do the container objects
(list, array, tuple, dictionary) we'll see shortly.

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

While all values in Larch are Python objects, Larch organizes data into
Groups, which are a key concept to Larch.  A Group is simply a named
container for variables of any kind, including other Groups.  As Larch
doesn't directly provide a way to definie your own objects, a Group is the
way to organize your data in Larch.  The organization of data with nested
Groups provides a heirarchical structure to all data in a Larch session,
much like a directory of files.  Each Larch variable belongs to a Group,
and can always be accessed by its full Group name.  The top-level Group is
called '_main'.  You'll rarely need to use that fact, but it's there::

   larch> myvar = 22.13
   larch> print _main.myvar
   22.13
   larch> print myvar
   22.13

You can create your own groups and add data to it with the builtin
:meth:`group` function::

    larch> g = group()
    larch> g
    <Group 0x17ee50f0>

You can add variables to your Group 'g', using the '.' (dot) to separate
the parent group from the child object::

    larch> g.x = 1002.8
    larch> g.label = 'here is a string'
    larch> g.data = arange(100)
    larch> print g.x/5
    200.56

(:func:`arange` is a builtin function to create an array of numbers).  As
from the above discussion of objects, the '.' (dot) notation implies that
'x', 'label', and 'data' are attributes of 'g' -- that's entirely correct.

Groups have 1 builtin property -- ``__name__`` which holds a name for the
Group. If not specified, it will be set to a hexidecimal value.  Groups
have no other builtin properties or methods.  Since they're objects, you
can use the :func:`dir` function as above::

    larch> dir(g)
    ['data', 'label', 'x']

(Note that the order shown may vary).  You can also use the builtin
:func:`show` function to get a slightly more complete view of the group's
contents::

    larch> show(g)
    == Group 0x1b8cbfb0: 3 symbols ==
      data: array<shape=(100,), type=dtype('int32')>
      name: 'here is a string'
      x: 1002.8

(The '0x1b8cbfb0' is the default name, discussed in more detail below in
:ref:`tutor-objectids_sec`).  The :func:`group` function can take arguments
of attribute names and values, so that this group could have been created
with a single call::

    larch> g = group(x=1002.8, name='here is a string', data=arange(100))

Many Larch functions act on groups, either returning groups, expecting
groups as certain arguments, or taking a 'group' argument to write data
into.  For example, the built-in functions that read data from an external
files will likely organize that data into a group and that group perhaps
something like::

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

.. index:: toplevel groups
.. _tutor_topgroups_table:

   Table of Basic Larch Groups.  These groups are listed in order of how
   they will be searched for functions and data.

  ==================== =================================================
   **Group Name**       **description**
  ==================== =================================================
    _builtin             basic builtin functions.
    _math                mathematical and array functions.
    _sys                 larch system-wide variables.
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

    * append -- add an element to the end of the list
    * count -- to return the number of times a particular element occurs in the list
    * extend -- to extend a list with another list
    * index -- to find the first occurance of an element
    * insert -- to insert an element in a particular place.
    * pop -- to remove and return the last element (or other specified index).
    * remove -- remove a particular element
    * reverse -- reverse the order of elements
    * sort -- sort the elements.

Note that the methods that change the list do so *IN PLACE* and return
``None``.  That is, to sort a list (alphabetically by default, or with an
optional custom comparison function passed in), do this::

     larch> my_list.sort()

but not this::

     larch> my_list = my_list.sort()  # WRONG!!

as that will sort the list, then happily set 'my_list' to None.

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
function to create an ordered sequence of indices ([1, 2, 3, ...]), or one
of several other methods to create arrays.

Arrays are so important for processing numerical data that the next section
is devoted to them.


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

Dictionaries have several methods.  These include

    * clear -- remove all elements from a dictionary.
    * copy -- make a copy of a dictionary.
    * get -- get an element by name.
    * has_key -- return whether a dictionary has a key.
    * items -- return a list of (key, value) tuples
    * keys  -- return a list of keys.
    * values -- return a list of values.
    * pop -- remove an element by key, return the value.
    * popitem -- remove the "next" item, return (key, value)
    * update -- add or overwrite items from another dictionary.

For example:

    larch> atomic_weight.keys()
    ['Be', 'C', 'B', 'H', 'Li', 'He']
    larch> atomic_weight.values()
    [9.0120000000000005, 12.01, 10.811, 1.008, 6.9000000000000004, 4.0026000000000002]

Note that the keys and values are not in the order they were entered.  If
you add more elements to the dictionary, the new order can be unrelated to
the old order.  What is guaranteed is that the order of the list of keys
will always match the order of the list of values.

As with lists, dictionaries are mutable, and the values in a dictionary can
be any object, including other lists and dictionaries, so that a dictionary
can end up with a very complex structure.  Dictionaries are quite useful,
and are in fact used throughout python.

.. _tutor-objectids_sec:

Object identities, copying, and equality vs. identity
=========================================================

OK, this may be a bit advanced for a section in a *tutorial*, but there are
a few important topics we need to make about objects, groups, and the idea
of *mutability* discussed above.  Though it may at first pass seem
surprising, these points are all related, and will come up several times in
this document and in your use of Larch.  Those familiar with Fortran, C, or
Java programming may need to read this more carefully, as Larch and Python
actually work quite differently from those languages.  What we're aiming to
cover here includes:

  * what variable assignment really means.
  * mutable and immutable objects.
  * object identity.
  * the difference between equality and identity.

As mentioned above, each named quantity in Larch is simply a Python object
(for the C, C++, and Java programmers, every variable is reference or
pointer).  Assignment to a Larch variable as with::

    larch> w = 1 + 2
    larch> x = 'a string'
    larch> y = ['a', 'b', 'c', 'd']
    larch> z = some_function(3)

first determines the *value* from the right-hand-side of the expression
(1+2, 'a string', a list, and the return value of some_function()) then
assigns the variable *name* (w, x, y, z) to point to the corresponding
value.  Larch doesn't pre-assign variable names so that 'w' there can only
ever hold an integer -- you can change not only its value but the *type* of
data its pointing to::

    larch> w = 3.25  # now a floating point number
    larch> w = [1, 2, 3]  # now a list

For this reason, a variable name is best thought of as something very
different from the value it points to.  Of course, it is obvious when two
different variable names are different, because the names are different.
It is less clear whether the value the variables hold are different.

Values of simple types (integer, float, string, tuple, and a few other
builtin types) are said to be **immutable** --  the value itself cannot
change.   You can reassign a name to a different value, but::

    larch> w = 3.25
    larch> w = 4.68

doesn't change the value of 3.25.  Assignment to simple types then can be
thought of as essentially making a fresh value for the name to point each
time an assignment is made.  This isn't exactly true because Python sets
pre-allocates small integers so that it is not making a new integer object
every time you assign a number to 1, but it's a reasonable approximation
for now.

Several object types such as lists, dictionaries, arrays, and groups, all
are meant to changeable after they are created: they are **mutable**.  That
is, even after creating a list, you can append an element to it or you can
remove an item from it, and so on.  These actions changes the *value* that
the object points to.  The object just points to a place in memory -- this
does not have to change just because the value changes.

This is somewhat different than the model for variable in languages such as
C or Fortran where variables have fixed memory locations and specific types
of data they can hold.   In Python and Larch, all objects point to some
value.  For mutable data types, the value is allowed to change.  In
addition, what the object points to can also change.

Each object value has a unique memory location -- its identity.  The
builtin :func:`id` function returns this identity.  Two variables are said
to be *identical* if their values have the same identity -- the variables
point to the same quantitiy.  Two variabales are *equal* if their values
are the same, even if these values are held in different memory locations.
And, of course, two different variables can point to the same object.

You can test both equality (whether two variables hold equal value) and identity
(whether two variables point to the same value).   First, the builtin
:func:`id` function will give the identity (essentially, the memory
location) of a variable::

    larch> x = [1, 2, 3, 4, 5]
    larch> id(x)
    108444568

(the value shown will be different each time you run Larch).  Now if we
assign another variable to ``x``, we can use :func:`id` to see why changing
the value of one changes the value of the other::

    larch> y = x
    larch> id(y)
    108444568      ### The same as id(x) !!
    larch> y[1] = 'hello'
    larch> print x
    [1, 'hello', 3, 4, 5]

Here, ``x`` changed because it is identical to ``y`` and is mutable.
However, if we make another variable that happens to have the same value::

    larch> z = [1, 'hello', 3, 4, 5]
    larch> id(z)
    108399752

Now changing an element of ``z`` will not change ``x`` or ``y``.     You
can test whether two variables have equal values with the boolean operator
`==`.   Similarly, you can test whether two variables are identical with
the  boolean operator `is`.  So::

    larch> x == y, x is y
    (True, True)
    larch> x == z, x is z
    (True, False)

If you want to make a copy of a mutable object, you can use the builtin
:func:`copy` function::

    larch> q = copy(z)
    larch> q == z, q is z
    (True, False)

Another, and very common way to make copies of lists and arrays is to
create a new value that happens to have the same value.  For a list, a very
common approach is to make a *full slice*::

    larch> newx = x[:]
    larch> x == newx, x is newx
    (True, False)

and for arrays, you can multiply by 1 or add 0::

    larch> a = array([1., 2., 3., 4., 5., 6.])
    larch> b = a
    larch> c = 1 * a
    larch> a is b, a is c
    (True, False)


Note that doing ``a == b`` on arrays here would give an array of values, testing
the values element-by-element.  This will be discussed the next section.

Larch Groups are also mutable objects and so assignment to a group does not
make a new copy of the group but another reference to the same group::

    larch> g = group(x=1, text='hello')
    larch> h = g
    larch> h is g
    True

If ask for the group to be printed or run the :func:`show` function on a group::

    larch> g
    <Group 0x6bf17f0>
    larch> show(g)
    == Group 0x6bf17f0: 2 symbols ==
      x: 1
      text: 'hello'

we see the hexidecimal representation of its  memory address::

    larch> id(g), hex(id(g))
    (113186800, '0x6bf17f0')



In practice, this issue is not as confusing as it sounds, and the model for
data, variables, and values is generally very easy to deal with.  The most
important thing to be aware of -- the thing most likely to cause trouble --
is that assigning a variable to be a mutable object like a list,
dictionary, or array does not make a copy of the object, but simply creates
another variable that points to the same value.




