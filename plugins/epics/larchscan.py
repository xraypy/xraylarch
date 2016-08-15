#!/usr/bin/env python
from __future__ import print_function

MODDOC = """
=== Epics Scanning Functions for Larch ===


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
import os, shutil
import time
from threading import Thread
import json
import numpy as np
import random
import six

from datetime import timedelta

from larch import Group, ValidateLarchPlugin
from larch.utils import debugtime
from larch_plugins.io import fix_varname

try:
    from epics import PV, caget, caput, get_pv, poll
    HAS_EPICS = True
except ImportError:
    HAS_EPICS = False

try:
    import epicsscan
    from epicsscan import (Counter, Trigger, AreaDetector, get_detector,
                           ASCIIScanFile, Positioner)
    from epicsscan.scandb import ScanDBException, ScanDBAbort

    from epics.devices.struck import Struck
    from epics.devices.xspress3 import Xspress3

    HAS_EPICSSCAN = True
except ImportError:
    HAS_EPICSSCAN = False


from larch_plugins.epics.xps_trajectory import XPSTrajectory

MODNAME = '_scan'

MIN_POLL_TIME = 1.e-3

XAFS_K2E = 3.809980849311092
HC       = 12398.4193
RAD2DEG  = 180.0/np.pi
MAXPTS   = 8192

class PVSlaveThread(Thread):
    """
    Sets up a Thread to allow a Master Index PV (say, an advancing channel)
    to send a Slave PV to a value from a pre-defined array.

    undulator = PVSlaveThread(master_pvname='13IDE:SIS1:CurrentChannel',
                              slave_pvname='ID13us:ScanEnergy')
    undulator.set_array(array_of_values)
    undulator.enable()
    # start thread
    undulator.start()

    # other code that may trigger the master PV

    # to finish, set 'running' to False, and join() thread
    undulator.running = False
    undulator.join()

    """
    def __init__(self, master_pvname=None,  slave_pvname=None, scan=None,
                 values=None, maxpts=8192, wait_time=0.05, dead_time=0.5,
                 offset=3):
        Thread.__init__(self)
        self.maxpts = maxpts
        self.offset = offset
        self.wait_time = wait_time
        self.dead_time = dead_time
        self.last_move_time = time.time() - 100.0
        self.pulse = -1
        self.last  = None
        self.scan = scan
        self.running = False
        self.vals = values
        if self.vals is None:
            self.vals  = np.zeros(self.maxpts)
        self.master = None
        self.slave = None
        if master_pvname is not None: self.set_master(master_pvname)
        if slave_pvname is not None: self.set_slave(slave_pvname)

    def set_master(self, pvname):
        self.master = PV(pvname, callback=self.onPulse)

    def set_slave(self, pvname):
        self.slave = PV(pvname)

    def onPulse(self, pvname, value=1, **kws):
        self.pulse  = max(0, min(self.maxpts, value + self.offset))

    def set_array(self, vals):
        "set array values for slave PV"
        n = len(vals)
        if n > self.maxpts:
            vals = vals[:self.maxpts]
        self.vals  = np.ones(self.maxpts) * vals[-1]
        self.vals[:n] = vals

    def enable(self):
        self.last = self.pulse = -1
        self.running = True

    def run(self):
        while self.running:
            time.sleep(self.wait_time)
            now = time.time()
            if (self.pulse > self.last and self.last is not None and
                (now - self.last_move_time) > self.dead_time):
                val = self.vals[self.pulse]
                if self.slave.write_access:
                    try:
                        self.slave.put(val)
                        self.last_move_time = time.time()
                    except:
                        print("PVFollow Put failed: ", self.slave.pvname , val)
                self.last = self.pulse
                if (self.scan is not None and self.pulse > 3 and self.pulse % 5 == 0):
                    npts = self.scan.npts
                    cpt = self.pulse
                    dtime = self.scan.dwelltime
                    if isinstance(dtime, list):
                        dtime = dtime[0]
                    time_left = (npts-cpt)*dtime
                    self.scan.set_info('scan_time_estimate', time_left)
                    time_est  = hms(time_left)
                    msg = 'Point %i/%i,  time left: %s' % (cpt, npts, time_est)
                    if cpt % self.scan.message_points == 0:
                        self.scan.write("%s\n" % msg)
                    self.scan.set_info('scan_progress', msg)
                    for c in self.scan.counters:
                        try:
                            c.buff = c.pv.get().tolist()
                        except:
                            pass
                        name = getattr(c, 'db_label', None)
                        if name is None:
                            name = c.label
                        c.db_label = fix_varname(name)
                        self.scan.scandb.set_scandata(c.db_label, c.buff)
                    self.scan.scandb.commit()


def etok(energy):
    return np.sqrt(energy/XAFS_K2E)

def ktoe(k):
    return k*k*XAFS_K2E

def energy2angle(energy, dspace=3.13555):
    omega   = HC/(2.0 * dspace)
    return RAD2DEG * np.arcsin(omega/energy)

def hms(secs):
    "format time in seconds to H:M:S"
    return str(timedelta(seconds=int(secs)))

class ScanMessenger(Thread):
    """ Provides a way to run user-supplied functions per scan point,
    in a separate thread, so as to not delay scan operation.

    Initialize a ScanMessenger with a function to call per point, and the
    StepScan instance.  On .start(), a separate thread will createrd and
    the .run() method run.  Here, this runs a loop, looking at the .cpt
    attribute.  When this .cpt changes, the executing will run the user
    supplied code with arguments of 'scan=scan instance', and 'cpt=cpt'

    Thus, at each point in the scan the scanning process should set .cpt,
    and the user-supplied func will execute.

    To stop the thread, set .cpt to None.  The thread will also automatically
    stop if .cpt has not changed in more than 1 hour
    """
    # number of seconds to wait for .cpt to change before exiting thread
    timeout = 3600.
    def __init__(self, func=None, scan=None,
                 cpt=-1, npts=None, func_kws=None):
        Thread.__init__(self)
        self.func = func
        self.scan = scan
        self.cpt = cpt
        self.npts = npts
        if func_kws is None:
            func_kws = {}
        self.func_kws = func_kws
        self.func_kws['npts'] = npts

    def run(self):
        """execute thread, watching the .cpt attribute. Any chnage will
        cause self.func(cpt=self.cpt, scan=self.scan) to be run.
        The thread will stop when .pt == None or has not changed in
        a time  > .timeout
        """
        last_point = self.cpt
        t0 = time.time()


        while True:
            poll(MIN_POLL_TIME, 0.25)
            if self.cpt != last_point:
                last_point =  self.cpt
                t0 = time.time()
                if self.cpt is not None and hasattr(self.func, '__call__'):
                    self.func(cpt=self.cpt, scan=self.scan,
                              **self.func_kws)
            if self.cpt is None or time.time()-t0 > self.timeout:
                return

class LarchStepScan(object):
    """
    Epics Step Scanning for Larch
    """
    def __init__(self, filename=None, auto_increment=True, _larch=None):
        self.pos_settle_time = MIN_POLL_TIME
        self.det_settle_time = MIN_POLL_TIME
        self.pos_maxmove_time = 3600.0
        self.det_maxcount_time = 86400.0
        self._larch = _larch
        self._scangroup =  _larch.symtable._scan
        self.scandb = None
        if getattr(self._scangroup, '_scandb', None) is not None:
            self.scandb = self._scangroup._scandb

        self.dwelltime = None
        self.comments = None

        self.filename = filename
        self.auto_increment = auto_increment
        self.filetype = 'ASCII'
        self.scantype = 'linear'

        self.verified = False
        self.abort = False
        self.pause = False
        self.inittime = 0 # time to initialize scan (pre_scan, move to start, begin i/o)
        self.looptime = 0 # time to run scan loop (even if aborted)
        self.exittime = 0 # time to complete scan (post_scan, return positioners, complete i/o)
        self.runtime  = 0 # inittime + looptime + exittime

        self.cpt = 0
        self.npts = 0
        self.complete = False
        self.debug = False
        self.message_points = 25
        self.extra_pvs = []
        self.positioners = []
        self.triggers = []
        self.counters = []
        self.detectors = []

        self.breakpoints = []
        self.at_break_methods = []
        self.pre_scan_methods = []
        self.post_scan_methods = []
        self.pos_actual  = []

    def set_info(self, attr, value):
        """set scan info to _scan variable"""
        setattr(self._scangroup, attr, value)
        if self.scandb is not None:
            self.scandb.set_info(attr, value)
            self.scandb.set_info('heartbeat', time.ctime())

    def open_output_file(self, filename=None, comments=None):
        """opens the output file"""
        creator = ASCIIScanFile
        # if self.filetype == 'ASCII':
        #     creator = ASCIIScanFile
        if filename is not None:
            self.filename = filename
        if comments is not None:
            self.comments = comments

        return creator(name=self.filename,
                       auto_increment=self.auto_increment,
                       comments=self.comments, scan=self)

    def add_counter(self, counter, label=None):
        "add simple counter"
        if isinstance(counter, six.string_types):
            counter = Counter(counter, label)
        if counter not in self.counters:
            self.counters.append(counter)
        self.verified = False

    def add_trigger(self, trigger, label=None, value=1):
        "add simple detector trigger"
        if trigger is None:
            return
        if isinstance(trigger, six.string_types):
            trigger = Trigger(trigger, label=label, value=value)
        if trigger not in self.triggers:
            self.triggers.append(trigger)
        self.verified = False

    def add_extra_pvs(self, extra_pvs):
        """add extra pvs (tuple of (desc, pvname))"""
        if extra_pvs is None or len(extra_pvs) == 0:
            return
        for desc, pvname in extra_pvs:
            if isinstance(pvname, PV):
                pv = pvname
            else:
                pv = get_pv(pvname)

            if (desc, pv) not in self.extra_pvs:
                self.extra_pvs.append((desc, pv))

    def add_positioner(self, pos):
        """ add a Positioner """
        self.add_extra_pvs(pos.extra_pvs)
        self.at_break_methods.append(pos.at_break)
        self.post_scan_methods.append(pos.post_scan)
        self.pre_scan_methods.append(pos.pre_scan)

        if pos not in self.positioners:
            self.positioners.append(pos)
        self.verified = False

    def add_detector(self, det):
        """ add a Detector -- needs to be derived from Detector_Mixin"""
        if det.extra_pvs is None: # not fully connected!
            det.connect_counters()

        self.add_extra_pvs(det.extra_pvs)
        self.at_break_methods.append(det.at_break)
        self.post_scan_methods.append(det.post_scan)
        self.pre_scan_methods.append(det.pre_scan)
        self.add_trigger(det.trigger)
        for counter in det.counters:
            self.add_counter(counter)

        if det not in self.detectors:
            self.detectors.append(det)
        self.verified = False

    def set_dwelltime(self, dtime=None):
        """set scan dwelltime per point to constant value"""
        if dtime is not None:
            self.dwelltime = dtime
        for d in self.detectors:
            d.set_dwelltime(self.dwelltime)

    def at_break(self, breakpoint=0, clear=False):
        out = [m(breakpoint=breakpoint) for m in self.at_break_methods]
        if self.datafile is not None:
            self.datafile.write_data(breakpoint=breakpoint)
        return out


    def pre_scan(self, **kws):
        if self.debug: print('Stepscan PRE SCAN ')
        for (desc, pv) in self.extra_pvs:
            pv.connect()

        out = []
        for meth in self.pre_scan_methods:
            out.append( meth(scan=self))
            time.sleep(0.1)

        for det in self.detectors:
            for counter in det.counters:
                self.add_counter(counter)

        prescan_proc = None
        try:
            prescan_proc = self._larch.symtable.get_symbol('pre_scan_command')
        except NameError:
            pass
        if prescan_proc is not None:
            if (isinstance(prescan_proc, Group) and
                hasattr(prescan_proc, 'pre_scan_command')):
                prescan_proc = prescan_proc.pre_scan_command
            try:
                ret = prescan_proc(scan=self)
            except:
                ret = None
            out.append(ret)
        return out

    def post_scan(self):
        if self.debug: print('Stepscan POST SCAN ')
        return [m() for m in self.post_scan_methods]

    def verify_scan(self):
        """ this does some simple checks of Scans, checking that
        the length of the positions array matches the length of the
        positioners array.

        For each Positioner, the max and min position is checked against
        the HLM and LLM field (if available)
        """
        npts = None
        for pos in self.positioners:
            if not pos.verify_array():
                self.set_error('Positioner {0} array out of bounds'.format(
                    pos.pv.pvname))
                return False
            if npts is None:
                npts = len(pos.array)
            if len(pos.array) != npts:
                self.set_error('Inconsistent positioner array length')
                return False
        return True


    def check_outputs(self, out, msg='unknown'):
        """ check outputs of a previous command
            Any True value indicates an error
        That is, return values must be None or evaluate to False
        to indicate success.
        """
        if not isinstance(out, (tuple, list)):
            out = [out]
        if any(out):
            raise Warning('error on output: %s' % msg)

    def read_extra_pvs(self):
        "read values for extra PVs"
        out = []
        for desc, pv in self.extra_pvs:
            out.append((desc, pv.pvname, pv.get(as_string=True)))
        return out

    def clear_data(self):
        """clear scan data"""
        for c in self.counters:
            c.clear()
        self.pos_actual = []

    def _messenger(self, cpt, npts=0, **kws):
        time_left = (npts-cpt)* (self.pos_settle_time + self.det_settle_time)
        if self.dwelltime_varys:
            time_left += self.dwelltime[cpt:].sum()
        else:
            time_left += (npts-cpt)*self.dwelltime
        self.set_info('scan_time_estimate', time_left)
        time_est  = hms(time_left)
        if cpt < 4:
            self.set_info('filename', self.filename)
        msg = 'Point %i/%i,  time left: %s' % (cpt, npts, time_est)
        if cpt % self.message_points == 0:
            self.write("%s\n" % msg)
        self.set_info('scan_progress', msg)

    def set_all_scandata(self):
        self.publishing_scandata = True
        for c in self.counters:
            name = getattr(c, 'db_label', None)
            if name is None:
                name = c.label
            c.db_label = fix_varname(name)
            self.scandb.set_scandata(c.db_label, c.buff)
        self.publishing_scandata = False

    def publish_scandata(self, wait=False):
        "post scan data to db"
        if self.scandb is None:
            return
        if wait:
            self.set_all_scandata()
        else:
            self.publish_thread = Thread(target=self.set_all_scandata)
            self.publish_thread.start()

    def set_error(self, msg):
        """set scan error message"""
        self._scangroup.error_message = msg
        if self.scandb is not None:
            self.set_info('last_error', msg)

    def set_scandata(self, attr, value):
        if self.scandb is not None:
            self.scandb.set_scandata(fix_varname(attr), value)

    def init_scandata(self):
        if self.scandb is None:
            return
        self.scandb.clear_scandata()
        self.scandb.commit()
        time.sleep(0.1)
        names = []
        npts = len(self.positioners[0].array)
        for p in self.positioners:
            try:
                units = p.pv.units
            except:
                units = 'unknown'

            name = fix_varname(p.label)
            if name in names:
                name += '_2'
            if name not in names:
                self.scandb.add_scandata(name, p.array.tolist(),
                                         pvname=p.pv.pvname,
                                         units=units, notes='positioner')
                names.append(name)
        for c in self.counters:
            try:
                units = c.pv.units
            except:
                units = 'counts'

            name = fix_varname(c.label)
            if name in names:
                name += '_2'
            if name not in names:
                self.scandb.add_scandata(name, [],
                                         pvname=c.pv.pvname,
                                         units=units, notes='counter')
                names.append(name)
        self.scandb.commit()

    def get_infobool(self, key):
        if self.scandb is None:
            return getattr(self._scan, key)
        return self.scandb.get_info(key, as_bool=True)

    def look_for_interrupts(self):
        """set interrupt requests:

        abort / pause / resume

        if scandb is being used, these are looked up from database.
        otherwise local larch variables are used.
        """
        self.abort  = self.get_infobool('request_abort')
        self.pause  = self.get_infobool('request_pause')
        self.resume = self.get_infobool('request_resume')
        return self.abort

    def write(self, msg):
        self._larch.writer.write(msg)

    def clear_interrupts(self):
        """re-set interrupt requests:

        abort / pause / resume

        if scandb is being used, these are looked up from database.
        otherwise local larch variables are used.
        """
        self.abort = self.pause = self.resume = False
        self.set_info('request_abort', 0)
        self.set_info('request_pause', 0)
        self.set_info('request_resume', 0)

    def run(self, filename=None, comments=None, debug=False):
        """ run the actual scan:
           Verify, Save original positions,
           Setup output files and messenger thread,
           run pre_scan methods
           Loop over points
           run post_scan methods
        """
        self.dtimer = dtimer = debugtime(verbose=debug)
        self.publishing_scandata = False
        self.publish_thread = None

        self.complete = False
        if filename is not None:
            self.filename  = filename
        if comments is not None:
            self.comments = comments
        self.pos_settle_time = max(MIN_POLL_TIME, self.pos_settle_time)
        self.det_settle_time = max(MIN_POLL_TIME, self.det_settle_time)

        ts_start = time.time()
        if not self.verify_scan():
            self.write('Cannot execute scan: %s' % self._scangroup.error_message)
            self.set_info('scan_message', 'cannot execute scan')
            return

        self.clear_interrupts()
        dtimer.add('PRE: cleared interrupts')
        orig_positions = [p.current() for p in self.positioners]

        out = [p.move_to_start(wait=False) for p in self.positioners]
        self.check_outputs(out, msg='move to start')


        npts = len(self.positioners[0].array)
        self.message_points = min(100, max(10, 25*round(npts/250.0)))
        self.dwelltime_varys = False
        if self.dwelltime is not None:
            self.min_dwelltime = self.dwelltime
            self.max_dwelltime = self.dwelltime
            if isinstance(self.dwelltime, (list, tuple)):
                self.dwelltime = np.array(self.dwelltime)
            if isinstance(self.dwelltime, np.ndarray):
                self.min_dwelltime = min(self.dwelltime)
                self.max_dwelltime = max(self.dwelltime)
                self.dwelltime_varys = True

        time_est = npts*(self.pos_settle_time + self.det_settle_time)
        if self.dwelltime_varys:
            time_est += self.dwelltime.sum()
            for d in self.detectors:
                d.set_dwelltime(self.dwelltime[0])
        else:
            time_est += npts*self.dwelltime
            for d in self.detectors:
                d.set_dwelltime(self.dwelltime)

        if self.scandb is not None:
            self.set_info('scan_progress', 'preparing scan')

        out = self.pre_scan()
        self.check_outputs(out, msg='pre scan')


        self.datafile = self.open_output_file(filename=self.filename,
                                              comments=self.comments)

        self.datafile.write_data(breakpoint=0)
        self.filename =  self.datafile.filename
        self.set_info('filename', self.filename)

        self.clear_data()
        if self.scandb is not None:
            self.init_scandata()
            self.set_info('request_abort', 0)
            self.set_info('scan_time_estimate', time_est)
            self.set_info('scan_total_points', npts)

        dtimer.add('PRE: wrote data 0')
        self.set_info('scan_progress', 'starting scan')
        #self.msg_thread = ScanMessenger(func=self._messenger, npts=npts, cpt=0)
        # self.msg_thread.start()
        self.cpt = 0
        self.npts = npts

        t0 = time.time()
        out = [p.move_to_start(wait=True) for p in self.positioners]
        self.check_outputs(out, msg='move to start, wait=True')
        [p.current() for p in self.positioners]
        [d.pv.get() for d in self.counters]
        i = -1
        ts_init = time.time()
        self.inittime = ts_init - ts_start
        dtimer.add('PRE: start scan')

        while not self.abort:
            i += 1
            if i >= npts:
                break
            try:
                point_ok = True
                self.cpt = i+1
                self.look_for_interrupts()
                dtimer.add('Pt %i : looked for interrupts' % i)
                while self.pause:
                    time.sleep(0.25)
                    if self.look_for_interrupts():
                        break
                # set dwelltime
                if self.dwelltime_varys:
                    for d in self.detectors:
                        d.set_dwelltime(self.dwelltime[i])
                # request move to next position
                [p.move_to_pos(i) for p in self.positioners]
                dtimer.add('Pt %i : move_to_pos (%i)' % (i, len(self.positioners)))
                # publish scan data while waiting for move to finish
                if i > 1 and not self.publishing_scandata:
                    self.publish_scandata()
                dtimer.add('Pt %i : publish data' % i)
                # wait for position move to finish
                t0 = time.time()
                mcount = 0
                while (not all([p.done for p in self.positioners]) and
                       time.time() - t0 < self.pos_maxmove_time):
                    if self.look_for_interrupts():
                        break
                    poll(10*MIN_POLL_TIME, 0.25)
                    mcount += 1
                # wait for positioners to settle
                dtimer.add('Pt %i : pos done' % i)
                # print 'Move completed in %.5f s, %i' % (time.time()-t0, mcount)
                time.sleep(self.pos_settle_time) # , 0.25)
                dtimer.add('Pt %i : pos settled (%.3f)' % (i, self.pos_settle_time))
                # start triggers, wait for them to finish
                [trig.start() for trig in self.triggers]
                dtimer.add('Pt %i : triggers fired, (%d)' % (i, len(self.triggers)))
                t0 = time.time()
                time.sleep(max(0.05, self.min_dwelltime/2.0))
                while not all([trig.done for trig in self.triggers]):
                    if (time.time() - t0) > 5.0*(1 + 2*self.max_dwelltime):
                        break
                    poll(MIN_POLL_TIME, 0.5)
                dtimer.add('Pt %i : triggers done' % i)
                if self.look_for_interrupts():
                    break
                point_ok = (all([trig.done for trig in self.triggers]) and
                            time.time()-t0 > (0.8*self.min_dwelltime))

                # for simulating random trigger errors:
                # point_ok = point_ok and (random.randint(1, 20) < 17)
                if not point_ok:
                    point_ok = True
                    time.sleep(0.25)
                    poll(0.1, 2.0)
                    for trig in self.triggers:
                        poll(10*MIN_POLL_TIME, 1.0)
                        point_ok = point_ok and (trig.runtime > (0.8*self.min_dwelltime))
                        if not point_ok:
                            print('Trigger problem?: ', trig, trig.runtime, self.min_dwelltime)
                            trig.abort()

                # wait, then read read counters and actual positions
                time.sleep(self.det_settle_time)
                dtimer.add('Pt %i : det settled done.' % i)
                [c.read() for c in self.counters]
                dtimer.add('Pt %i : read counters' % i)

                # self.cdat = [c.buff[-1] for c in self.counters]

                self.pos_actual.append([p.current() for p in self.positioners])
                dtimer.add('Pt %i : added positions' % i)

                # if a messenger exists, let it know this point has finished
                self._messenger(cpt=self.cpt, npts=npts)
                dtimer.add('Pt %i : sent message' % i)

                # if this is a breakpoint, execute those functions
                if i in self.breakpoints:
                    self.at_break(breakpoint=i, clear=True)

                dtimer.add('Pt %i: done.' % i)
                self.look_for_interrupts()

            except KeyboardInterrupt:
                self.set_info('request_abort', 1)
                self.abort = True
            if not point_ok:
                self.write('point messed up.  Will try again\n')
                time.sleep(0.25)
                for trig in self.triggers:
                    trig.abort()
                for det in self.detectors:
                    det.pre_scan(scan=self)
                i -= 1
            dtimer.add('Pt %i: joining publish thread.' % i)
            if self.publish_thread is not None:
                self.publish_thread.join()
            dtimer.add('Pt %i: completely done.' % i)

        # scan complete
        # return to original positions, write data
        dtimer.add('Post scan start')
        self.publish_scandata(wait=True)
        ts_loop = time.time()
        self.looptime = ts_loop - ts_init

        for val, pos in zip(orig_positions, self.positioners):
            pos.move_to(val, wait=False)
        dtimer.add('Post: return move issued')
        self.datafile.write_data(breakpoint=-1, close_file=True, clear=False)
        dtimer.add('Post: file written')
        if self.look_for_interrupts():
            self.write("scan aborted at point %i of %i." % (self.cpt, self.npts))
            raise ScanDBAbort("scan aborted")

        # run post_scan methods
        self.set_info('scan_progress', 'finishing')
        out = self.post_scan()
        self.check_outputs(out, msg='post scan')
        dtimer.add('Post: post_scan done')
        self.complete = True

        # end messenger thread
        # if self.msg_thread is not None:
        #      self.msg_thread.cpt = None
        #      self.msg_thread.join()

        self.set_info('scan_progress',
                      'scan complete. Wrote %s' % self.datafile.filename)
        ts_exit = time.time()
        self.exittime = ts_exit - ts_loop
        self.runtime  = ts_exit - ts_start
        dtimer.add('Post: fully done')

        # dtimer.show()

        return self.datafile.filename
        ##

    def write_fastmap_config(self, datafile, comments, mapper='13XRM:map:'):
        "write ini file for fastmap"
        if datafile is None: datafile = 'scan.001'
        if comments is None: comments = ''
        currscan = 'CurrentScan.ini'
        server  = self.scandb.get_info('server_fileroot')
        workdir = self.scandb.get_info('user_folder')
        basedir = os.path.join(server, workdir, 'Maps')
        if not os.path.exists(basedir):
            os.mkdir(basedir)
        sname = os.path.join(server, workdir, 'Maps', currscan)
        oname = os.path.join(server, workdir, 'Maps', 'PreviousScan.ini')

        if mapper is not None:
            caput('%sbasedir'  % mapper, basedir)
            caput('%sfilename' % mapper, datafile)
            caput('%sscanfile' % mapper, currscan)

        if os.path.exists(sname):
            shutil.copy(sname, oname)
        txt = ['# FastMap configuration file (saved: %s)'%(time.ctime()),
               '#-------------------------#',  '[scan]',
               'filename = %s' % datafile,
               'comments = %s' % comments]

        dim  = len(self.positioners)
        pos  = self.positioners[0]
        pospv = str(pos.pv.pvname)
        if pospv.endswith('.VAL'): pospv = pospv[:-4]
        arr  = pos.array
        ltim = self.dwelltime*(len(arr) - 1)
        txt.append('dimension = %i' % dim)
        txt.append('pos1 = %s'     % pospv)
        txt.append('start1 = %.4f' % arr[0])
        txt.append('stop1 = %.4f'  % arr[-1])
        txt.append('step1 = %.4f'  % (arr[1]-arr[0]))
        txt.append('time1 = %.4f'  % ltim)

        if dim > 1:
            pos = self.positioners[1]
            pospv = str(pos.pv.pvname)
            if pospv.endswith('.VAL'): pospv = pospv[:-4]
            arr = pos.array
            txt.append('pos2 = %s'   % pospv)
            txt.append('start2 = %.4f' % arr[0])
            txt.append('stop2 = %.4f' % arr[-1])
            txt.append('step2 = %.4f' % (arr[1]-arr[0]))

        txt.append('#------------------#')
        txt.append('[xrd_ad]')
        xrd_det = None
        for det in self.detectors:
            if isinstance(det, AreaDetector):
                xrd_det = det

        if xrd_det is None:
            txt.append('use = False')
        else:
            txt.append('use = True')
            txt.append('type = PEDET1')
            txt.append('prefix = %s' % det.prefix)
            txt.append('fileplugin = netCDF1:')
            # txt.append('fileplugin = %s' % det.file_plugin)


        f = open(sname, 'w')
        f.write('\n'.join(txt))
        f.close()
        return sname

    def epics_slewscan(self, filename='map.001', comments=None,
                       mapper='13XRM:map:'):
        """ request and what a slew-scan, executed with epics interface
        and separate fastmap collector....
        should be replaced!
        """
        self.write_fastmap_config(filename, comments, mapper=mapper)
        caput('%smessage' % mapper, 'starting...')
        caput('%sStart' % mapper, 1)

        self.clear_interrupts()
        self.set_info('scan_progress', 'starting')
        # watch scan
        # first, wait for scan to start (status == 2)
        collecting = False
        t0 = time.time()
        while not collecting and time.time()-t0 < 120:

            collecting = (2 == caget('%sstatus' % mapper))
            time.sleep(0.25)
            if self.look_for_interrupts():
                break
        if self.abort:
            caput("%sAbort" % mapper, 1)

        nrow = 0
        t0 = time.time()
        maxrow = caget('%smaxrow' % mapper)
        info = caget("%sinfo" % mapper, as_string=True)
        self.set_info('scan_progress', info)
        #  wait for scan to get past row 1
        while nrow < 1 and time.time()-t0 < 120:
            nrow = caget('%snrow' % mapper)
            time.sleep(0.25)
            if self.look_for_interrupts():
                break
        if self.abort:
            caput("%sAbort" % mapper, 1)

        maxrow  = caget("%smaxrow" % mapper)
        time.sleep(1.0)
        fname  = caget("%sfilename" % mapper, as_string=True)
        self.set_info('filename', fname)

        # wait for map to finish:
        # must see "status=Idle" for 10 consequetive seconds
        collecting_map = True
        nrowx, nrow = 0, 0
        t0 = time.time()
        while collecting_map:
            time.sleep(0.25)
            status_val = caget("%sstatus" % mapper)
            status_str = caget("%sstatus" % mapper, as_string=True)
            nrow       = caget("%snrow" % mapper)
            self.set_info('scan_status', status_str)
            time.sleep(0.25)
            if self.look_for_interrupts():
                break
            if nrowx != nrow:
                info = caget("%sinfo" % mapper, as_string=True)
                self.set_info('scan_progress', info)
                nrowx = nrow
            if status_val == 0:
                collecting_map = ((time.time() - t0) < 10.0)
            else:
                t0 = time.time()

        # if aborted from ScanDB / ScanGUI wait for status
        # to go to 0 (or 5 minutes)
        self.look_for_interrupts()
        if self.abort:
            caput('%sAbort' % mapper, 1)
            time.sleep(0.5)
            t0 = time.time()
            status_val = caget('%sstatus' % mapper)
            while status_val != 0 and (time.time()-t0 < 10.0):
                time.sleep(0.25)
                status_val = caget('%sstatus' % mapper)

        status_strg = caget('%sstatus' % mapper, as_string=True)
        self.set_info('scan_status', status_str)
        if self.abort:
            raise ScanDBAbort("slewscan aborted")
        return

class XAFS_Scan(LarchStepScan):
    """XAFS Scan"""
    def __init__(self, label=None, energy_pv=None, read_pv=None,
                 extra_pvs=None,  e0=0, _larch=None, **kws):
        self.label = label
        self.e0 = e0
        self.energies = []
        self.regions = []
        LarchStepScan.__init__(self, _larch=_larch, **kws)

        self.is_qxafs = False
        self.scantype = 'xafs'
        self.dwelltime = []
        self.energy_pos = None
        self.set_energy_pv(energy_pv, read_pv=read_pv, extra_pvs=extra_pvs)

    def set_energy_pv(self, energy_pv, read_pv=None, extra_pvs=None):
        self.energy_pv = energy_pv
        self.read_pv = read_pv
        if energy_pv is not None:
            self.energy_pos = Positioner(energy_pv, label='Energy',
                                         extra_pvs=extra_pvs)
            self.positioners = []
            self.add_positioner(self.energy_pos)
        if read_pv is not None:
            self.add_counter(read_pv, label='Energy_readback')

    def add_region(self, start, stop, step=None, npts=None,
                   relative=True, use_k=False, e0=None,
                   dtime=None, dtime_final=None, dtime_wt=1, min_estep=0.01):
        """add a region to an EXAFS scan.
        Note that scans must be added in order of increasing energy
        """
        if e0 is None:
            e0 = self.e0
        if dtime is None:
            dtime = self.dtime
        if min_estep < 0:
            min_estep = 0.01
        self.e0 = e0
        self.dtime = dtime

        if npts is None and step is None:
            print('add_region needs start, stop, and either step on npts')
            return

        if step is not None:
            npts = 1 + int(0.1  + abs(stop - start)/step)

        en_arr = list(np.linspace(start, stop, npts))

        self.regions.append((start, stop, npts, relative, e0,
                             use_k, dtime, dtime_final, dtime_wt))

        if use_k:
            en_arr = [e0 + ktoe(v) for v in en_arr]
        elif relative:
            en_arr = [e0 +    v    for v in en_arr]

        # check that all energy values in this region are
        # greater than previously defined regions
        en_arr.sort()
        min_energy = min_estep
        if len(self.energies) > 0:
            min_energy += max(self.energies)
        en_arr = [e for e in en_arr if e > min_energy]

        npts   = len(en_arr)

        dt_arr = [dtime]*npts
        # allow changing counting time linear or by a power law.
        if dtime_final is not None and dtime_wt > 0:
            _vtime = (dtime_final-dtime)*(1.0/(npts-1))**dtime_wt
            dt_arr= [dtime + _vtime *i**dtime_wt for i in range(npts)]
        self.energies.extend(en_arr)
        self.dwelltime.extend(dt_arr)
        if self.energy_pos is not None:
            self.energy_pos.array = np.array(self.energies)


class QXAFS_Scan(XAFS_Scan): # (LarchStepScan):
    """QuickXAFS Scan"""

    def __init__(self, label=None, energy_pv=None, read_pv=None,
                 extra_pvs=None, e0=0, _larch=None, **kws):

        self.label = label
        self.e0 = e0
        self.energies = []
        self.regions = []
        XAFS_Scan.__init__(self, label=label, energy_pv=energy_pv,
                           read_pv=read_pv, e0=e0, extra_pvs=extra_pvs,
                           _larch=_larch, **kws)

        self.is_qxafs = True
        self.scantype = 'xafs'
        qconf = self.scandb.get_config('QXAFS')
        qconf = self.qconf = json.loads(qconf.notes)

        self.xps = XPSTrajectory(qconf['host'],
                                 user=qconf['user'],
                                 password=qconf['passwd'],
                                 group=qconf['group'],
                                 positioners=qconf['positioners'],
                                 outputs=qconf['outputs'])


        self.set_energy_pv(energy_pv, read_pv=read_pv, extra_pvs=extra_pvs)

    def make_XPS_trajectory(self, reverse=False,
                            theta_accel=0.25, width_accel=0.25, **kws):
        """this method builds the text of a Trajectory script for
        a Newport XPS Controller based on the energies and dwelltimes"""

        qconf = self.qconf

        dspace = caget(qconf['dspace_pv'])
        height = caget(qconf['height_pv'])
        th_off = caget(qconf['theta_motor'] + '.OFF')
        wd_off = caget(qconf['width_motor'] + '.OFF')

        energy = np.array(self.energies)
        times  = np.array(self.dwelltime)
        if reverse:
            energy = energy[::-1]
            times  = times[::-1]

        traw    = energy2angle(energy, dspace=dspace)
        theta  = 1.0*traw
        theta[1:-1] = traw[1:-1]/2.0 + traw[:-2]/4.0 + traw[2:]/4.0
        width  = height / (2.0 * np.cos(theta/RAD2DEG))

        width -= wd_off
        theta -= th_off

        tvelo = np.gradient(theta)/times
        wvelo = np.gradient(width)/times
        tim0  = abs(tvelo[0] / theta_accel)
        the0  = 0.5 * tvelo[ 0] * tim0
        wid0  = 0.5 * wvelo[ 0] * tim0
        the1  = 0.5 * tvelo[-1] * tim0
        wid1  = 0.5 * wvelo[-1] * tim0

        dtheta = np.diff(theta)
        dwidth = np.diff(width)
        dtime  = times[1:]
        fmt = '%.8f, %.8f, %.8f, %.8f, %.8f'
        efirst = fmt % (tim0, the0, tvelo[0], wid0, wvelo[0])
        elast  = fmt % (tim0, the1, 0.00,     wid1, 0.00)

        buff  = ['', efirst]
        for i in range(len(dtheta)):
            buff.append(fmt % (dtime[i], dtheta[i], tvelo[i],
                               dwidth[i], wvelo[i]))
        buff.append(elast)

        return  Group(buffer='\n'.join(buff),
                      start_theta=theta[0]-the0,
                      start_width=width[0]-wid0,
                      theta=theta, tvelo=tvelo,   times=times,
                      energy=energy, width=width, wvelo=wvelo)


    def init_qscan(self, traj):
        """initialize a QXAFS scan"""

        qconf = self.qconf

        caput(qconf['id_track_pv'],  1)
        caput(qconf['y2_track_pv'],  1)

        time.sleep(0.1)
        caput(qconf['width_motor'] + '.DVAL', traj.start_width)
        caput(qconf['theta_motor'] + '.DVAL', traj.start_theta)
        # caput(qconf['id_track_pv'], 0)
        # caput(qconf['id_wait_pv'], 0)
        caput(qconf['y2_track_pv'], 0)


    def finish_qscan(self):
        """initialize a QXAFS scan"""
        qconf = self.qconf
        caput(qconf['id_track_pv'],  1)
        caput(qconf['y2_track_pv'],  1)
        time.sleep(0.1)

    def gathering2energy(self, text):
        """read gathering file, calculate and return
        energy and height. Gathering data is text with columns of
         Theta_Current, Theta_Set, Height_Current, Height_Set
        """
        angle, height = [], []
        for line in text.split('\n'):
            line = line[:-1].strip()
            if len(line) > 4:
                words = line[:-1].split()
                angle.append(float(words[0]))
                height.append(float(words[2]))
        angle  = np.array(angle)
        height = np.array(height)
        angle  = (angle[1:] + angle[:-1])/2.0
        height = (height[1:] + height[:-1])/2.0

        angle += caget(self.qconf['theta_motor'] + '.OFF')
        dspace = caget(self.qconf['dspace_pv'])
        energy = HC/(2.0 * dspace * np.sin(angle/RAD2DEG))
        return (energy, height)


    def run(self, filename=None, comments=None, debug=False, reverse=False):
        """
        run the actual QXAFS scan
        """
        print(" preparing QXAFS scan")
        self.complete = False
        if filename is not None:
            self.filename  = filename

        if comments is not None:
            self.comments = comments

        ts_start = time.time()
        if not self.verify_scan():
            self.write('Cannot execute scan: %s' % self._scangroup.error_message)
            self.set_info('scan_message', 'cannot execute scan')
            return

        qconf = self.qconf
        energy_orig = caget(qconf['energy_pv'])

        traj = self.make_XPS_trajectory(reverse=reverse)
        self.init_qscan(traj)

        idarray = 0.001*traj.energy + caget(qconf['id_offset_pv'])

        try:
            caput(qconf['id_drive_pv'], idarray[0], wait=False)
        except:
            pass
        caput(qconf['energy_pv'],  traj.energy[0], wait=False)

        self.xps.upload_trajectoryFile(qconf['traj_name'], traj.buffer)

        self.clear_interrupts()
        orig_positions = [p.current() for p in self.positioners]

        sis_prefix = qconf['mcs_prefix']
        und_thread = PVSlaveThread(master_pvname=sis_prefix+'CurrentChannel',
                                   slave_pvname=qconf['id_drive_pv'],
                                   scan=self)

        und_thread.set_array(idarray)
        und_thread.running = False

        npulses = len(traj.energy) + 1
        caput(qconf['energy_pv'], traj.energy[0], wait=True)
        try:
            caput(qconf['id_drive_pv'], idarray[0], wait=True, timeout=5.0)
        except:
            pass

        npts = len(self.positioners[0].array)
        self.dwelltime_varys = False
        dtime = self.dwelltime[0]

        self.set_info('scan_progress', 'preparing scan')
        extra_vals = []
        for desc, pv in self.extra_pvs:
            extra_vals.append((desc, pv.get(as_string=True), pv.pvname))

        xsp3_prefix = None
        scaler_prefix = None
        for d in self.detectors:
            if 'scaler' in d.label.lower():
                scaler_prefix = d.prefix
            elif 'xspress3' in d.label.lower():
                xsp3_prefix = d.prefix

        qxsp3 = Xspress3(xsp3_prefix)
        sis  = Struck(sis_prefix, scaler=scaler_prefix)
        qxsp3.Acquire = 0
        caput(qconf['energy_pv'], traj.energy[0])
        out = self.pre_scan()
        self.check_outputs(out, msg='pre scan')
        # replace Counters with Array Versions for QXAFS
        sis.stop()
        qxafs_counters = []
        for c in self.counters:
            qpv = None
            try:
                pvname = c.pv.pvname.replace('.VAL', '')
            except AttributeError:
                continue
            if pvname.startswith(scaler_prefix):
                pvname = pvname.replace(scaler_prefix, '')
                if '_calc' in pvname or '.S' in pvname:
                    jsca = int(pvname.replace('_calc', '').replace('.s', '')) - 1
                    qpv = sis.mcas[jsca]._pvs['VAL'].pvname
            elif pvname.startswith(xsp3_prefix):
                if 'MCA' in pvname and pvname.endswith('Total_RBV'):
                    qpv= pvname.replace('Total_RBV', 'TSTotal')
                elif 'SCA1' in pvname:
                    qpv = pvname.replace('Value_RBV', 'TSArrayValue')
            if qpv is not None:
                qxafs_counters.append(Counter(qpv, label=c.label))
        self.counters =qxafs_counters
        #######
        self.init_scandata()

        sis.ExternalMode()
        sis.NuseAll = MAXPTS
        sis.put('PresetReal', 0.0)
        sis.put('Prescale',   1.0)

        qxsp3.NumImages = MAXPTS
        qxsp3.ERASE  = 1
        qxsp3.useExternalTrigger()
        time.sleep(0.25)

        qxsp3.TimeSeriesCaptureOn(npts=npts+5)

        self.datafile = self.open_output_file(filename=self.filename,
                                              comments=self.comments)

        self.datafile.write_data(breakpoint=0)
        self.filename =  self.datafile.filename

        self.set_info('filename', self.filename)
        self.set_info('request_abort', 0)
        self.set_info('scan_time_estimate', npts*dtime)
        self.set_info('scan_total_points', npts)

        out = [p.move_to_start(wait=True) for p in self.positioners]
        self.check_outputs(out, msg='move to start, wait=True')

        caput(qconf['energy_pv'], traj.energy[0], wait=True)
        caput(qconf['width_motor'] + '.DVAL', traj.start_width, wait=True)
        caput(qconf['theta_motor'] + '.DVAL', traj.start_theta, wait=True)

        self.set_info('scan_progress', 'starting scan')
        self.cpt = 0
        self.npts = npts

        und_thread.enable()
        und_thread.start()
        time.sleep(0.1)


        ts_init = time.time()
        self.inittime = ts_init - ts_start
        start_time = time.strftime('%Y-%m-%d %H:%M:%S')

        self.xps.SetupTrajectory(npts+1, dtime, traj_file=qconf['traj_name'])

        sis.start()
        qxsp3.Acquire = 1
        time.sleep(0.1)

        self.xps.RunTrajectory()

        time.sleep(0.1)
        self.xps.EndTrajectory()

        sis.stop()
        qxsp3.Acquire = 0
        qxsp3.TimeSeriesCaptureOff()
        qxsp3.useInternalTrigger()

        self.finish_qscan()
        und_thread.running = False
        und_thread.join()
        self.set_info('scan_progress', 'reading data')

        npulses, gather_text = self.xps.ReadGathering()
        energy, height = self.gathering2energy(gather_text)
        self.pos_actual = []
        for e in energy:
           self.pos_actual.append([e])
        ne = len(energy)
        caput(qconf['energy_pv'], energy_orig-2.0)
        nout = sis.CurrentChannel
        narr = 0
        t0  = time.time()
        while narr < (nout-1) and (time.time()-t0) < 15.0:
            time.sleep(0.1)
            narr = nout
            for c in qxafs_counters:
                if len(c.buff) < ne:
                    dat = c.read(timeout=5.0)
                try:
                    ndat = np.array(dat).size
                except:
                    ndat = 0
                narr = min(ndat, narr)

        for c in qxafs_counters:
            dat = c.read()
            dat = np.array(dat).squeeze()
            if len(dat) > ne:
                dat = dat[-ne:]
            c.buff = dat.tolist()
        self.set_info('scan_progress', 'publishing data')
        self.publish_scandata(wait=True)
        for val, pos in zip(orig_positions, self.positioners):
            pos.move_to(val, wait=False)

        self.datafile.write_data(breakpoint=-1, close_file=True, clear=False)
        if self.look_for_interrupts():
            self.write("scan aborted at point %i of %i." % (self.cpt, self.npts))
            raise ScanDBAbort("scan aborted")

        # run post_scan methods
        self.set_info('scan_progress', 'finishing')
        caput(qconf['energy_pv'], energy_orig, wait=True)
        out = self.post_scan()
        self.check_outputs(out, msg='post scan')
        self.complete = True
        self.set_info('scan_progress',
                      'scan complete. Wrote %s' % self.datafile.filename)
        self.runtime  = time.time() - ts_start
        return self.datafile.filename
        ##

@ValidateLarchPlugin
def scan_from_json(text, filename='scan.001', current_rois=None,
                   is_qxafs=False, _larch=None):
    """(PRIVATE)

    creates and returns a LarchStepScan object from a json-text
    representation.

    """
    sdict = json.loads(text)
    #
    # create positioners
    if sdict['type'] == 'xafs':
        min_dtime = sdict['dwelltime']
        if isinstance(min_dtime, np.ndarray):
            min_dtime = min(dtime)
        is_qxafs = (is_qxafs or
                    sdict.get('is_qxafs', False) or
                    (min_dtime < 0.45))
        kwargs = dict(energy_pv=sdict['energy_drive'],
                      read_pv=sdict['energy_read'],
                      e0=sdict['e0'], _larch=_larch)

        if is_qxafs:
            scan = QXAFS_Scan(**kwargs)
            sdict['time_kw'] = 0
            sdict['max_time'] = 0
        else:
            scan = XAFS_Scan(**kwargs)
            pos_stime = min(0.1, sdict.get('pos_settle_time', 0.1))
            sdict['pos_settle_time'] = pos_stime

        t_kw  = sdict['time_kw']
        t_max = sdict['max_time']
        nreg  = len(sdict['regions'])
        for i, det in enumerate(sdict['regions']):
            start, stop, npts, dt, units = det
            kws  = {'relative': sdict['is_relative']}
            kws['dtime'] =  dt
            kws['use_k'] =  units.lower() !='ev'
            if i == nreg-1: # final reg
                if t_max > dt and t_kw>0 and kws['use_k']:
                    kws['dtime_final'] = t_max
                    kws['dtime_wt'] = t_kw
            scan.add_region(start, stop, npts=npts, **kws)
    else:
        scan = LarchStepScan(filename=filename, _larch=_larch)
        if sdict['type'] == 'linear':
            for pos in sdict['positioners']:
                label, pvs, start, stop, npts = pos
                p = Positioner(pvs[0], label=label)
                p.array = np.linspace(start, stop, npts)
                scan.add_positioner(p)
                if len(pvs) > 0:
                    scan.add_counter(pvs[1], label="%s_read" % label)

        elif sdict['type'] == 'mesh':
            label1, pvs1, start1, stop1, npts1 = sdict['inner']
            label2, pvs2, start2, stop2, npts2 = sdict['outer']
            p1 = Positioner(pvs1[0], label=label1)
            p2 = Positioner(pvs2[0], label=label2)

            inner = npts2* [np.linspace(start1, stop1, npts1)]
            outer = [[i]*npts1 for i in np.linspace(start2, stop2, npts2)]

            p1.array = np.array(inner).flatten()
            p2.array = np.array(outer).flatten()
            scan.add_positioner(p1)
            scan.add_positioner(p2)
            if len(pvs1) > 0:
                scan.add_counter(pvs1[1], label="%s_read" % label1)
            if len(pvs2) > 0:
                scan.add_counter(pvs2[1], label="%s_read" % label2)

        elif sdict['type'] == 'slew':
            label1, pvs1, start1, stop1, npts1 = sdict['inner']
            p1 = Positioner(pvs1[0], label=label1)
            p1.array = np.linspace(start1, stop1, npts1)
            scan.add_positioner(p1)
            if len(pvs1) > 0:
                scan.add_counter(pvs1[1], label="%s_read" % label1)
            if sdict['dimension'] >=2:
                label2, pvs2, start2, stop2, npts2 = sdict['outer']
                p2 = Positioner(pvs2[0], label=label2)
                p2.array = np.linspace(start2, stop2, npts2)
                scan.add_positioner(p2)
                if len(pvs2) > 0:
                    scan.add_counter(pvs2[1], label="%s_read" % label2)
    # detectors
    rois = sdict.get('rois', current_rois)
    scan.rois = rois

    for dpars in sdict['detectors']:
        dpars['rois'] = rois
        scan.add_detector(get_detector(**dpars))

    # extra counters (not-triggered things to count
    if 'counters' in sdict:
        for label, pvname  in sdict['counters']:
            scan.add_counter(pvname, label=label)

    # other bits
    scan.add_extra_pvs(sdict['extra_pvs'])
    scan.scantype = sdict.get('type', 'linear')
    scan.scantime = sdict.get('scantime', -1)
    scan.filename = sdict.get('filename', 'scan.dat')
    if filename is not None:
        scan.filename  = filename
    scan.pos_settle_time = sdict.get('pos_settle_time', 0.1)
    scan.det_settle_time = sdict.get('det_settle_time', 0.01)
    scan.nscans          = sdict.get('nscans', 1)
    if scan.dwelltime is None:
        scan.set_dwelltime(sdict.get('dwelltime', 1))
    return scan

@ValidateLarchPlugin
def scan_from_db(name, filename='scan.001', timeout=5.0, is_qxafs=False,
                 _larch=None):
    """(PRIVATE)

    get scan definition from ScanDB

    timeout is for db lookup
    """
    if _larch.symtable._scan._scandb is None:
        return
    sdb = _larch.symtable._scan._scandb
    current_rois = json.loads(sdb.get_info('rois'))
    t0 = time.time()
    while time.time()-t0 < timeout:
        scandef = sdb.get_scandef(name)
        if scandef is not None:
            break
        time.sleep(0.25)

    if scandef is None:
        raise ScanDBException("no scan definition '%s' found" % name)

    return scan_from_json(scandef.text, filename=filename,
                          is_qxafs=is_qxafs,
                          current_rois=current_rois, _larch=_larch)


@ValidateLarchPlugin
def do_scan(scanname, filename='scan.001', nscans=1, comments='', _larch=None):
    """do_scan(scanname, filename='scan.001', nscans=1, comments='')

    execute a step scan as defined in Scan database

    Parameters
    ----------
    scanname:     string, name of scan
    filename:     string, name of output data file
    comments:     string, user comments for file
    nscans:       integer (default 1) number of repeats to make.

    Examples
    --------
      do_scan('cu_xafs', 'cu_sample1.001', nscans=3)

    Notes
    ------
      1. The filename will be incremented so that each scan uses a new filename.
    """

    if _larch.symtable._scan._scandb is None:
        print('need to connect to scandb!')
        return
    scandb =  _larch.symtable._scan._scandb
    if nscans is not None:
        scandb.set_info('nscans', nscans)

    scan = scan_from_db(scanname, filename=filename,
                        _larch=_larch)
    scan.comments = comments
    if scan.scantype == 'slew':
        return do_slewscan(scanname, filename=filename, nscans=nscans,
                           comments=comments, _larch=_larch)
    else:
        scans_completed = 0
        nscans = int(scandb.get_info('nscans'))
        abort  = scandb.get_info('request_abort', as_bool=True)
        while (scans_completed  < nscans) and not abort:
            scan.run()
            scans_completed += 1
            nscans = int(scandb.get_info('nscans'))
            abort  = scandb.get_info('request_abort', as_bool=True)
        return scan

@ValidateLarchPlugin
def do_slewscan(scanname, filename='scan.001', comments='',
                nscans=1, _larch=None):
    """do_slewscan(scanname, filename='scan.001', nscans=1, comments='')

    execute a slewscan as defined in Scan database

    Parameters
    ----------
    scanname:     string, name of scan
    filename:     string, name of output data file
    comments:     string, user comments for file
    nscans:       integer (default 1) number of repeats to make.

    Examples
    --------
      do_slewscan('small_map', 'map.001')

    Notes
    ------
      1. The filename will be incremented so that each scan uses a new filename.
    """

    if _larch.symtable._scan._scandb is None:
        print('need to connect to scandb!')
        return
    scan = scan_from_db(scanname, _larch=_larch)
    if scan.scantype != 'slew':
        return do_scan(scanname, comments=comments, nscans=1,
                       filename=filename, _larch=_larch)
    else:
        scan.epics_slewscan(filename=filename)
    return scan

@ValidateLarchPlugin
def make_xafs_scan(label=None, e0=0, _larch=None, **kws):
    return XAFS_Scan(label=label, e0=e0, _larch=_larch, **kws)

@ValidateLarchPlugin
def get_dbinfo(key, default=None, as_int=False, as_bool=False,
               full_row=False, _larch=None, **kws):
    """get a value for a keyword in the scan info table,
    where most status information is kept.

    Arguments
    ---------
     key        name of data to look up
     default    (default None) value to return if key is not found
     as_int     (default False) convert to integer
     as_bool    (default False) convert to bool
     full_row   (default False) return full row, not just value

    Notes
    -----
     1.  if this key doesn't exist, it will be added with the default
         value and the default value will be returned.
     2.  the full row will include notes, create_time, modify_time

    """
    if _larch.symtable._scan._scandb is None:
        print('need to connect to scandb!')
        return
    get_info = _larch.symtable._scan._scandb.get_info
    return get_info(key, default=default, full_row=full_row,
                    as_int=as_int, as_bool=as_bool, **kws)

def initializeLarchPlugin(_larch=None):
    """initialize _scan"""
    if not _larch.symtable.has_group(MODNAME):
        g = Group()
        g.__doc__ = MODDOC
        _larch.symtable.set_symbol(MODNAME, g)

def registerLarchPlugin():
    symbols = {}
    if HAS_EPICSSCAN:
        symbols = {'scan_from_json': scan_from_json,
                   'scan_from_db':   scan_from_db,
                   'make_xafs_scan': make_xafs_scan,
                   'do_scan': do_scan,
                   'do_slewscan': do_slewscan,
                   'do_fastmap':  do_slewscan,
                   'get_dbinfo': get_dbinfo}

    return (MODNAME, symbols)
