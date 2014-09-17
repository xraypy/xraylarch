#!/usr/bin/env python
"""
spec_emulator.SpecScan provides Spec-like scanning functions
based on EpicsApps.StepScan.

    from epicsscan import SpecScan
    spec = SpecScan()
    spec.add_motors(x='XX:m1', y='XX:m2')
    spec.add_detector('XX:scaler1')
    spec.set_scanfile(outputfile)

    spec.ascan('x', start, finish, npts, time)
    spec.a2scan('x', s1, f1, 'y', s1, f1, npts, time)
    spec.a3scan('x', s1, f1, 'y', s2, f2, 'z', s3, f3, npts, time)
    spec.mesh('x', s1, f1, npts1, 'y', s2, f2, npts2, time)

    spec.lup('x', start, finish, npts, time)
    spec.dscan('x', start, finish, npts, time)
    spec.d2scan('x', s1, f1, 'y', s1, f1, npts, time)
    spec.d3scan('x', s1, f1, 'y', s2, f2, 'z', s3, f3, npts, time)

yet to be implemented:
    -- th2th tth_start_rel tth_finish_rel intervals time
    -- automatic plotting
    -- save/read configuration
"""
from time import sleep
from numpy import array, linspace

from epics_interface import PV, caget, poll

from .stepscan   import StepScan
from .positioner import Positioner
from .detectors  import get_detector, Counter
from .spec_config import SpecConfig

class SpecScan(object):
    """Spec Mode for StepScan"""
    def __init__(self, filename='specscan.001', configfile=None,
                 auto_increment=True):
        self.motors  = {}
        self.detectors = []
        self.bare_counters = []
        self._scan = StepScan(filename=filename,
                              auto_increment=auto_increment)
        self.datafilename = filename
        if configfile is not None:
            self.configfile = configfile
        self.read_config(filename=configfile)
        self.lup = self.dscan

    def read_config(self, filename=None):
        " "
        self.config = SpecConfig(filename=filename)
        self.configfile = self.config.filename
        for label, pvname in self.config.motors.items():
            self.motors[label] = Positioner(pvname, label=label)

        for label, pvname in self.config.counters.items():
            self.bare_counters.append(Counter(pvname, label=label))

        self.add_extra_pvs(self.config.extra_pvs.items())
        for label, val in self.config.detectors.items():
            opts = {'label': label}
            prefix = val[0]
            if len(val) > 1:
                pairs = [w.strip() for w in val[1].split(',')]
                for s in pairs:
                    skey, sval = s.split('=')
                    opts[skey.strip()] = sval.strip()
            self.add_detector(prefix, **opts)

    def add_motors(self, **motors):
        """add motors as keyword=value pairs: label=EpicsPVName"""
        for label, pvname in motors.items():
            self.motors[label] = Positioner(pvname, label=label)

    def add_counter(self, name, label=None):
        # self._scan.add_counter(name, label=label)
        self.bare_counters.append(Counter(name, label=label))

    def add_detector(self, name, kind=None, **kws):
        "add detector, giving base name and detector type"
        self.detectors.append(get_detector(name, kind=kind, **kws))

    def add_extra_pvs(self, extra_pvs):
        """add extra PVs to be recorded prior to each scan
        extra_pvs should be list or tuple of (label, PVname)
        """
        self._scan.add_extra_pvs(extra_pvs)

    def set_scanfile(self, filename):
        "set file name"
        self.datafilename = filename

    def _checkmotors(self, *args):
        "check that all args are motor names"
        for mname in args:
            if mname not in self.motors:
                raise Exception("Error: unknown motor name '%s'" % mname)

    def _run(self, dwelltime):
        """internal function to start scans"""
        self._scan.counters = []
        self._scan.triggers = []
        self._scan.dwelltime = dwelltime
        for d in self.detectors:
            self._scan.add_detector(d)
            d.dwelltime = dwelltime
        for c in self.bare_counters:
            self._scan.add_counter(c)

        self._scan.run(filename=self.datafilename)

    def ascan(self, motor, start, finish, npts, dtime):
        "ascan: absolute scan"
        self._checkmotors(motor)
        self._scan.positioners  = [self.motors[motor]]
        self._scan.positioners[0].array = linspace(start, finish, npts)
        self._run(dtime)

    def dscan(self, motor, start, finish, npts, dtime):
        "dscan: relative scan"
        self._checkmotors(motor)
        current = self.motors[motor].current()
        start  += current
        finish += current
        self.ascan(motor, start, finish, npts, dtime)

    def a2scan(self, motor1, start1, finish1,
               motor2, start2, finish2, npts, dtime):
        "a2scan: absolute scan of 2 motors"
        self._checkmotors(motor1, motor2)
        self._scan.positioners  = [self.motors[motor1], self.motors[motor2]]
        self._scan.positioners[0].array = linspace(start1, finish1, npts)
        self._scan.positioners[1].array = linspace(start2, finish2, npts)
        self._run(dtime)

    def d2scan(self, motor1, start1, finish1,
               motor2, start2, finish2, npts, dtime):
        "d2scan: relative scan of 2 motors"
        self._checkmotors(motor1, motor2)
        current1 = self.motors[motor1].current()
        start1  += current1
        finish1 += current1

        current2 = self.motors[motor2].current()
        start2  += current2
        finish2 += current2

        self.a2scan(motor1, start1, finish1,
                    motor2, start2, finish2, npts, dtime)

    def a3scan(self, motor1, start1, finish1, motor2, start2, finish2,
               motor3, start3, finish3, npts, dtime):
        "a3scan: absolute scan of 3 motors"
        self._checkmotors(motor1, motor2, motor3)

        self._scan.positioners  = [self.motors[motor1],
                                   self.motors[motor2],
                                   self.motors[motor3]]
        self._scan.positioners[0].array = linspace(start1, finish1, npts)
        self._scan.positioners[1].array = linspace(start2, finish2, npts)
        self._scan.positioners[2].array = linspace(start3, finish3, npts)
        self._run(dtime)

    def d3scan(self, motor1, start1, finish1, motor2, start2, finish2,
               motor3, start3, finish3, npts, dtime):
        "d3scan: relative scan of 3 motors"
        self._checkmotors(motor1, motor2, motor3)

        current1 = self.motors[motor1].current()
        start1  += current1
        finish1 += current1

        current2 = self.motors[motor2].current()
        start2  += current2
        finish2 += current2

        current3 = self.motors[motor2].current()
        start3  += current3
        finish3 += current3

        self.a3scan(motor1, start1, finish1,
                    motor2, start2, finish2,
                    motor3, start3, finish3, npts, dtime)

    def mesh(self, motor1, start1, finish1, npts1,
               motor2, start2, finish2, npts2, dtime):
        """mesh scan: absolute scan of motor1 at each
        position for motor2"""
        self._checkmotors(motor1, motor2)

        self._scan.positioners = [self.motors[motor1], self.motors[motor2]]

        fast = npts2* [linspace(start1, finish1, npts1)]
        slow = [[i]*npts1 for i in linspace(start2, finish2, npts2)]

        self._scan.positioners[0].array = array(fast).flatten()
        self._scan.positioners[1].array = array(slow).flatten()

        # set breakpoints to be the end of each row
        self._scan.breakpoints = [(i+1)*npts1 - 1 for i in range(npts2-1)]

        # add print statement at end of each row
        def show_meshstatus(breakpoint=None):
            print 'finished row  %i of %i' % (1+(breakpoint/npts1), npts2)
            sleep(0.25)
        self._scan.at_break_methods.append(show_meshstatus)
        self._run(dtime)
