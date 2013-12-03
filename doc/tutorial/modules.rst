=======================================================
Tutorial: Running Larch Scripts, and Modules
=======================================================

Once you've done any significant amount of work with Larch, you'll want to
save what you've done to a file of Larch code or a *script* and run it over
again, perhaps changing some input.  You may even want to write some
function that can be re-used -- this is highly recommended, and it reduces
the amount of text to maintain and find bugs in.

Once you have a Larch script, there are two ways to use it with Larch.
First, you can just run it as a script.  Alternatively, you can **import**
it into Larch.  The distinction can be subtle, and has to with where the
variables "live" within your larch session.  We'll discuss both
possibilities and their differences here.


Running a larch script with :func:`run`
========================================

If you have a Larch script, you can run it with the built-in :func:`run`
function::

    # file myscript.lar
    print 'hello from myscript.lar!'

    name = 'Fred'
    phi  = (sqrt(5)+1)/2

    for i in range(5):
       print i, sqrt(i)
    endfor
    # end of file myscript.lar

To run this, you simply type::

    larch> run('myscript.lar')
    hello from myscript.lar!
    0 0.0
    1 1.0
    2 1.41421356237
    3 1.73205080757
    4 2.0

Again, the script can contain any Larch code, including procedure
definitions.  After running the script, any variables assigned in the
script will exist in your larch session.  For example, running the above
script, there will be variables ``name``, ``phi``, and ``i`` (and ``i``
will hold the value 4), and you can access these:

    larch> print i, name, phi
    4 Fred 1.61803398875

These variables are held in the "top-level namespace", ``_main``, about which
we'll see more below.

Importing a Larch Script as a Module
========================================

The alternative method for using the script above is to **import** it, using the ``import`` statement::

    larch> import myscript
    0 0.0
    1 1.0
    2 1.41421356237
    3 1.73205080757
    4 2.0

Notice a few differences: First, the '.lar' suffix was removed.  Second,
the name is not in quotes.  The content of the file is still run, and the
``print`` statements still print output.  But now the variables ``name``,
``phi``, and ``i`` are held in a group named ``myscript``.  Compared to the
:func:`run` function  above, this provides better organization, as the
variable names are not in the top-level group, but in their own group.


The ``import`` statement is much more versatile than the :func:`run`
function.   First, the ``import`` statement looks for files with extensions
of ``.lar`` or ``.py``, so that you can import python modules (files of
python code) or larch scripts.

Second, it has a search path.



  * module lookup
  * import myscript as foo
  * from myscript import name
  * from myscript import name as othername


...

Namespaces, again
==============================

