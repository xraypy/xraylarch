This directory contains plugins for Larch.  Larch Plugins are Python
functions that contain code (or data) that are automatically loaded by the
Larch interpreter as it starts up and become part of the Larch session.

On startup, the Larch interpreter will search all subdirectories of this
folder, and add plugin modules defined there.  A Plugin module is a Python
module (that is, a file of Python code) that contains a function named
`registerLarchPlugin`.  This function takes no arguments and must return a
tuple of (module_name, dictionary) where the dictionary has keywordss of
Larch function names (to be placed in the specified module) and values of
the Python functions.

An example plugin file would look like this:

    def func(x):
        return x*x/2.0

    def registerLarchPlugin():
        return ('mod', {'func': func})

This will add the function `mod.func` to Larch.

You can also have a function named `initializeLarchPlugin(_larch=None)`
which takes an instance of the Larch intrepreter as an argument and runs
initialization code.

In addition, a plugin folder can have a 'requirements.txt' file that lists
(one per line) Python modules and versions required to use that plugin.  If
any of the requirements are not met, none of the modules in that folder
will be loaded.  In this way, plugins can place more demands on installed
python packages than Larch does itself.
