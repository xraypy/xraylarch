.. _tutorial_modules_section:

=======================================================
Running Larch Scripts, and Modules
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
    print('hello from myscript.lar!')

    name = 'Fred'
    phi  = (sqrt(5)+1)/2

    for i in range(5):
       print(i, sqrt(i))
    #endfor
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
will hold the value 4), and you can access these::

    larch> print(i, name, phi)
    4 Fred 1.61803398875

These variables are held in the "top-level namespace", ``_main``, about which
we'll see more below.

Importing a Larch Script as a Module
========================================

The alternative method for using the script above is to **import** it,
using the ``import`` statement::

    larch> import myscript
    0 0.0
    1 1.0
    2 1.41421356237
    3 1.73205080757
    4 2.0

Notice a few differences: First, the '.lar' suffix was removed.  Second,
the name is not in quotes.  The content of the file is still run, and the
``print`` function still prints output.  But now the variables ``name``,
``phi``, and ``i`` are held in a group named ``myscript``.  Compared to the
:func:`run` function above, this provides better organization, as the
variable names are not in the top-level group, but in their own group,
named after the name of the module.


The ``import`` statement is more versatile than the :func:`run` function,
and has three important differences.  First, the ``import`` statement looks
for files with extensions of ``.lar`` or ``.py``, so that you can import
either larch scripts or any python module with the ``import statement``.
This is a subtle but highly important point: **any python module** can be
imported directly into Larch.

Second, you can control what is actually imported, and where it goes.  For
the above example with ``import myscript``, a group called ``myscript`` was
created, with variables ``name``, ``phi``, and ``i``.  If you want the
group called something else, or you want to not import everything, but only
selected elements (perhaps only one procedure or piece of data), you can
use variations on the standard Python ``import`` statement like::

    import myscript as mx

    from myscript import name, phi

    from myscript import name as my_name


The first of these will create a group ``mx`` with elements ``name``,
``phi``, and ``i``.  The second will copy the values of ``name`` and
``phi`` into the top group, and the last will copy the value of ``name`` to
the variable ``my_name`` in the top group.

The third important feature of ``import`` is that it will search for
modules outside of the current working directory.  For this, there is a
**search path** used to find larch modules.  The search path is held in the
system variable ``_sys.path``, and can thus be set during a larch session.
By default, this starts with the current working directory ('.'), and is
then followed by the user's Larch module directory, which will typically
``$HOME/.larch/modules`` on Unix or Mac OSX or ``$USER\larch\modules`` on
Windows.  If a file with the ``.lar`` extension is not found in one of
these three places, the standard Python rules for importing modules will be
used.
