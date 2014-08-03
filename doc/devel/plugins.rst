.. _plugins_section:


Plugins
================

Plugins are a powerful feature of Larch that allow it to be easily extended
without the requiring detailed knowledge of all of Larch's internals.  A
plugin is a specially written Python module that is meant to add
functionality to Larch at run-time.  Generally speaking, plugins will be
python modules which define new or customized versions of functions to
create or manipulate Groups.

Plugins need access to Larch's symbol table and need to tell Larch how to
use them.  To do this, each function to be added to Larch in a plugin
module needs a `_larch` keyword argument, which will be used to pass in the
instance of the current larch interpreter.  Normally, you will only need
the `symtable` attribute of the `_larch` variable, which is the symbol table
used.

In addition, all functions to be added to Larch need to be *registered*, by
defining a function call :func:`registerLarchPlugin` that returns a tuple
containing the name of the group containing the added functions, and a
dictionary of Larch symbol names and functions.  A simple plugin module
would look like::

    def _f1(x, y, _larch=None):  # Note:  larch instance passed in to '_larch'
        if _larch is None: return
	group = _larch.symtable.create_group(name='created by f1')

        setattr(group, 'x', x) # add symbols by "setting attributes"
        setattr(group, 'y', y)

	return group

    def registerLarchPlugin(): # must have a function with this name!
        return ('mymod', {'f1': _f1})

This is a fairly trivial example, simply putting data into a Group.  Of
course, the main point of a plugin is that you can do much more complicated
work inside the function.

If this is placed in a file called 'myplugin.py' in the larch plugins
folder (either $HOME/.larch/plugins/ or /usr/local/share/larch/plugins on
Unix, or C:\\Users\\ME\\larch\\plugins or C:\\Program Files\\larch\\plugins on
Windows), then::

   larch> add_plugin('myplugin')

will add a top-level group 'mymod' with an 'f1' function, so that::

   larch> g1 = mymod.f1(10, 'yes')
   larch> print g1
   <Group created by f1!>
   larch> print g1.x, g1.y
   (10, 'yes')

For commonly used plugins, the :func:`add_plugin` call can be added to your
startup script.
