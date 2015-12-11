.. _frompython_section:


Using Larch from Python
===================================

Although Larch contains its own scripting language, this is not Python, and
it is perfectly reasonable to expect that the Larch analysis functionality
be available in Python without using the Larch scripting language at all.
That is, you may want to consider Larch to be a set of Python modules for
the analysis of X-ray spectroscopic and related data.  There are plenty of
good reasons to want to do this, and it is certainly possible.  However,
because Larch is intended for use independent of an installed Python
system, there are two points to keep in mind when using Larch from Python.

First, Larch keeps essentially all its functionality in plugins, which are
*not* installed into the standard Python tree of installed modules, but
into a folder specific to Larch.  This means that, while Larch can be used
from Python, Python will need to be told about where Larch is installed in
order for the ``import`` statements to work.

.. module:: larch


.. function:: use_plugin_path(folder_name)

    add the named Plugin folder to Python's ``sys.path``, allowing python
    functions to be imported from the modules in the specified plugin folder.

    The argument is the subfolder for each plugin, relative to the
    installed Larch plugins (typically ``$HOME/.larch/plugins`` for
    Unix or Mac OSX or ``$USER\larch\plugins`` on Windows).

Thus to get the :func:`_xafs.autobk` function into a Python module, you
could do either::

    import larch
    from larch_plugins.xafs import autobk

or::

    from larch import use_plugin_path
    use_plugin_path('xafs')
    from autobk import autobk

The first approach is encouraged, the latter kept for backward compatibility.

The second consideration is that many of the functions in the Larch plugins
will only work if they are passed an instance of the Larch interpreter.
This interpreter instance is primarily used inside Larch plugins to create
Groups and place them in the current symbol table, or to access
data from the builtin ``_sys`` module  or from data resouces loaded into
the ``_xray`` module.
Though you won't need to write Larch scripts inside
python (you **can**, but if you're reading this section, you probably want
to use Python instead of Larch), you will need an instance of the
interpreter.  This is easily created, and can then be passed to any of the
plugin functions with the ``_larch`` keyword argument::

    from larch import Interpreter
    from larch_plugins.xafs import autobk
    from larch_plugins.io import read_xdi

    mylarch = Interpreter(with_plugins=False)
    dat = read_xdi('../xafsdata/fe3c_rt.xdi', _larch=mylarch)
    dat.mu = dat.mutrans
    autobk(dat, rbkg=1.0, kweight=2, _larch=mylarch)

That is, the ``_larch=mylarch`` argument is vital to having
:func:`_io.read_xdi` properly create a Larch group, and for allowing
:func:`_xafs.autobk` to do the actual fit, and organize the results.


Note that you can create the interpreter without loading all the plugins
using ``with_plugins=False``.  When running from python, this may be a
reasonable default.  If you want to add some of the plugins for a
particular interpreter session, you can::

    >>> import larch
    >>> session = larch.Interpreter(with_plugins=False)
    >>> session.add_plugin('xray')
    >>> session.run("cu_ka = xray_line('Cu', 'Ka1')")
    >>> session.symtable.cu_ka
    (8046.3, 0.577108, u'K', u'L3')

This would be nearly the same as doing::

    >>> import larch
    >>> from larch_plugins.xray import xray_line
    >>> session = larch.Interpreter(with_plugins=False)
    >>> xray_line('Cu', 'Ka1', _larch=session)
    (8046.3, 0.577108, u'K', u'L3')

except that the former Larch session retains the value in ``cu_ka``.
