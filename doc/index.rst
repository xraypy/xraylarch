==========================================================================
StepScan: Data Acquisition with Python and Epics Channel Access
==========================================================================

Epics StepScan is a library and (soon...) set of command-line and GUI
applications for data acquisition with Epics Channel Access using Python.
StepScan allows you to define and run step scans, in which a motorized
stage or other variable is changed through a set of pre-defined positions
(or steps), and a set of detectors are measured at each position.  By using
Epics Channel Access, nearly any motors, detectors, or Epics Process
Variable can be scanned or counted in a StepScan.  Using concepts are
borrowed from the Epics SScan record and from commonly used Spec software,
simple to moderately complex step scans can be built and run.  With
StepScan, the data collection happens in the python client, so that many
other python libraries and environments can be coupled with Epics StepScan.

Though StepScan allows nearly any Process Variable to be scanned or counted
during a scan, and thus allows scans to become quite complex, the StepScan
library and applications allow simple scans to still be simple to define
and run.  A description of some terms in the :ref:`scan_concepts-label`
section is given to clarify the concepts used in StepScan and this
documentation.   Examples of simple scans and some more complex scans are
given.

.. toctree::
   :maxdepth: 2

   install
   concepts
   usage
   spec
   gui
