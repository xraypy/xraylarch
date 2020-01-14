.. _frompython_section:


Using Larch from Python
===================================


That is, you may want to consider Larch to be a set of Python modules for
the analysis of X-ray spectroscopic and related data.  There are plenty of
good reasons to want to do this, and it is certainly possible.  However,
because Larch is intended for use independent of an installed Python
system, there are two points to keep in mind when using Larch from Python.


Larch keeps essentially all its functionality in plugins, which are
*not* installed into the standard Python tree of installed modules, but
into a folder specific to Larch.  This means that, while Larch can be used
from Python, Python will need to be told about where Larch is installed in
order for the ``import`` statements to work.

.. module:: larch

Thus to get the :func:`_xafs.autobk` function into a Python module, you
could do either::

    from larch.xafs import autobk


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

    from larch.xafs import autobk
    from larch.io import read_xdi

    dat = read_xdi('../xafsdata/fe3c_rt.xdi')
    dat.mu = dat.mutrans
    autobk(dat, rbkg=1.0, kweight=2)

    from larch.xray import xray_line
    xray_line('Cu', 'Ka1')
    (8046.3, 0.577108, u'K', u'L3')
