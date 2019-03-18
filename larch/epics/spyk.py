#!/usr/bin/env python
"""
Spyk is a Spec emulator, providing Spec-like scanning functions to Larch

    spec = SpykScan()
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
import os
import sys
import time
import numpy as np
from collections import OrderedDict
from io import StringIO
from configparser import ConfigParser


from larch import Group

from larch.utils import get_homedir
from larch.io import get_timestamp

try:
    from epics import PV, caget, caput, get_pv, poll
    HAS_EPICS = True
except ImportError:
    HAS_EPICS = False

try:
    from .larchscan   import LarchStepScan
    import epicsscan
    from epicsscan.positioner import Positioner
    from epicsscan.detectors  import get_detector, Counter
    HAS_EPICSSCAN = True
except ImportError:
    HAS_EPICSSCAN = False


class SpykConfig(object):
    """
    Configuration file (INI format) for Spyk scanning
    """
    LEGEND     = '# index = label || PVname'
    DET_LEGEND = '# index = label || DetectorPV || options '
    SPYK_DIR   = '.spyk'
    SPYK_INI   = 'spyk.ini'
    #  sections            name      ordered?
    __sects = OrderedDict((('setup',     False),
                           ('motors',    True),
                           ('detectors', True),
                           ('extra_pvs', True),
                           ('counters',  True)))

    def __init__(self, filename=None, text=None):
        for s in self.__sects:
            setattr(self, s, {})
        self._cp = ConfigParser()
        self.filename = filename
        if self.filename is None:
            cfile = self.get_default_configfile()
            if (os.path.exists(cfile) and os.path.isfile(cfile)):
                self.filename = cfile
        if self.filename is not None:
            self.Read(self.filename)

    def get_default_configfile(self):
        return os.path.join(get_homedir(), self.SPYK_DIR, self.SPYK_INI)

    def Read(self, fname=None):
        "read config"
        if fname is None:
            return
        ret = self._cp.read(fname)
        if len(ret) == 0:
            time.sleep(0.25)
            ret = self._cp.read(fname)
        self.filename = fname
        # process sections
        for sect, ordered in self.__sects.items():
            if not self._cp.has_section(sect):
                continue
            thissect = OrderedDict() if ordered else {}
            for opt in self._cp.options(sect):
                val = self._cp.get(sect, opt)
                if '||' in val:
                    words = [i.strip() for i in val.split('||')]
                    label = words.pop(0)
                    if len(words) == 1:
                        words = words[0]
                    else:
                        words = tuple(words)
                    thissect[label] = words
                else:
                    thissect[opt] = val
                setattr(self, sect, thissect)

    def Save(self, fname=None):
        "save config file"
        if fname is None:
            fname = self.get_default_configfile()
            path, fn = os.path.split(fname)
            if not os.path.exists(path):
                os.makedirs(path, mode=755)

        out = ['###Spyke Configuration: %s'  % (get_timestamp())]
        for sect, ordered in self.__sects.items():
            out.append('#-----------------------#\n[%s]' % sect)
            if sect == 'setup':
                for name, val in self.setup.items():
                    out.append("%s = %s" % (name, val))
            elif sect == 'detectors':
                out.append(self.DET_LEGEND)
                idx = 0
                for key, val in getattr(self, sect).items():
                    idx = idx + 1
                    if isinstance(val, (list, tuple)):
                        val = ' || '.join(val)
                    out.append("%i = %s || %s"  % (idx, key, val))

            else:
                out.append(self.LEGEND)
                idx = 0
                for key, val in getattr(self, sect).items():
                    idx = idx + 1
                    if isinstance(val, (list, tuple)):
                        val = ' || '.join(val)
                    out.append("%i = %s || %s"  % (idx, key, val))
        out.append('#-----------------------#')
        with open(fname, 'w') as fh:
            fh.write('\n'.join(out))

    def sections(self):
        return self.__sects.keys()


class Spyk(Group):
    """Spyk is a set of Spec-like scanning tools for Larch"""
    def __init__(self, filename='spykscan.001', configfile=None,
                 auto_increment=True, _larch=None, **kwargs):
        Group.__init__(self, **kwargs)
        self.motors  = {}
        self.detectors = []
        self.bare_counters = []
        self._scan = LarchStepScan(filename=filename,
                                   auto_increment=auto_increment,
                                   _larch=_larch)
        self.datafilename = filename
        if configfile is not None:
            self.configfile = configfile
        self.read_config(filename=configfile)
        self.lup = self.dscan

    def read_config(self, filename=None):
        "read Spyk configuration file"
        self.config = SpykConfig(filename=filename)
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

    def save_config(self, filename=None):
        "save Spyk configuration file"
        print( 'save spyk config....')

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
        self._scan.positioners[0].array = np.linspace(start, finish, npts)
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
        self._scan.positioners[0].array = np.linspace(start1, finish1, npts)
        self._scan.positioners[1].array = np.linspace(start2, finish2, npts)
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
        self._scan.positioners[0].array = np.linspace(start1, finish1, npts)
        self._scan.positioners[1].array = np.linspace(start2, finish2, npts)
        self._scan.positioners[2].array = np.linspace(start3, finish3, npts)
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

        fast = npts2* [np.linspace(start1, finish1, npts1)]
        slow = [[i]*npts1 for i in np.linspace(start2, finish2, npts2)]

        self._scan.positioners[0].array = np.array(fast).flatten()
        self._scan.positioners[1].array = np.array(slow).flatten()

        # set breakpoints to be the end of each row
        self._scan.breakpoints = [(i+1)*npts1 - 1 for i in range(npts2-1)]

        # add print statement at end of each row
        def show_meshstatus(breakpoint=None):
            print('finished row  %i of %i' % (1+(breakpoint/npts1), npts2))
            time.sleep(0.25)
        self._scan.at_break_methods.append(show_meshstatus)
        self._run(dtime)
