.. _programming_chapter:

====================================
Programming with Larch from Python
====================================

This chapter describes some of the key concepts of programming with the
`larch` module from Python.  All the functionality described elsewhere in
this documentation is available from the `larch` Python module::

    import larch


A simple session might look like this::

    from larch.xafs import autobk
    from larch.io import read_xdi
    from wxmplot.interactive import plot

    dat = read_xdi('examples/xafsdata/fe3c_rt.xdi')
    dat.mu = dat.mutrans
    autobk(dat, rbkg=1.0, kweight=2)
    plot(dat.k, dat.k*dat.chi, xlabel='k 1/A', ylabel='chi*k')

    from larch.xray import xray_line
    print(xray_line('Cu', 'Ka1'))
    (8046.3, 0.577108, u'K', u'L3')


Larch submodules
============================

.. module:: larch

The `larch` module is broken up into a number of submodules, based mostly
on type of data being processed.
