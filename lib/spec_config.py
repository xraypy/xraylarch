#!/usr/bin/python

import os
import time
from ConfigParser import  ConfigParser
from cStringIO import StringIO
from epics.wx.ordereddict import OrderedDict
from .file_utils import get_homedir, get_timestamp

LEGEND     = '# index = label || PVname'
DET_LEGEND = '# index = label || DetectorPV || options '

DEFAULT_CONF = """
### PyScan Spec Configuration
[setup]
filename = test.dat
filemode = increment
#--------------------------#
[motors]
# index = label || PVname
1 = x ||  XXX.m1
2 = y || XXX.m2
#--------------------------#
[detectors]
# index = label || DetectorPV  || options
1 = scaler1 || XXX.scaler1  || kind=scaler, use_calc=True
#--------------------------#
[counters]
# index = label || PVname
1 = pv 1  || XXX.PV1
#--------------------------#
[extra_pvs]
# index = label || PVname
1 = ring current || XXX.PV1
2 = temperature  || XXX.TPV
"""

DEF_CONFFILE = os.path.join(get_homedir(), '.pyscan', 'pyscan_spec.ini')

class SpecConfig(object):
    #  sections            name      ordered?
    sects = OrderedDict((('setup',     False),
                         ('motors',    True),
                         ('detectors', True),
                         ('extra_pvs', True),
                         ('counters',  True)))

    def __init__(self, filename=None, text=None):
        self.config = {}
        self.cp = ConfigParser()
        self.ns = 0
        if filename is None:
            if os.path.exists(DEF_CONFFILE) and os.path.isfile(DEF_CONFFILE):
                filename = DEF_CONFFILE

        if filename is not None:
            self.Read(fname=filename)
        else:
            self.cp.readfp(StringIO(DEFAULT_CONF))
            self._process_data()

    def Read(self, fname=None):
        "read config"
        if fname is not None:
            ret = self.cp.read(fname)
            if len(ret)==0:
                time.sleep(0.25)
                ret = self.cp.read(fname)
            self.filename = fname
            self._process_data()

    def _process_data(self):
        "process sections"
        for sect, ordered in self.sects.items():
            if not self.cp.has_section(sect):
                continue
            thissect = {}
            if ordered:
                thissect = OrderedDict()
            for opt in self.cp.options(sect):
                val = self.cp.get(sect, opt)
                if '||' in val:
                    words = [i.strip() for i in val.split('||')]
                    label = words.pop(0)
                    if len(words) == 1:
                        words = words[0]
                    thissect[label] = words
                else:
                    thissect[opt] = val
                self.config[sect] = thissect

    def Save(self, fname=None):
        cnf = self.config
        if fname is not None:
            self.filename = fname
        if fname is None:
            fname = self.filename = DEF_CONFFILE
            path, fn = os.path.split(fname)
            if not os.path.exists(path):
                os.makedirs(path, mode=0755)

        out = ['###PyScan Spec Configuration: %s'  % (get_timestamp())]
        for sect, ordered in self.sects:
            out.append('#-----------------------#\n[%s]' % sect)
            if sect == 'setup':
                for name, val in cnf[sect].items():
                    out.append("%s = %s" % (name, val))
            else:
                leg = LEGEND
                if sect == 'detectors':
                    leg = DET_LEGEND
                out.append(leg)
                idx = 0
                for key, val in cnf[sect].items():
                    idx = idx + 1
                    if isinstance(val, (list, tuple)):
                        val = ' || '.join(val)
                    out.append("%i = %s || %s"  % (idx, key, val))
        out.append('#-----------------------#')
        f = open(fname, 'w')
        f.write('\n'.join(out))
        f.close()

    def sections(self):
        return self.config.keys()

    def section(self,section):
        return self.config[section]

    def get(self,section,value=None):
        if value is None:
            return self.config[section]
        else:
            return self.config[section][value]
