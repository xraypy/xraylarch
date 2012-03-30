#!/usr/bin/python
"""
Classes and Functions for simple step scanning for epics.

This does not used the Epics SScan Record, and the scan is intended to run
as a python application, but many concepts from the Epics SScan Record are
borrowed.  Where appropriate, the difference will be noted here.

A Step Scan consists of the following objects:
   a list of Positioners
   a list of Triggers
   a list of Counters

Each Positioner will have a list (or numpy array) of position values
corresponding to the steps in the scan.  As there is a fixed number of
steps in the scan, the position list for each positioners must have the
same length -- the number of points in the scan.  Note that, unlike the
SScan Record, the list of points (not start, stop, step, npts) must be
given.  Also note that the number of positioners or number of points is not
limited.

A Trigger is simply an Epics PV that will start a particular detector,
usually by having 1 written to its field.  It is assumed that when the
Epics ca.put() to the trigger completes, the Counters associated with the
triggered detector will be ready to read.

A Counter is simple a PV whose value should be recorded at every step in
the scan.  Any PV can be a Counter, including waveform records.  For many
detector types, it is possible to build a specialized class that creates
many counters.

Because Triggers and Counters are closely associated with detectors, a
Detector is also defined, which simply contains a single Trigger and a list
of Counters, and will cover most real use cases.

In addition to the core components (Positioners, Triggers, Counters, Detectors),
a Step Scan contains the following objects:

   breakpoints   a list of scan indices at which to pause and write data
                 collected so far to disk.
   extra_pvs     a list of PVs that are not recorded at each step in the
                 scan, but recorded at the beginning of scan, and at each
                 breakpoint, and to be recorded to disk file.
   pre_scan()    method to run prior to scan.
   post_scan()   method to run after scan.
   at_break()    method to run at each breakpoint.

Note that Postioners and Detectors may add their own pieces into extra_pvs,
pre_scan(), post_scan(), and at_break().

With these concepts, a Step Scan ends up being a fairly simple loop, going
roughly (that is, skipping error checking) as:

   pos = <DEFINE POSITIONER LIST>
   det = <DEFINE DETECTOR LIST>
   run_pre_scan(pos, det)
   [p.move_to_start() for p in pos]
   record_extra_pvs(pos, det)
   for i in range(len(pos[0].array)):
       [p.move_to_pos(i) for p in pos]
       while not all([p.done for p in pos]):
           time.sleep(0.001)
       [trig.start() for trig in det.triggers]
       while not all([trig.done for trig in det.triggers]):
           time.sleep(0.001)
       [det.read() for det in det.counters]

       if i in breakpoints:
           write_data(pos, det)
           record_exrta_pvs(pos, det)
           run_at_break(pos, det)
   write_data(pos, det)
   run_post_scan(pos, det)

Note that multi-dimensional mesh scans over a rectangular grid is not
explicitly supported, but these can be easily emulated with the more
flexible mechanism of unlimited list of positions and breakpoints.
Non-mesh scans are also possible.

A step scan can have an Epics SScan Record or StepScan database associated
with it.  It will use these for PVs to post data at each point of the scan.

"""

import time
from epics import PV


class StepScan(object):
    def __init__(self):
        self.pos_settle_time = 0
        self.pos_maxmove_time = 3600.0
        self.det_settle_time = 0
        self.det_maxcount_time = 86400.0
        self.extra_pvs = []
        self.positioners = []
        self.triggers = []
        self.counters = []
        self.breakpoints = []
        self.at_break_methods = []
        self.pre_scan_methods = []
        self.post_scan_methods = []
        self.verified = False

    def add_counter(self, counter, label=None):
        "add simple counter"
        if isinstance(counter, str):
            counter = Counter(counter, label)
        if isinstance(counter, Counter):
            self.counters.append(counter)
        else:
            print 'Cannot add Counter? ', counter
        self.verified = False

    def add_extra_pvs(self, pvs):
        """add extra pvs (list of pv names)"""
        if isinstance(pvs, str):
            self.extra_pvs.append(PV(pvs))
        else:
            self.extra_pvs.extend([PV(p) for p in pvs])

    def add_positioner(self, pos):
        """ add a Positioner """
        self.extra_pvs.extend(pos.extra_pvs)
        self.at_break_methods.extend(pos.at_break)
        self.post_scan_methods.extend(pos.post_scan)
        self.pre_scan_methods.extend(pos.pre_scan)
        self.verified = False

    def add_detector(self, det):
        """ add a Detector -- needs to be derived from Detector_Mixin"""
        self.extra_pvs.extend(det.extra_pvs)
        self.triggers.append(det.trigger)
        self.counters.extend(det.counters)
        self.at_break_methods.extend(det.at_break)
        self.post_scan_methods.extend(det.post_scan)
        self.pre_scan_methods.extend(det.pre_scan)
        self.verified = False

    def at_break(self, breakpoint=0):
        out = [m() for m in self.at_break_methods]
        self.read_extra_pvs()
        self.write_data(breakpoint=breakpoint)

    def pre_scan(self):
        return [m() for m in self.pre_scan_methods]

    def post_scan(self):
        return [m() for m in self.pre_scan_methods]

    def verify_scan(self):
        """ this does some simple checks of Scans, checking that
    the length of the positions array matches the length of the
    positioners array.

    For each Positioner, the max and min position is checked against
    the HLM and LLM field (if available)
    """
        npts = None
        self.error_message = ''
        for p in self.positioners:
            if not p.verify_array():
                self.error_message = 'Positioner %s array out of bounds' % p._pv.pvname
                return False
            if npts is None:
                npts = len(p.array)
            if len(p.array) != npts:
                self.error_message = 'Inconsistent positioner array length'
                return False
        return True

    def run(self):
        print 'run scan!'
        if not self.verify_scan():
            print 'Cannot execute scan -- out of bounds'
            return
        out = self.pre_scan()
        self.checkout_outputs(out)

        out = [p.move_to_start() for p in self.positions]
        self.checkout_outputs(out)

        self.open_datafile()
        self.read_extra_pvs()
        self.write_data(breakpoint=0)

        print 'len of positioner arrays ' , self.positioners[0].array
        npts = self.positioners[0].array
        for i in range(npts):
            [p.move_to_pos(i) for p in self.positioners]
        self.t0 = time.time()
        while (not all([p.done for p in pos]) and
               time.time() - self.t0 < self.pos_maxmove_time):
            time.sleep(0.001)
        time.sleep(self.pos_settle_time)
        [trig.start() for trig in self.triggers]
        self.t0 = time.time()
        while (not all([trig.done for trig in det.triggers]) and
               time.time() - self.t0 < self.det_maxcount_time):
               time.sleep(0.001)
        time.sleep(self.det_settle_time)
        [c.read() for c in self.counters]
        if i in breakpoints:
            self.at_break()

    self.write_data(closefile=True)

    def write_data(self, breakpoint=0, closefile=False):
        print 'write data!'
