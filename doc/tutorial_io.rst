=======================================================
Tutorial: Reading and Writing Data
=======================================================

Larch has several built-in functions for reading scientific data.  The
intention that the types of supported files will increase.  In addition,
many Python modules for reading standard image data can be used.


.. module:: _io
   :synopsis: Basic Input/Output Functions


Simple ASCII Column Files
============================

A simple way to store, and one that is widely used in the XAFS community,
is to store data in plaintext (ASCII encoded) data files, with whitespace
delimited numbers layed out as a table, with a fix number of columns and
rows indicated by newlines.   Typically a comment character such as "#" is
used to signify header information.  For instance::

   # room temperature FeO.
   # data from 20-BM, 2001, as part of NXS school
   #------------------------
   #   energy     xmu       i0
     6911.7671  -0.35992590E-01  280101.00
     6916.8730  -0.39081634E-01  278863.00
     6921.7030  -0.42193483E-01  278149.00
     6926.8344  -0.45165576E-01  277292.00
     6931.7399  -0.47365589E-01  265707.00

This file can be read with the builtin :func:`read_ascii` function.

.. function:: read_ascii(filename, ...)

   open and read an plaintext data file, returning a new Group.


Using HDF5 Files
========================

HDF5 is an increasingly popular data format for scientific data, as it can
efficiently hold very large arrays in a heirarchical format that holds
"metadata" about the data, and can be explored with a variety of tools.
