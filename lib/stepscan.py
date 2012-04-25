#!/usr/bin/env python
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
   extra_pvs     a list of (description, PV) tuples that are recorded at
                 the beginning of scan, and at each breakpoint, to be
                 recorded to disk file as metadata.
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
from epics import PV, poll
from ordereddict import OrderedDict
from .detectors import Counter, DeviceCounter
from .outputfile import ASCIIScanFile

class StepScan(object):
    def __init__(self, datafile=None):
        self.pos_settle_time = 1.e-5
        self.pos_maxmove_time = 3600.0
        self.det_settle_time = 1.e-5
        self.det_maxcount_time = 86400.0
        self.extra_pvs = []
        self.positioners = []
        self.triggers = []
        self.counters = []
        self._det = []
        self.breakpoints = []
        self.at_break_methods = []
        self.pre_scan_methods = []
        self.post_scan_methods = []
        self.verified = False
        self.datafile = None
        self.abort = False
        if datafile is not None:
            self.datafile = ASCIIFile(filename=datafile)

        self.pos_actual  = []
        
    def add_counter(self, counter, label=None):
        "add simple counter"
        if isinstance(counter, str):
            counter = Counter(counter, label)
        if isinstance(counter, (Counter, DeviceCounter)):
            self.counters.append(counter)
        else:
            print 'Cannot add Counter? ', counter
        self.verified = False

    def add_extra_pvs(self, extra_pvs):
        """add extra pvs (tuple of (desc, pvname))"""
        if len(extra_pvs) == 0:
            return
        for desc, pvname in extra_pvs:
            if isinstance(pvname, str):
                pv = PV(pvname)
            else:
                pv = pvname
            self.extra_pvs.append((desc, pv))

    def add_positioner(self, pos):
        """ add a Positioner """
        self.add_extra_pvs(pos.extra_pvs)
        self.at_break_methods.append(pos.at_break)
        self.post_scan_methods.append(pos.post_scan)
        self.pre_scan_methods.append(pos.pre_scan)
        self.verified = False
        self.positioners.append(pos)
        
    def add_detector(self, det):
        """ add a Detector -- needs to be derived from Detector_Mixin"""
        self.add_extra_pvs(det.extra_pvs)
        self.triggers.append(det.trigger)
        self.counters.extend(det.counters)
        self._det.append(det)
        self.at_break_methods.append(det.at_break)
        self.post_scan_methods.append(det.post_scan)
        self.pre_scan_methods.append(det.pre_scan)
        self.verified = False

    def set_dwelltime(self, dtime):
        """set scan dwelltime per point to constant value"""
        for d in self._det:
            d.dwelltime = dtime
            
    def at_break(self, breakpoint=0):
        out = [m(breakpoint=breakpoint) for m in self.at_break_methods]
        if self.datafile is not None:
            self.datafile.write_data(breakpoint=breakpoint)

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
                self.error_message = 'Positioner %s array out of bounds' % p.pv.pvname
                return False
            if npts is None:
                npts = len(p.array)
            if len(p.array) != npts:
                self.error_message = 'Inconsistent positioner array length'
                return False
        return True

    def check_outputs(self, out, msg='unknown'):
        """ check outputs of a previous command"""
        for i in out:
            if i is not None and not i:
                raise Warning('error on output: %s' % msg)
        
    def read_extra_pvs(self):
        [pv.connect() for  (desc, pv) in self.extra_pvs]
        return [(desc, pv.pvname, pv.get()) for desc, pv in self.extra_pvs]
            
    def run(self, filename='test.dat'):
        if not self.verify_scan():
            print 'Cannot execute scan -- out of bounds'
            return
        out = self.pre_scan()
        self.check_outputs(out, msg='pre scan')
        
        orig_positions = [p.current() for p in self.positioners]

        out = [p.move_to_start() for p in self.positioners]
        self.check_outputs(out, msg='move to start')

        self.abort = False
        self.datafile = ASCIIScanFile(filename=filename,
                                      scan = self)
        self.datafile.write_data(breakpoint=0)
        npts = len(self.positioners[0].array)
        self.pos_actual  = []
        for i in range(npts):
            if self.abort:
                break
            [p.move_to_pos(i) for p in self.positioners]
            # wait for moves to finish
            t0 = time.time()
            while (not all([p.done for p in self.positioners]) and
                   time.time() - t0 < self.pos_maxmove_time):
                poll()
            # print  "  move done in %.4fs" % (time.time()-t0)
            time.sleep(self.pos_settle_time)
            # start triggers
            [trig.start(1) for trig in self.triggers]
            
            # wait for detectors to finish
            t0 = time.time()
            self.pos_actual.append([p.current() for p in self.positioners])
            while (not all([trig.done for trig in self.triggers]) and
                   time.time() - t0 < self.det_maxcount_time):
                poll(1.e-3, 0.05)
            # print 'triggers done! ', self.triggers, self.det_settle_time, len(self.counters)
            time.sleep(self.det_settle_time)
            [c.read() for c in self.counters]
            # print 'counters read ' , len(self.counters)

            if i in self.breakpoints:
                self.at_break(breakpoint=i)
                
        
        for val, pos in zip(orig_positions, self.positioners):
            pos.move_to(val, wait=False)
        
        self.datafile.write_data(breakpoint=-1, close_file=True)
        self.abort = False
        

