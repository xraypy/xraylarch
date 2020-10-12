.. _tutor-array_sec:

=====================================================
Basic Array Manipulation
=====================================================

.. _numpy: http://numpy.scipy.org/
.. _numpy documentation: http://docs.scipy.org/doc

Arrays are sequences of numerical data, with each element having the same
underlying data type -- integers, real (floating point) numbers, or complex
numbers.  Of course, arrays are very important for scientific data, and the
majority of data you will be manipulating with Larch will be in the form of
arrays.  Larch depends on the `numpy`_ library for providing basic array
data types and the methods for fast manipulation of array data.  These
arrays can be multi-dimensional, have their dimensionality change
dynamically, an can be sliced (subsets of elements taken).  Many built-in
functions will act on the whole array, generally element-by-element, in a
highly efficient way, greatly reducing the need to "loop over" elements.

This section introduces the creation, basic manipulation, and key
properties of arrays.  The discussion here is not exhaustive, but is
intended to get you far enough along to be able to manipulate arrays
sufficiently for most needs.  The `numpy documentation`_ is quite extensive
and well-written, and should be consulted for more details.

Functions for creating arrays
==============================

There are a handful of builtin functions for creating arrays from scratch.
These are listed in :ref:`Table of Array Creation Functions
<tutor_arraycreate_table>` In addition, when dealing with data stored in
files, reading the files (see :ref:`data-io_chapter`) with Larch will create
arrys for you.  Like lists, arrays are *mutable*.  That is, elements of
arrays can be changed without changing the rest of the array.

.. index:: array creation
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
    linspace             fill with bounds and N   arr = linspace(0, 1, 11)
    eye                  2-d identity matrix      arr = eye(3)
    meshgrid             2-d mesh arrays          mx, my = meshgrid(x, y)
  ==================== ========================= ===========================

Some examples of using these functions are needed::

    larch> i = arange(10)
    larch> i
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    larch> f = arange(10, dtype=float)
    larch> f
    array([0., 1., 2., 3., 4., 5., 6., 7., 8., 9.])
    larch> c = arange(10, dtype=complex)
    larch> c
    array([ 0.+0.j,  1.+0.j,  2.+0.j,  3.+0.j,  4.+0.j,  5.+0.j,  6.+0.j,
            7.+0.j,  8.+0.j,  9.+0.j])
    larch> i3 = eye(3)
    larch> i3
    array([[ 1.,  0.,  0.],
           [ 0.,  1.,  0.],
           [ 0.,  0.,  1.]])

Here, the **dtype** argument sets the data type for the array members.  For
example, ``float`` means a double precision floating point representation
of a real number and complex means double precision complex floating point.
The :ref:`Table of Array Data types <tutor_arraydtype_table>` below
lists the available data types that can be passed as a ``dtype`` argument.

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

The :func:`eye` function creates a 2 dimensional square array (or, possibly
``matrix``, though that term can connote additional meaning that a square
array does not necessarily have) with values of 1 for the diagonal
elements, and 0 elsewhere.

The function :func:`meshgrid` can be used to build a mesh of values from two one dimensional
arrays.  That is::

    larch> x = array([0, 1, 2, 3, 4])
    larch> y = array([-1, 0.5, 0, 0.5, 1])
    larch> mx, my = meshgrid(x, y)
    larch> print mx
    array([[0, 1, 2, 3, 4],
           [0, 1, 2, 3, 4],
           [0, 1, 2, 3, 4],
           [0, 1, 2, 3, 4],
           [0, 1, 2, 3, 4]])
    larch> print my
    array([[-1. , -1. , -1. , -1. , -1. ],
           [-0.5, -0.5, -0.5, -0.5, -0.5],
           [ 0. ,  0. ,  0. ,  0. ,  0. ],
           [ 0.5,  0.5,  0.5,  0.5,  0.5],
           [ 1. ,  1. ,  1. ,  1. ,  1. ]])

That is, the values of each ``mx`` and ``my`` contain the coordinates of a
two-dimensional mesh or map of the input ``x`` and ``y`` values.

The array *dtype* -- datatype
=================================

Arrays are sequences of numbers stored in memory to make access to the
elements of the arrays fast and memory use efficient.  As mentioned above,
each array will use one of several storage conventions depending on what
type of data is needed for the elements.  Basically, this dictates how many
bytes to use and whether these values are meant to hold integers, real
floating points, or complex floating point numbers. This information is
encapsulated in the arrays *dtype*.  It can be one of several values,
listed in the


.. index:: array dtype
.. _tutor_arraydtype_table:

   Table of Array Data types.  Each array has exactly one of these create
   arrays in Larch.  The **dtype** can be used in any of the array creation
   functions using the ``dtype`` keyword argument (e.g,
   ``dtype=float32``).

  ========================= ===================================================
   **dtype**                  **description**
  ========================= ===================================================
   bool                      boolean (``True`` or ``False``)
   int8                      signed 8-bit integer (-128 to 127)
   int16                     signed 16-bit integer (-32768 to 32767)
   int32                     signed 32-bit integer (-2**31 to 2**31-1)
   int64                     signed 64-bit integer  (-2**63 to 2**63-1)
   uint8                     unsigned 8-bit integer (0 to 255)
   uint16                    unsigned 16-bit integer (0 to 65535)
   uint32                    unsigned 32-bit integer (0 to 2**32)
   uint64                    unsigned 64-integer (0 to 2**64)
   float32                   single precision float
   float64 or float          double precision float
   complex64                 single precision complex two float32s
   complex128 or complex     double precision complex, two float64s.
  ========================= ===================================================



Basic array manipulation
===========================================

Arrays can either be used as a single object, or individual or ranges of elements can be extracted
from them.   Usually, mathematical operations and functions done to arrays are applied
element-by-element.  For example::

    larch>  x = arange(5)
    larch> print x
    [0 1 2 3 4]
    larch> print 2*x+1
    [1 3 5 7 9]

and so on for all of the basic mathematical operators.   To add to arrays of equal lengths
together is also easy::

    larch>  y = array([10, 12, 14, 16, 18])
    larch> print y - 3*x
    [10  9  8  7  6]

If the arrays are not of equal length, an exception is raised. In that case, you can take a sub-set
of the larger array to match the size of the smaller one.


Boolean operators also apply to each element, so that::

    larch> print y > 13
    [False False  True  True  True]

The :func:`any` and :func:`all` functions (in the tables below) can be used to determine if any or
all of the Boolean values are ``True``.


You can extract single elements from arrays with brackets, just as for lists::

    larch> print y[2]
    14
    larch> print (y-3*x)[2]
    7

which leads us to the next section.


Slicing and extracting sub-arrays
=====================================

An important aspect of arrays is that they can be treated as a single entity.  That is, ``sin(x)``
operates on each element of ``x``.  But sometimes it is necessary to get a particular element from
an array or work on only a selected part of an array.  To do these, one takes a sub-set of the array
-- a **slice**.  For extracting contiguous portions of 1-dimension arrays, this is pretty
straightforward, using the range of indices needed for the slice between square brackets ``[`` and
``]``.  For example::

    larch> arr = linspace(0, 2, 21)
    larch> print arr
    [ 0.   0.1  0.2  0.3  0.4  0.5  0.6  0.7  0.8  0.9  1.   1.1  1.2  1.3  1.4
      1.5  1.6  1.7  1.8  1.9  2. ]
    larch> print arr[20]
    2.0
    larch> print arr[15]
    1.5
    larch> print arr[10:15]
    [ 1.   1.1  1.2  1.3  1.4]

The general syntax for a slice is pretty complicated, but the simplest cases are straightforward.
As with lists, ``arr[i]`` selects value at index ``i`` (counting from 0).  Similarly, ``arr[i:j]``
selects elements starting at ``i`` and ending at (but not including -- see the example above)
``j``.  If ``i`` is omitted,
it is taken as 0 (the first element), and if ``j`` is omitted, it defaults to the last element of
the array.  In addition, if ``i`` and/or ``j`` are negative, they count from the end of the array::

    larch> print arr[:-8]
    [ 0.   0.1  0.2  0.3  0.4  0.5  0.6  0.7  0.8  0.9  1.   1.1  1.2]
    larch> print arr[-2:]
    [ 1.9  2.]

A slice can take a third argument ``k`` -- the stride -- which allows selection of every ``k``
elements.  That is::

    larch> print arr[1:6:2]
    [ 0.1  0.3  0.5]
    larch> print arr[::2]
    [ 0.   0.2  0.4  0.6  0.8  1.   1.2  1.4  1.6  1.8  2. ]

If ``k`` is negative, it starts from the end of the array::

    larch> print arr[::-3]
    [2.   1.7  1.4  1.1  0.8  0.5  0.2]


For mult-dimensional arrays, slices can be made for each dimension, with slices separated by
commas.  If no slice is given, the whole array along that dimension is used.  Thus::

    larch> x = arange(30).reshape((6, 5)
    larch> print x
    [[ 0  1  2  3  4]
     [ 5  6  7  8  9]
     [10 11 12 13 14]
     [15 16 17 18 19]
     [20 21 22 23 24]
     [25 26 27 28 29]]
    larch> print x[2]  # third row
    [10 11 12 13 14]
    larch> print x[:,1]  # second column
    [ 1  6 11 16 21 26]
    larch> print x[:3,2:5]
    [[ 2  3  4]
     [ 7  8  9]
     [12 13 14]]

Note that multi-dimensional arrays use a layout like C and unlike Fortran by default.  In addition
to the comma-based syntax shown above to extract different dimensions or use brackets around each
dimension::

    larch> print x[1][:4]  # second row, first 4 columns
    [5 6 7 8]
    larch> print x[1,:4]   # same
    [5 6 7 8]

In general, the syntax for a slice is then ``arr[i1:j1,:k1, i2:j2:k2, ...]`` with default values for ``i``
of 0, for ``j`` of the length of the array, and for ``k`` of 1.





Array attributes and methods
===========================================

Arrays have several useful attributes and methods.  As mentioned above, each array has a
:data:`dtype` attribute describing how its data is mapped in memory.  In addition, each
has a :data:`size` attribute giving the number of elements, a :data:`ndim` giving the
number of dimensions, and :data:`shape` giving the a tuple with the length along each
dimension.  The dimensionality and shape of a multi-dimensional array can be specified
by setting the value of :data:`shape` to the desired value::

    larch> x = arange(12, dtype=float)
    larch> x
    array([0., 1., 2., 3., 4., 5., 6., 7., 8., 9., 11., 12.])
    larch> x.shape = (2, 6)
    larch> x
    array([[ 0.,  1.,  2.,  3.,  4.,  5.],
           [ 6.,  7.,  8.,  9., 10., 11.]])


.. index:: array methods, array attributes
.. _tutor_arraymethods_table:

   Table of Array Attribute and Methods.  Those ending with parentheses (``()``) are
   methods, that act on the array.  Most of the attributes and the vast majority of
   methods return a value based on the array contents, leaving the array unchanged.  The
   attributes and methods marked ``read/write`` operate in place, changing the array.

  ===================== ========================================== ===============
   **attribute**           **description**                            **notes**
  ===================== ========================================== ===============
   dtype                  data type                                 read only
   size                   number of elements  (int)                 read only
   ndim                   number of dimensions (int)                read only
   shape                  length along each dimension (tuple)       read/write
   real                   real part of array                        read/write
   imag                   imaginary part of array                   read/write
   resize()               grow/shrink array to specified size       read/write

   conjugate()            conjugate of array
   all()                  boolean: if all values are ``True``       (non-zero)
   any()                  boolean: if any value is ``True``         (non-zero)
   min()                  minimum value of array elements
   max()                  maximum value of array elements
   mean()                 mean value of array elements
   std()                  standard deviation of array elements
   prod()                 product of array elements
   sum()                  sum of array elements
   argmin()               index of first minimum value
   argmax()               index of first maximum value
   argsort()              array of indices for sorted array          (min to max)
   cumprod()              array of cumulative product of elements
   cumsum()               array of cumulative sum of elements

   astype()               array re-cast as a different ``dtype``
   round()                array of rounded elements
   diagonal()             array of diagonal elements
   trace()                sum of diagonal elements()
   transpose()            transpose of array
   flatten()              array "flattened" to 1-dimension
   tolist()               list containing array elements
   reshape()              array reshaped to specified shape tuple
  ===================== ========================================== ===============


Mathematical functions for arrays
==========================================

Many of the basic mathemetical functions in larch automatically work on arrays
element-by-element.  For example, :func:`sqrt` returns the square-root of a single
value or for each element in an array::

    larch> print sqrt(3)
    1.73205080757
    larch> x = arange(10)
    larch> print sqrt(x)
    [ 0.          1.          1.41421356  1.73205081  2.          2.23606798
      2.44948974  2.64575131  2.82842712  3.        ]

The numpy library provides the underlying functions, and they are much faster than
looping over elements of the array::

    larch> for el in x:  # this is much slower than sqrt(x)!!
    .....>     print el, sqrt(el)
    .....> endfor
    0 0.0
    1 1.0
    2 1.41421356237
    3 1.73205080757
    4 2.0
    5 2.2360679775
    6 2.44948974278
    7 2.64575131106
    8 2.82842712475
    9 3.0

There are a large number of general purpose mathematical functions available in larch --
the ``_math`` group contains over 500 items on startup.  A partial list is given in the
The :ref:`Table of Array-aware Mathematical functions <tutor_arrayfuncs_table>` below.
What's more, many more are available by importing them from the scipy library.

.. index:: mathematical functions
.. _tutor_arrayfuncs_table:

   Table of Array-aware Mathematical functions.  More info on each of these can be found with the
   builtin :func:`help` function.  The table is broken up by categories to make printing easier.

  **General Purpose Functions**

  +-----------------+--------------------------------------------------------------+
  | **function**    |   **description**                                            |
  +=================+==============================================================+
  | all             |    all values are ``True``                                   |
  +-----------------+--------------------------------------------------------------+
  | allclose        |    all values of 2 arrays are close                          |
  +-----------------+--------------------------------------------------------------+
  | info            |    print information about array storage                     |
  +-----------------+--------------------------------------------------------------+
  | fabs            |    absolute value of values                                  |
  +-----------------+--------------------------------------------------------------+
  | sqrt            |    square root of values                                     |
  +-----------------+--------------------------------------------------------------+
  | exp             |    exponential of values                                     |
  +-----------------+--------------------------------------------------------------+
  | expm1           |    exp(x) - 1   for values x                                 |
  +-----------------+--------------------------------------------------------------+
  | exp2            |    2**x for values x                                         |
  +-----------------+--------------------------------------------------------------+
  | ln / log        |    natural logarithm of values                               |
  +-----------------+--------------------------------------------------------------+
  | log1p           |    log(x) + 1 for values x                                   |
  +-----------------+--------------------------------------------------------------+
  | log10           |    base-10 logarithm of values                               |
  +-----------------+--------------------------------------------------------------+
  | log2            |    base-2 logarithm of values                                |
  +-----------------+--------------------------------------------------------------+
  | mod             |    modulus of values                                         |
  +-----------------+--------------------------------------------------------------+
  | ldexp           |    x * 2**y for values x and y                               |
  +-----------------+--------------------------------------------------------------+
  | fmin            |    element-wise minima of two arrays                         |
  +-----------------+--------------------------------------------------------------+
  | fmax            |    element-wise maxima of two arrays                         |
  +-----------------+--------------------------------------------------------------+
  | fmod            |    element-wise modulus of two arrays                        |
  +-----------------+--------------------------------------------------------------+
  | frexp           |    split value into fractional and exponent                  |
  +-----------------+--------------------------------------------------------------+

  **Trigonometry Functions**

  +-----------------+--------------------------------------------------------------+
  | **function**    |   **description**                                            |
  +=================+==============================================================+
  | angle           |    phase angle for complex values                            |
  +-----------------+--------------------------------------------------------------+
  | acos  / arccos  |    inverse of cosine                                         |
  +-----------------+--------------------------------------------------------------+
  | asin  / arcsin  |    inverse of sine                                           |
  +-----------------+--------------------------------------------------------------+
  | atan  / arctan  |    inverse of tangent                                        |
  +-----------------+--------------------------------------------------------------+
  | atan2 / arctan2 |    inverse of tangent of ratio of two values                 |
  +-----------------+--------------------------------------------------------------+
  | acosh / arccosh |    inverse of hyperbolic cosine                              |
  +-----------------+--------------------------------------------------------------+
  | asinh / arcsinh |    inverse of hyperbolic sine                                |
  +-----------------+--------------------------------------------------------------+
  | atanh / arctanh |    inverse of hyperbolic tangent                             |
  +-----------------+--------------------------------------------------------------+
  | cos             |    cosine                                                    |
  +-----------------+--------------------------------------------------------------+
  | cosh            |    hyperbolic cosine                                         |
  +-----------------+--------------------------------------------------------------+
  | sin             |    sine                                                      |
  +-----------------+--------------------------------------------------------------+
  | sinh            |    hyperbolic sine                                           |
  +-----------------+--------------------------------------------------------------+
  | tan             |    tangent                                                   |
  +-----------------+--------------------------------------------------------------+
  | tanh            |    hyperbolic tangent                                        |
  +-----------------+--------------------------------------------------------------+
  | deg2rad         |    convert degrees to radians                                |
  +-----------------+--------------------------------------------------------------+
  | rad2deg         |    convert radians to degrees                                |
  +-----------------+--------------------------------------------------------------+
  | hypot           |  hypotenuse (distance) of two values                         |
  +-----------------+--------------------------------------------------------------+

  **Array Manipulation and Re-shaping**

  +-----------------+--------------------------------------------------------------+
  | **function**    |   **description**                                            |
  +=================+==============================================================+
  | append          |    append a value to an array                                |
  +-----------------+--------------------------------------------------------------+
  | insert          |  insert a value into a specified location of an array        |
  +-----------------+--------------------------------------------------------------+
  | concatenate     |  Join a sequence of arrays together                          |
  +-----------------+--------------------------------------------------------------+
  | tile            |  build array by repeating an array a number of times         |
  +-----------------+--------------------------------------------------------------+
  | repeat          |  repeat elements of an array a number of times               |
  +-----------------+--------------------------------------------------------------+
  |  split          |  Split array into sub-arrays vertically (row)                |
  +-----------------+--------------------------------------------------------------+
  |  hsplit         |  Split array into sub-arrays horizontally (column)           |
  +-----------------+--------------------------------------------------------------+
  |  dsplit         |  Split array into sub-arrays along the 3rd axixpth (depth)   |
  +-----------------+--------------------------------------------------------------+
  |  hstack         |  Stack arrays in sequence horizontally (column)              |
  +-----------------+--------------------------------------------------------------+
  |  vstack         |  Stack arrays in sequence vertically (row )                  |
  +-----------------+--------------------------------------------------------------+
  |  dstack         |  Stack arrays in sequence along third dimension (depth)      |
  +-----------------+--------------------------------------------------------------+
  | take            |  take values at specified indices                            |
  +-----------------+--------------------------------------------------------------+
  | choose          |  construct array from index array and a set of arrays        |
  +-----------------+--------------------------------------------------------------+
  | where           | select array elements depending on an input condition        |
  +-----------------+--------------------------------------------------------------+

  **Statistical Functions**

  +-----------------+--------------------------------------------------------------+
  | **function**    |   **description**                                            |
  +=================+==============================================================+
  | average         |   average value of an array, with optional weights           |
  +-----------------+--------------------------------------------------------------+
  | max             |  maximum value of an array                                   |
  +-----------------+--------------------------------------------------------------+
  | mean            |  mean value of an array                                      |
  +-----------------+--------------------------------------------------------------+
  | median          |  median value of an array                                    |
  +-----------------+--------------------------------------------------------------+
  | min             |  minimum value of an array                                   |
  +-----------------+--------------------------------------------------------------+
  | var             |  variance of an array                                        |
  +-----------------+--------------------------------------------------------------+
  | std             |  standard deviation of an array                              |
  +-----------------+--------------------------------------------------------------+
  | trapz           |  integrate using composite trapezoidal rule                  |
  +-----------------+--------------------------------------------------------------+
  | remainder       |  remainder of division (``x1 - floor(x1 / x2) * x2``)        |
  +-----------------+--------------------------------------------------------------+
  | percentile      |  returns the given  percentile of array elements             |
  +-----------------+--------------------------------------------------------------+
  | ceil            |  ceiling values (round "up") of input                        |
  +-----------------+--------------------------------------------------------------+
  | floor           |  floor values (round "down") of input                        |
  +-----------------+--------------------------------------------------------------+
  | round           |  round values (away from 0) of input                         |
  +-----------------+--------------------------------------------------------------+
  | clip            |  set upper/lower bounds on array values                      |
  +-----------------+--------------------------------------------------------------+
  | digitize        |  indices of bins for binned values                           |
  +-----------------+--------------------------------------------------------------+
  | bincount        |  number of occurrences of each value in array                |
  +-----------------+--------------------------------------------------------------+
  | histogram       |  build a histogram from an array                             |
  +-----------------+--------------------------------------------------------------+
  | histogram2d     |  build a 2-d histogram from two arrays                       |
  +-----------------+--------------------------------------------------------------+
  | convolve        |    discrete convolution of two 1-d arrays                    |
  +-----------------+--------------------------------------------------------------+
  | correlate       |    cross-correlation of two 1-d arrays                       |
  +-----------------+--------------------------------------------------------------+
  | cumprod         |    cumulative product                                        |
  +-----------------+--------------------------------------------------------------+
  | cumsum          |    cumulative sum                                            |
  +-----------------+--------------------------------------------------------------+

  **Multi-dimensional and Matrix Functions**

  +-----------------+--------------------------------------------------------------+
  | **function**    |   **description**                                            |
  +=================+==============================================================+
  | tril            | upper triagonal of an array                                  |
  +-----------------+--------------------------------------------------------------+
  | triu            | lower triagonal of an array                                  |
  +-----------------+--------------------------------------------------------------+
  | diagonal        | diagonal elements of an array                                |
  +-----------------+--------------------------------------------------------------+
  | trace           | sum of diagonal elements                                     |
  +-----------------+--------------------------------------------------------------+
  | dot             | dot product of two arrays                                    |
  +-----------------+--------------------------------------------------------------+
  | inner           | inner product of two arrays                                  |
  +-----------------+--------------------------------------------------------------+
  | outer           | outer product of two arrays                                  |
  +-----------------+--------------------------------------------------------------+
  | kron            | Kronecker product of two arrays                              |
  +-----------------+--------------------------------------------------------------+
  |  swapaxes       |  rotate axes of an array                                     |
  +-----------------+--------------------------------------------------------------+
  |  transpose      |  transpose array                                             |
  +-----------------+--------------------------------------------------------------+
  |  fliplr         |  Flip an array horizontally                                  |
  +-----------------+--------------------------------------------------------------+
  |  flipud         |  Flip an array vertically                                    |
  +-----------------+--------------------------------------------------------------+
  |  rot90          |  rotate an array 90 degrees counter clockwise                |
  +-----------------+--------------------------------------------------------------+

  **Array and Signal Processing**

  +-----------------+--------------------------------------------------------------+
  | **function**    |   **description**                                            |
  +=================+==============================================================+
  | diff            |    finite difference of array elements                       |
  +-----------------+--------------------------------------------------------------+
  | gradient        |    gradient of an array                                      |
  +-----------------+--------------------------------------------------------------+
  | interp          |    linear interpolation of 1-d arrays                        |
  +-----------------+--------------------------------------------------------------+
  | poly            | Evaluate a polynomial at a point                             |
  +-----------------+--------------------------------------------------------------+
  | root            | the roots of a polynomial                                    |
  +-----------------+--------------------------------------------------------------+
  | polyfit         | least squares polynomial fit                                 |
  +-----------------+--------------------------------------------------------------+

  **Random number generation and other**

  +-----------------+--------------------------------------------------------------+
  | **function**    |   **description**                                            |
  +=================+==============================================================+
  | random.random   |  randomly distributed reals, on [0, 1).                      |
  +-----------------+--------------------------------------------------------------+
  | random.randint  |  array of random integers, over specified range              |
  +-----------------+--------------------------------------------------------------+
  | random.normal   |  normally distributed random numbers                         |
  +-----------------+--------------------------------------------------------------+

  **Fourier transforms**

  +-----------------+--------------------------------------------------------------+
  | **function**    |   **description**                                            |
  +=================+==============================================================+
  | fft.fft         |  Fourier transform of a 1-d array                            |
  +-----------------+--------------------------------------------------------------+
  | fft.ifft        |  inverse Fourier transform of a 1-d array                    |
  +-----------------+--------------------------------------------------------------+
  | fft.fft2        |  Fourier transform of a 2-d array                            |
  +-----------------+--------------------------------------------------------------+
  | fft.ifft2       |  inverse Fourier transform of a 2-d array                    |
  +-----------------+--------------------------------------------------------------+


Many other functions that work on arrays are available from numpy subpackages and from scipy.
