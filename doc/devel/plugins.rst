.. _plugins_section:


Plugins
================

A Larch plugin is a Python module that adds functionality to Larch at
run-time.  Plugins are a powerful part of Larch that allow it to be
extended without the requiring detailed knowledge of all of Larch's
internals.  Generally speaking, plugins will define new functions or data
to become part of the Larch framework.  Functions defined in plugins can
access the Larch interpreter session, including creating or manipulating
Groups in Larch's symbol table.  Essentially all the scientific
functionality of Larch is implemented as plugins.

.. module:: larch

There are a few points to consider for writing plugins.  First, in order
for a plugin function to interact with the running Larch interpreter, it
needs a ``_larch`` keyword argument.  To be clear, the function does not
require a ``_larch`` keyword argument, but if the function does have a
``_larch`` keyword argument, it will be used to pass in the current larch
interpreter.  Normally, you will only really need the ``symtable``
attribute of the ``_larch`` variable which holds the symbol table used, but
you can interact with any part of the interpreter if you need to.

Second, all functions (or data resources) that are to be added to Larch
need to be *registered*.  This is done by defining a function called
:func:`registerLarchPlugin` that returns a tuple containing the name of the
group containing the added functions, and a dictionary with keys used for
the names to be put into the Larch symbol table, and values of the functions
or data to be used. of Larch symbol. A simple plugin module would
look like::

    def myfunc(x, y, _larch=None):
        # Note: larch instance passed in to '_larch'
        if _larch is None:
            return
	group = _larch.symtable.create_group(name='created by myfunc')

        group.x = x
	group.y = y
	group.z = 100
	return group

    def registerLarchPlugin(): # must have a function with this name!
        return ('mymod', {'func': myfunc})

This would create a top-level Larch group ``mymod`` (if it didn't already
exist), and create a function ``func`` in this group that held the python
function ``myfunc``.  To use this function from the Larch interpreter, you
would use something like::

    larch> out = mymod.func(12, 'a string')
    larch> print out.x, out.y, out.z
    12  'a string' 100

This plugin simply puts data into a Group, but of course you can do much
more complicated work inside the function.

.. function:: registerLarchPlugin():

   register a set of functions or data resources defined in the module into
   the current Larch interpreter.   This function should return a tuple of
   (GroupName, Symbols_Dictionary), where the Group name is the
   top-level Group to place the data in, and the Symbols dictionary maps
   the values (functions or data in the Python module) to names in the
   Larch Group.



Locations of Plugins
~~~~~~~~~~~~~~~~~~~~~~~~~

Plugins are meant to be long-lived and reused, and so are not expected to
be placed in the current working directory.  Plugins are located in the the
installed Larch Plugin folder ( $HOME/.larch/plugins/ on Unix or Mac OS X
or C:\\Users\\USERNAME\\larch\\plugins on Windows).

Plugins in the user's Larch Plugin folder can be added into the current
Larch session with the :func:`add_plugin` function.

.. function:: _builtin.add_plugin(python_file)

   add a plugin from the given plugin python file.  In contrast to the
   ``import`` statement, :func:`add_plugin` will install the resources
   defined by :func:`registerLarchPlugin` every time it is run.

   :param python_file:  name of Python file containing plugin code.
   :return:  ``True`` on success, ``False`` on error

If the above plugin file is saved in a file named `myplugin.py` in the
user's Larch Plugin folder, then doing::

   larch> add_plugin('myplugin')

will add a top-level group ``mymod`` with the ``func`` function, as described
above.  For commonly used plugins, the :func:`add_plugin` call can be added
to your startup script (`init.lar` in the User's Larch folder).  Since
:func:`registerLarchPlugin` is re-applied every time :func:`add_plugin` is
run, this provides a convenient way to develop and debug plugins.

Many plugins are installed into the Larch system folder.  These are
organized into sub-folders, and generally each plugin folder contains
mulitple files (modules) providing Larch functionality.


Customizing Plugins and  Folders of Plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Plugins are meant to be organized in folders.  The standard system plugins
have several folders, each with several functions.  Generally every file
(module) in the folder is treated as a plugin module, and if it has a
function :func:`registerLarchPlugin`, that will be run to place functions
in the Larch interpreter.

There are a few ways to control the plugins beyond the
:func:`registerLarchPlugin` function.  First, each module file can have a
:func:`initializeLarchPlugin` function that will be run immediately after
the plugin is registered to initialize plugin functionality.

.. function:: initializeLarchPlugin(_larch=None)

   initializes a Larch plugin.  If defined for a plugin, this function is
   run immediately after installing all the symbols.

.. index:: plugins.txt

Secondly, you may want to tell larch to look only at certain files within
the plugin folder for plugins.  To do this, simply include a file named
`plugins.txt` in the plugin folder that lists the files (one per line) to
use for plugins.


.. index:: requirements.txt

Finally, a Larch plugin may depend on third party Python modules that may
not be installed or available on all systems.  This should be considered
acceptable -- certain plugins may not work on all systems, but that
shouldn't cause problems for the other functionality.  To specify which
Python modules (and which versions of the modules), a particular plugin
depends on, you can include a file `requirements.txt` in the plugin folder
which contains the module name and version strings, one per line.  A
typical `requirements.txt` file might look like::

    epics>=3.1
    scipy>=0.13

to specify which modules and minimal versions for the plugin files in that
folder to work.  If these requirements are not satisfied, the modules will
not be installed.
