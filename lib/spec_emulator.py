#!/usr/bin/env python
"""
spec_emulator.SpecScan provides Spec-like scanning functions
based on EpicsApps.StepScan.

    spec = SpecMode()
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

from epics import PV, caget, poll

from .stepscan   import StepScan
from .outputfile import ASCIIScanFile
from .positioner import Positioner
from .detectors  import (SimpleDetector, MotorDetector,
                         ScalerDetector, McaDetector)

class SpecScan(object):
    """Spec Mode for StepScan"""
    def __init__(self, filename=None):
        self.motors  = {}
        self.detectors = []
        self.filename = filename

        self._scan = StepScan()
        self.lup = self.dscan

    def add_motors(self, **motors):
        """add motors as keyword=value pairs: label=EpicsPVName"""
        for label, pvname in motors.items():
            self.motors[label] = Positioner(pvname, label=label)
            if '.' in pvname:
                idot = pvname.index('.')
                rbv_pv = pvname[:idot] + '.RBV'
                p = PV(rbv_pv, connect=True)
                poll(1.e-3, 1.0)
                if p.connected:
                    self.add_detector(pvname, kind='motor')


    def add_detector(self, name, kind='scaler', **kws):
        "add detector, giving base name and detector type"
        builder = SimpleDetector
        if kind == 'scaler':
            builder = ScalerDetector
        elif kind == 'motor':
            builder = MotorDetector
        elif kind == 'mca':
            builder = MCADetector
        self.detectors.append(builder(name, **kws))

    def add_extra_pvs(self, extra_pvs):
        """add extra PVs to be recorded prior to each scan
        extra_pvs should be list or tuple of (label, PVname)
        """
        self._scan.add_extra_pvs(extra_pvs)

    def set_scanfile(self, outputfile):
        "set file name"
        self.filename = outputfile


    def ascan(self, motor, start, finish, npts, dtime):
        "ascan: absolute scan"
        if motor not in self.motors:
            print("Error: unknown motor name '%s'" % motor)

        self._scan.positioners  = [self.motors[motor]]
        self._scan.positioners[0].array = linspace(start, finish, npts)

        self._scan.counters = []
        self._scan.triggers = []
        for d in self.detectors:
            self._scan.add_detector(d)
            d.dwelltime = dtime
        self._scan.run(filename=self.filename)

    def dscan(self, motor, start, finish, npts, dtime):
        "dscan: relative scan"
        if motor not in self.motors:
            print("Error: unknown motor name '%s'" % motor)

        current = self.motors[motor].current()
        start  += current
        finish += current
        self.ascan(motor, start, finish, npts, dtime)


    def a2scan(self, motor1, start1, finish1,
               motor2, start2, finish2, npts, dtime):
        "a2scan: absolute scan of 2 motors"
        if motor1 not in self.motors:
            print("Error: unknown motor name '%s'" % motor1)

        if motor2 not in self.motors:
            print("Error: unknown motor name '%s'" % motor2)

        self._scan.positioners  = [self.motors[motor1],
                                   self.motors[motor2]]

        self._scan.positioners[0].array = linspace(start1, finish1, npts)
        self._scan.positioners[1].array = linspace(start2, finish2, npts)

        self._scan.counters = []
        self._scan.triggers = []
        for d in self.detectors:
            self._scan.add_detector(d)
            d.dwelltime = dtime

        self._scan.run(filename=self.filename)


    def d2scan(self, motor1, start1, finish1,
               motor2, start2, finish2, npts, dtime):
        "d2scan: relative scan of 2 motors"
        if motor1 not in self.motors:
            print("Error: unknown motor name '%s'" % motor1)

        if motor2 not in self.motors:
            print("Error: unknown motor name '%s'" % motor2)

        current1 = self.motors[motor1].current()
        start1  += current1
        finish1 += current1

        current2 = self.motors[motor2].current()
        start2  += current2
        finish2 += current2

        self.a2scan(self, motor1, start1, finish1,
                    motor2, start2, finish2, npts, dtime)


    def a3scan(self, motor1, start1, finish1,
               motor2, start2, finish2,
               motor3, start3, finish3, npts, dtime):
        "a3scan: absolute scan of 3 motors"
        if motor1 not in self.motors:
            print("Error: unknown motor name '%s'" % motor1)

        if motor2 not in self.motors:
            print("Error: unknown motor name '%s'" % motor2)

        if motor3 not in self.motors:
            print("Error: unknown motor name '%s'" % motor3)

        self._scan.positioners  = [self.motors[motor1],
                                   self.motors[motor2],
                                   self.motors[motor3]]


        self._scan.positioners[0].array = linspace(start1, finish1, npts)
        self._scan.positioners[1].array = linspace(start2, finish2, npts)
        self._scan.positioners[2].array = linspace(start3, finish3, npts)

        self._scan.counters = []
        self._scan.triggers = []
        for d in self.detectors:
            self._scan.add_detector(d)
            d.dwelltime = dtime

        self._scan.run(filename=self.filename)


    def d3scan(self, motor1, start1, finish1,
               motor2, start2, finish2,
               motor3, start3, finish3, npts, dtime):
        "d3scan: relative scan of 3 motors"
        if motor1 not in self.motors:
            print("Error: unknown motor name '%s'" % motor1)

        if motor2 not in self.motors:
            print("Error: unknown motor name '%s'" % motor2)

        if motor3 not in self.motors:
            print("Error: unknown motor name '%s'" % motor3)

        current1 = self.motors[motor1].current()
        start1  += current1
        finish1 += current1

        current2 = self.motors[motor2].current()
        start2  += current2
        finish2 += current2

        current3 = self.motors[motor2].current()
        start3  += current3
        finish3 += current3

        self.a2scan(self, motor1, start1, finish1,
                    motor2, start2, finish2,
                    motor3, start3, finish3, npts, dtime)


    def mesh(self, motor1, start1, finish1, npts1,
               motor2, start2, finish2, npts2, dtime):
        """mesh scan: absolute scan of motor1 at each
        position for motor2"""
        if motor1 not in self.motors:
            print("Error: unknown motor name '%s'" % motor1)
        if motor2 not in self.motors:
            print("Error: unknown motor name '%s'" % motor2)

        self._scan.positioners  = [self.motors[motor1],
                                   self.motors[motor2]]

        fast = npts2* [linspace(start1, finish1, npts1)]
        slow = [[i]*npts1 for i in linspace(start2, finish2, npts2)]


        self._scan.positioners[0].array = array(fast).flatten()
        self._scan.positioners[1].array = array(slow).flatten()

        self._scan.counters = []
        self._scan.triggers = []
        for d in self.detectors:
            self._scan.add_detector(d)
            d.dwelltime = dtime

        npts = len(array(fast).flatten())
        breakpoints = []
        for i in range(npts2-1):
            breakpoints.append((i+1)*npts1 - 1)

        def show_meshstatus(breakpoint=None):
            print 'finished row  %i of %i' % (1+(breakpoint/npts1), npts2)
            sleep(0.5)

        self._scan.at_break_methods.append(show_meshstatus)
        self._scan.breakpoints = breakpoints

        self._scan.run(filename=self.filename)


