=======================================================
Tutorial: Running Larch Scripts, and Modules
=======================================================

Once you've done any significant amount of work with Larch, you'll want to
save what you've done to a file of Larch code, and run it over again,
perhaps changing some input.  There are a few ways to do this.  Writing
procedures that can be re-used is a highly recommended approach.


Running a script with run
==============================

If you have a file of Larch code, you can run it with the built-in **run**
function::

    # file  myscript.lar
    print 'hello from myscript.lar!
    for i in range(5):
       print i, sqrt(a)
    endfor
    #

To run this, you simply type::

    larch> run('myscript.lar')
    hello from myscript.lar!
    0 0.0
    1 1.0
    2 1.41421356237
    3 1.73205080757
    4 2.0

A script can contain any Larch code, including procedure definitions.
After running the script, any variables assigned in the script will exist
in your larch session.  For example, after the loop in *myscript.lar*, the
variable *i* will be 4, and  you can access this variable::

    larch> print i
    4

This is to say that the script runs in the "top-level namespace", about which
we'll see more below.

Importing a Larch Module
==============================

A larch script can also be **imported** using the **import** statement::

   larch> import myscript

Notice a few differences.  First, the '.lar' suffix was removed.  Second,
the name is **NOT IN QUOTES** as one my expect for a string containing a
file name.  This is because the **import** statement knows what extensions
to look for:

  * module lookup
  * import as..
  * from xx import yy as zz


Namespaces, again
==============================
