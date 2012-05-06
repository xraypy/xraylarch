=========================================
StepScan:  Epics Scans with Python
=========================================

StepScan is a library and (soon...) GUI application for running
simple to moderately complex step scans of Epics motors,
detectors, and general variables.  Many concepts are borrowed from
the Epics SScan record and from Spec, but neither of those are
used by StepScan -- the scans happen in the python client
application.

With Epics, nearly any Process Variable can be scanned or counted
during a scan, and so a Step Scan can be a fairly complex thing.
Fortunately, simple things are still easy to do.  A description of
some terms in the :ref:`scan_concepts-label` section may be
helpful.


.. toctree::
   :maxdepth: 2

   install
   concepts
   usage
   spec
   gui
