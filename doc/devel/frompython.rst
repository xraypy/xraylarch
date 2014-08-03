.. _frompython_section:


Using Larch from Python
===================================

Larch can be considered a set of Python modules for the analysis of X-ray
spectroscopic and related data.  Because Larch is intended for use
independent of an installed Python system, the Larch plugins are not
installed into the standard Python tree of installed modules.  This means
that, while Larch can be used from Python, Python will need to be told
about where Larch is installed in order for the ``import`` statements to
work.
