This directory contains plugins for Larch.  Larch Plugins are Python
functions that contain code (or data) that are loaded by the Larch
interpreter at runtime.  Plugins differ from Modules in that they are
automatically loaded and become part of the standard Larch environment.

On startup, the Larch interpreter will search all subdirectories of this
folder, and add plugin modules defined there.  The folders here ('std',
'math', 'xafs', 'xrf', 'xrfmap', etc) are mostly organized by scientific
technique, though there are some overlaps.  The 'local' subdirectory is
intentionally left empty and is intended for plugins local to this
installation or for experimental code.

A Plugin module is a Python module (that is, a file of Python code) that
contains a function named `registerLarchPlugin`.  This function takes no
arguments and must return a tuple of (module_name, dictionary) where the
dictionary has keys of Larch function names (to be placed in the
specified module) and Python functions.  An example plugin file:

    def func(x):
        return x*x/2.0

    def registerLarchPlugin():
        return ('mod', {'func': func})

will add the function `mod.func` to Larch.  You can also have a function
named `initializeLarchPlugin(_larch=None)`  which takes an instance of
the Larch intrepreter as an argument and runs initialization code.

Each plugin folder can have a 'requirements.txt' file that lists (one
per line) Python modules and versions required to use that plugin.  If
any of the requirements are not met, no attempt is made to load any of
the modules in that folder.  In this way, plugins can place more demands
on installed python packages than Larch does itself.
