=====================================================
Tutorial: Builtin Functions
=====================================================

Larch has several general built-in functions for basic manipulation of data and
programming needs.  Many of these are copied directly from Python, but
several are Larch-specifc.   Note that the advanced math and scientific
functions are not listed here, but elsewhere in the documentation.

Builtin data values
==========================

The values ``True``, ``False``  represent the boolean values
for true and false.  ``None`` is the null value.


Larch-Specific Builtin functions
==============================================

These built-in functions are specific to Larch (that is, not inherited from
Python).  Many help you work with Larch groups or otherwise simplify common tasks.

.. function:: add_plugin(python_file)

    add plugin components from plugin file (Python file) or directory for a
    Python module.

.. function:: cd(directory_name)

    change directory to specified directory.

.. function:: cwd()

    return current working directory

.. function:: dict2group(dict)

   return a group created from a dictionary.  Note that this is equivalent
   to ``group(**dict)``.

.. function:: get(name)

   get object from symbol table by name.  For example::

      larch> g = group(a = 1,  b=2.3, z = 'a string')
      larch> print get('g.z')
      'a string'

   this is can also be accomplished by the similar::

      larch> print getattr(g, 'z')
      'a string'

   but the :func:`get` version uses only the name of the object.

.. function:: group(key=val, key2=val2, ....)

    create a group, with optional keyword/value pairs.

.. function:: group_items(group)

    return a list of (key, val) pairs for items in a group. This is
    equivalent to ``group2dict(group).items()``, and provides the idiomatic
    way to loop through all items in a group.

.. function:: group2dict(group)

   return dictionary of group members

.. function:: help(object)

    show help on topic or object

.. function:: isgroup(object)

    returns ``True`` is the object is a group.

.. function:: isparam(object)

    returns ``True`` is the object is a parameter.

.. function:: ls(directory_name_or_file_pattern)

    returns a list of files in the current directory.  If a '*' is used in
    the argument, the returned list is limited to files matching that
    pattern.  For example::

        larch> ls('.')
        ['cu.chi', 'cu.xmu', 'cu10k.chi', 'cu_10k.xmu', 'cu_150k.xmu',
         'cu_50k.xmu', 'cu_metal_rt.xdi', 'cu_rt01.xmu', 'fe.060',
         'fe2o3_rt1.xmu', 'fe3c_rt.xdi', 'feo_exafs_pnccat2001.dat',
         'feo_rt1.xmu', 'feo_xafs.dat', 'scorodite_as_xafs.001', 'znse_zn_xafs.001']
        larch> xdifiles = ls('*.xdi')
        larch> print xdifiles
        ['cu_metal_rt.xdi', 'fe3c_rt.xdi']


.. function:: mkdir(directory_name[, mode=0777])

    create directory (and any intermediate subdirectories) with the
    specified name.  The ``mode`` option sets the permission mask to use
    for creating directory (default=0777).


.. function:: more(filename[, pagelenghth=32])

    list file contents, optionally specifying the number of lines to
    show at a time.  By default, the file is shown 32 lines at a time.::

       larch> more('file.txt')
       larch> more('file.txt', pagelength=10)

.. function:: parent(object)

    print out parent group name of an object

.. function:: pause(timeout)

   pause for for input from the command line.

.. function:: run(filename[, printall=True])

    execute the larch text in a file as larch code.

.. function:: show(group[, with_private=False])

    display group members. The ``with_private`` option will show private
    members.

    See Also:  show_tree()

.. function:: show_tree(group)

    show members of a Group, with a tree structure for sub-groups

    larch> show_tree(group1)

.. function:: sleep(t=0)

   sleep for a specified number of seconds.

.. function:: subgroups(group)

    return list of subgroups of a group

.. function:: which(object)

    return full path of object in Larch's symbol table::

        larch> which(which)
        '_builtin.which'



Builtin functions inherited from Python
==============================================

.. function:: abs(value)

   Return the absolute value of the argument.

.. function:: all(x)

   Return ``True`` if bool(x) is ``True`` for all values x in the iterable.

.. function:: any(x)

   Return ``True`` if bool(x) is ``True`` for any x in the iterable.

.. function:: bin(number)

   Return the binary representation of an integer or long integer.

.. function:: bool(x)

   Returns True when the argument x is true, False otherwise.
   The builtins True and False are the only two instances of the class bool.
   The class bool is a subclass of the class int, and cannot be subclassed.

.. function:: buffer(object [, offset[, size]])

    Create a new buffer object which references the given object.
    The buffer will reference a slice of the target object from the
    start of the object (or at the specified offset). The slice will
    extend to the end of the target object (or with the specified size).

.. function:: bytearray(iterable_of_ints)

    bytearray(string, encoding[, errors]) -> bytearray.
    bytearray(bytes_or_bytearray) -> mutable copy of bytes_or_bytearray.
    bytearray(memory_view) -> bytearray.

    Construct an mutable bytearray object from:
      - an iterable yielding integers in range(256)
      - a text string encoded using the specified encoding
      - a bytes or a bytearray object
      - any object implementing the buffer API.

    bytearray(int) -> bytearray.

    Construct a zero-initialized bytearray of the given length.

.. function:: bytes(object)

    Return a nice string representation of the object.
    If the argument is a string, the return value is the same object.

.. function:: callable(object)

    Return whether the object is callable (i.e., some kind of function).
    Note that classes are callable, as are instances with a __call__() method.

.. function:: cd(directory)

    change directory to specified directory

.. function:: chr(i)

   Return a string of one character with ordinal i; 0 <= i < 256.

.. function:: cmp(x, y)

   Return negative if x<y, zero if x==y, positive if x>y.

.. function:: coerce(x, y)

    Return a tuple consisting of the two numeric arguments converted to
    a common type, using the same rules as used by arithmetic operations.
    If coercion is not possible, raise TypeError.

.. function:: complex(real[, imag])

    Create a complex number from a real part and an optional imaginary part.
    This is equivalent to (real + imag*1j) where imag defaults to 0.

.. function:: copy(object)

    copy an object

.. function:: deepcopy(object)

    deep copy an object

.. function:: delattr(object, name)

    Delete a named attribute on an object.
    delattr(x, 'y') is equivalent to ``del x.y``.

.. function:: dict([mapping or iterable])

   create a dictionary: dict(key1=val1, key2=val2, ....)

.. function:: dir(object)

    return directory of an object -- thin wrapper about python builtin

.. function:: divmod(x, y)

    return the tuple ((x-x%y)/y, x%y).  Invariant: div*y + mod == x.

.. function:: enumerate(iterable[, start])

    iterator for index, value of iterable

    Return an enumerate object.  iterable must be another object that supports
    iteration.  The enumerate object yields pairs containing a count (from
    start, which defaults to zero) and a value yielded by the iterable argument.
    enumerate is useful for obtaining an indexed list:
    (0, seq[0]), (1, seq[1]), (2, seq[2]), ...

.. function:: filter(function or None, sequence)

    Return those items of sequence for which function(item) is true.  If
    function is None, return the items that are true.  If sequence is a tuple
    or string, return the same type, else return a list.

.. function:: float(x)

   Convert a string or number to a floating point number, if possible.

.. function:: format(value[, format_spec])

   Returns value.__format__(format_spec). format_spec defaults to ""

.. function:: frozenset(iterable)

   create frozenset: an immutable unordered collection of unique elements.

.. function:: get(object)

    get object from symbol table from symbol name

.. function:: getattr(object, name[, default])

    Get a named attribute from an object; getattr(x, 'y') is equivalent to x.y.
    When a default argument is given, it is returned when the attribute doesn't
    exist; without it, an exception is raised in that case.

.. function:: hasattr(object, name)

    Return whether the object has an attribute with the given name.
    (This is done by calling getattr(object, name) and catching exceptions.)

.. function:: hash(object)

    Return a hash value for the object.  Two objects with the same value have
    the same hash value.  The reverse is not necessarily true, but likely.

.. function:: hex(number)

   Return the hexadecimal representation of an integer or long integer.

.. function:: id(object)

    Return the identity of an object.  This is guaranteed to be unique among
    simultaneously existing objects.  (Hint: it's the object's memory address.)

.. function:: int(x[, base])

    Convert a string or number to an integer, if possible.  A floating point
    argument will be truncated towards zero (this does not include a string
    representation of a floating point number!)  When converting a string, use
    the optional base.  It is an error to supply a base when converting a
    non-string.  If base is zero, the proper base is guessed based on the
    string content.  If the argument is outside the integer range a
    long object will be returned instead.

.. function:: isinstance(object, class-or-type-or-tuple)

    Return whether an object is an instance of a class or of a subclass thereof.
    With a type as second argument, return whether that is the object's type.
    The form using a tuple, isinstance(x, (A, B, ...)), is a shortcut for
    isinstance(x, A) or isinstance(x, B) or ... (etc.).

.. function:: len(object)

    Return the number of items of a sequence or mapping.

.. function:: list()

    create a list
    list(iterable) -> new list initialized from iterable's items

.. function:: map(function, sequence[, sequence, ...])

    Return a list of the results of applying the function to the items of
    the argument sequence(s).  If more than one sequence is given, the
    function is called with an argument list consisting of the corresponding
    item of each sequence, substituting None for missing values when not all
    sequences have the same length.  If the function is None, return a list of
    the items of the sequence (or a list of tuples if more than one sequence).

.. function:: max(iterable[, key=func])

   max(a, b, c, ...[, key=func]) -> value

    With a single iterable argument, return its largest item.
    With two or more arguments, return the largest argument.

.. function:: min(iterable[, key=func]) -> value

   min(a, b, c, ...[, key=func]) -> value

    With a single iterable argument, return its smallest item.
    With two or more arguments, return the smallest argument.

.. function:: oct(number)

    Return the octal representation of an integer or long integer.

.. function:: open(name[, mode[, buffering]])

    Open a file, returning a file object

    The mode can be 'r', 'w' or 'a' for reading (default),
    writing or appending.  The file will be created if it doesn't exist
    when opened for writing or appending; it will be truncated when
    opened for writing.  Add a 'b' to the mode for binary files.
    Add a '+' to the mode to allow simultaneous reading and writing.
    If the buffering argument is given, 0 means unbuffered, 1 means line
    buffered, and larger numbers specify the buffer size.  The preferred way
    to open a file is with the builtin open() function.
    Add a 'U' to mode to open the file for input with universal newline
    support.  Any line ending in the input file will be seen as a '\n'
    in Python.  Also, a file so opened gains the attribute 'newlines';
    the value for this attribute is one of None (no newline read yet),
    '\r', '\n', '\r\n' or a tuple containing all the newline types seen.

    'U' cannot be combined with 'w' or '+' mode.

.. function:: ord(c)

    Return the integer ordinal of a one-character string.

.. function:: pow(x, y[, z])

    With two arguments, equivalent to x**y.  With three arguments,
    equivalent to (x**y) % z, but may be more efficient (e.g. for longs).

.. function:: range([start,] stop[, step])

    Return a list containing an arithmetic progression of integers.
    range(i, j) returns [i, i+1, i+2, ..., j-1]; start (!) defaults to 0.
    When step is given, it specifies the increment (or decrement).
    For example, range(4) returns [0, 1, 2, 3].  The end point is omitted!
    These are exactly the valid indices for a list of 4 elements.

.. function:: raw_input([prompt])

    Read a string from standard input.  The trailing newline is stripped.
    If the user hits EOF (Unix: Ctl-D, Windows: Ctl-Z+Return), raise EOFError.
    On Unix, GNU readline is used if enabled.  The prompt string, if given,
    is printed without a trailing newline before reading.

.. function:: reduce(function, sequence[, initial])

    Apply a function of two arguments cumulatively to the items of a sequence,
    from left to right, so as to reduce the sequence to a single value.
    For example, reduce(lambda x, y: x+y, [1, 2, 3, 4, 5]) calculates
    ((((1+2)+3)+4)+5).  If initial is present, it is placed before the items
    of the sequence in the calculation, and serves as a default when the
    sequence is empty.

.. function:: reload(module)

    reload a module, either larch or python

.. function:: repr(object)

    Return the canonical string representation of the object.
    For many primitive object types, eval(repr(object)) == object.

.. function:: reversed(sequence)

    Return a reverse iterator

.. function:: round(number[, ndigits])

    Round a number to a given precision in decimal digits (default 0 digits).
    This always returns a floating point number.  Precision may be negative.

.. function:: set(list)

    create a new set: a collection of unique elements.

.. function:: setattr(object, name, value)

    Set a named attribute on an object;

    setattr(x, 'y', v) is equivalent to ``x.y = v``.

.. function:: slice([start,] stop[, step])

    Create a slice object.  This is used for extended slicing (e.g. a[0:10:2]).

.. function:: sorted(iterable, cmp=None, key=None, reverse=False)

   return a new sorted list

.. function:: str(object)

    Return a nice string representation of the object.
    If the argument is a string, the return value is the same object.

.. function:: sum(sequence[, start])

    Returns the sum of a sequence of numbers (NOT strings) plus the value
    of parameter 'start' (which defaults to 0).  When the sequence is
    empty, returns start.

.. function:: tuple()

    tuple() -> empty tuple
    tuple(iterable) -> tuple initialized from iterable's items

    If the argument is a tuple, the return value is the same object.

.. function:: type(object)

   return the object's type
   type(name, bases, dict) -> a new type

.. function:: unichr(i)

    Return a Unicode string of one character with ordinal i; 0 <= i <= 0x10ffff.

.. function:: unicode(string [, encoding[, errors]])

    Create a new Unicode object from the given encoded string.
    encoding defaults to the current default string encoding.
    errors can be 'strict', 'replace' or 'ignore' and defaults to 'strict'.

.. function:: zip(seq1 [, seq2 [...]])

    Return a list of tuples, where each tuple contains the i-th element
    from each of the argument sequences.  The returned list is truncated
    in length to the length of the shortest argument sequence.

