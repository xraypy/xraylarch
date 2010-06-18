.. xraylarch documentation master file, 


Documentation for Larch
=====================================

Larch is a set of tools 
writing to Epics Process Variables via the CA protocol. 

The Epics package consists of a fairly complete and *thin* interface to the
low-level CA library in the :mod:`ca` module that is base of all other
functionality.  The :mod:`PV` class provides a high-level `PV` object for
an object-oriented approach.  There is a very simple, functional approach
to CA similar to EZCA and the Unix command-line tools.  In addition, there
are classes for an epics :mod:`Device`, epics :mod:`Motor`, :mod:`Alarm`,
and special code for wxPython widgets.

For download, see  `PyEpics3 Home Page
<http://cars9.uchicago.edu/software/python/pyepics3/>`_.

This documentation is also available in  `PDF Format
<http://cars9.uchicago.edu/software/python/pyepics3/pyepics3.pdf>`_.


Contents:

.. toctree::
   :maxdepth: 3

   overview
   pv
   ca
   advanced
   devices
   wx
   installation
   
Indices and tables
~~~~~~~~~~~~~~~~~~~~~~

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


