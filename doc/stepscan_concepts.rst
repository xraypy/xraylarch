..  _scan_concepts-label:

=====================
Step Scan Concepts
=====================


A step scan is simply a **for loop** that iterates a collection of
**Positioners** (any Epics PV -- not restricted to Motors) through
a set of pre-determined position values.  At each position, a set
of detectors are **triggered** (which is to say, collection is
started), and then waited upon until they announce they are
complete.  At that point a collection of **Counters** (again, any
Epics PV, though for those holding waveform values see the notes
below) are read, and the loop starts over, moving on to the next
point in the list of positions.

A StepScan also contains several other components::
  *  extra_pvs: a set of PVs to record once (or a few times) for each
     scan, but not at every point in the scan.
  *  breakpoints: a series of points in the scan at which data collected
     so far is dumped to file, and perhaps other tasks are done.
  *  pre_scan: a set of functions to call just prior to beginning the scan.
  *  post_scan: a set of functions to call just after the scan completes.
  *  at_break: a set of functions to call at each breakpoint (after the
     data is written to disk).


Positioners
===============

Positioners are what is changed in the scan -- the dependent variables.
The can be represented by any Epics PV, such as Motors, temperatures,
currents, count times, or a combination of these.  Scans can have multiple
positioners, either moving in tandem to make a complex motion in the
positioner space, or independently to make a mesh in the positioner space.

In addition to a PV, each positioner will have an array of positions which
it should take during the scan.  The Positioner holds the full array
positions.  There are methods available for creating this from Start, Stop,
Step, and Npts parameters for simple linear scans, but you can also give it
a non-uniform array,

If you have multiple positioners, they must all have an array of positions
that is the same length.


Triggers
=============

A Trigger is something that starts a detector counting.  The general
assumption is that these start integrating detectors with a finite count
time (which may have been set prior to the scan, or set as one of the
Positioners).  The scan waits for these triggers to announce that they have
completed (ie, the Epics "put" has completed).  That means that not just
any PV can be used as a Trigger -- you really need a trigger that will
finish.

For many detectors using standard Epics Records (Scalers, MCAs,
multi-element MCAs, AreaDetectors), using a Detector (see below) will
include the appropriate Trigger.

Counters
=============

A Counter is any PV that you wish to measure at each point in the scan.

For many detectors using standard Epics Records (Scalers, MCAs,
multi-element MCAs, AreaDetectors), using a Detector (see below) will
automatically include a wide range of Counters.

Counters for waveforms
~~~~~~~~~~~~~~~~~~~~~~~~~


Currently, these are not directly supported, mostly as it is not yet
determined how to save this data into a plain ASCII file.  If more complex
file formats are used, these could be supported.

Note that a Trigger for an AreaDetector can be included, which
might cause it to save data through its own means.

Detectors
=============

Detectors are essentially a combination of Triggers and Counters that
represent a detector as defined by one of the common Epics detector
records.  These include Scalers, MCAs, multi-element MCAs, and
AreaDetectors.


Extra PVs
=============

Extra PVs are simply Epics PVs that should be recorded once (or
occasionally) during a scan, but but not at every point in the scan.  These
might include configuration information, detector and motor settings, and
ancillary data like temperatures, ring current, etc.

These should be supplied as a list of *(Label, PVname)* tuples.   The
values for these will be recorded at the beginning of each scan, and at
each breakpoint.


Breakpoints
===============

Breakpoints are points in the scan at which the scan pauses briefly to
to read values for Extra PVs, write out these and the data collected so far
to disk,  and run any other user-defined functions.

A typical short, one dimensional scan will not need any breakpoints -- the
data will be written at the end of the scan. On the other hand, a two
dimensional mesh scan may want to set a breakpoint at the end of each row,
so that the data collected to date can be read from the datafile.

To set breakpoints, just put the indices of the points to break after
(starting the counting from 0) into a `scan.breakpoints` list.

Users can add their own functions to be run at each breakpoint as well.


Pre- and Post-Scan functions
============================

These functions are run prior to and just after the scan has run.
Detectors and Positioners may add their own :func:`pre_scan` and 
:func:`post_scan` methods, for example to place a detector in the right
mode for scanning. 

