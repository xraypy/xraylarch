=====================================================
Tutorial: Basic Array Manipulation
=====================================================

Functions for creating arrays
==============================



:ref:`Table of Array Creation Functions <tutor_arraycreate_table>`

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


The array *dtype* -- datatype
==============================


Slicing and extracting sub-arrays
=====================================



