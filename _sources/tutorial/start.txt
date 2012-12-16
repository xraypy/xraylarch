=================================
Tutorial: Getting Started
=================================

This tutorial expects that you already have Larch installed and can run
either the program larch, basic Larch interpreter, or larch_gui, the
enhanced GUI interpreter::

   C:> larch
     Larch 0.9.17 (9-Dec-2012) M. Newville, T. Trainor
     using python 2.7.3, numpy 1.6.2, wx-enabled, wx version 2.9.4.0
   larch>


For Windows, you can start larch_gui or the larch shell program from the
Windows Start Menu.

As of this writing, the Larch GUI is little more than an enhanced command-line
shell, though it does include a "Data Browser" menu that allows you to view
a tree-like display of all the data in a Larch session, and to show help on
Larch functions.


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
also to hold the arguments to functions like :func:`sin`.

Variable names must start with a letter or underscore (_), followed by
any number of letters, underscores, or numbers.  You may notice that a dot
(.) may appear to be in many variable names.  This indicates an
*attribute*  of a variable -- we'll get to this in a later section.

If you're familiar with other programming langauges, an important point for
Larch (owing to its Python origins) is that variables are created
*dynamically*, they are not pre-defined to have some particular data type.
In fact, the a variable name (say, 'angle' above) can hold any type of
data, and its type can be changed easily::

    larch> angle = 'now I am a string'

Although the types of values for a variable can be changed dynamically,
values in Larch (Python) do have a definite and clear type, and conversion
between types is rigidly defined -- you can add an integer and a real
number to give a real number, but you cannot add a string and a real
number.   In fact, writing::

   larch> angle = asin(hc/(10000*2*d))*180/pi

is usually described as "create a variable 'angle' and set its value to the
result calculated (11.4...)".  For those used to working in C or Fortran,
in which variables are static and must be of a pre-declared type, this
description is a bit misleading.  A better way to think about it is that
the calculation on the right-hand-side of the equal sign results in a value
(11.4...) and we've assigned the name 'angle' to hold this value.  The
distinction may seem subtle, but it can have some profound results, as
we'll see in the following section when discussing lists and other dynamic
values.

