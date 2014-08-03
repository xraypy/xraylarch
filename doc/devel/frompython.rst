.. _frompython_section:


Using Larch from Python
===================================

Although Larch contains its own scripting language, this is not Python, and
it is perfectly reasonable to expect that the Larch analysis functionality
be available in Python without using the Larch scripting language at all.
That is, you may want to consider Larch to be a set of Python modules for
the analysis of X-ray spectroscopic and related data.  There are plenty of
good reasons to want to do this, and it is certainly possible.  However,
because Larch is intended for us independent of an installed Python system,
there are two points to keep in mind when using Larch from Python.

First, Larch keeps essentially all its functionality in plugins, which are
not installed into the standard Python tree of installed modules, but into
a folder specific to Larch.  This means that, while Larch can be used from
Python, Python will need to be told about where Larch is installed in order
for the ``import`` statements to work.

.. module:: larch

.. function:: use_plugin_path(folder_name)

    This python function will add the Plugin folder to Python's
    ``sys.path``, allowing python functions to be imported from the modules
    in the specified plugin folder.

    The argument is the subfolder for each plugin, relative to the
    installed Larch plugins (typically ``/usr/share/larch/plugins`` for
    Unix or Mac OSX or ``C:\Program Files\Larch\plugins`` on Windows).


Thus to get the :func:`_xafs.autobk` function into a Python module, you
would have to do::

    from larch import use_plugin_path
    use_plugin_path('xafs')
    from autobk import autobk


The second consideration is that many of the functions in the Larch plugins
will only work if they are passed an instance of the Larch interpreter.
This is primarily used inside Larch plugins to create Groups, or to access
data from the builtin ``_sys`` module, which requires a namespace (and
working interpreter).  Though you won't need to write Larch scripts inside
python (you **can**, but if you're reading this section, you probably want
to use Python instead of Larch), you probably will need an instance of the
interpreter.  This is easily created, and can then be passed to any of the
plugin functions with the ``_larch`` keyword argument.  Thus, while the
above use of :func:`use_plugin_path` was able to *find*
:func:`_xafs.autobk`, to actually use it, you'd have to pass in an instance
of a larch interpreter::

    from larch import use_plugin_path, Interpreter
    use_plugin_path('xafs')
    from autobk import autobk

    use_plugin_path('io')
    from xdi import read_xdi

    mylarch = Interpreter()
    data = read_xdi('feo_rt.xdi', _larch=mylarch)
    autobk(data, rbkg=1.0, kweight=2, _larch=mylarch)




