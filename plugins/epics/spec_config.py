#!/usr/bin/python

import os
import time
from ConfigParser import  ConfigParser
from cStringIO import StringIO
from ordereddict import OrderedDict
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
1 = x || XXX.m1
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
    __sects = OrderedDict((('setup',     False),
                           ('motors',    True),
                           ('detectors', True),
                           ('extra_pvs', True),
                           ('counters',  True)))

    def __init__(self, filename=None, text=None):
        for s in self.__sects:
            setattr(self, s, {})

        self._cp = ConfigParser()
        if filename is None:
            if (os.path.exists(DEF_CONFFILE) and
                os.path.isfile(DEF_CONFFILE)):
                filename = DEF_CONFFILE

        self.filename = filename
        if filename is not None:
            self.Read(filename)

    def Read(self, fname):
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
            thissect = {}
            if ordered:
                thissect = OrderedDict()
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
        if fname is not None:
            self.filename = fname
        if fname is None:
            fname = self.filename = DEF_CONFFILE
            path, fn = os.path.split(fname)
            if not os.path.exists(path):
                os.makedirs(path, mode=0755)

        out = ['###PyScan Spec Configuration: %s'  % (get_timestamp())]
        for sect, ordered in self.__sects.items():
            out.append('#-----------------------#\n[%s]' % sect)
            if sect == 'setup':
                for name, val in self.setup.items():
                    out.append("%s = %s" % (name, val))
            elif sect == 'detectors':
                out.append(DET_LEGEND)
                print 'sect = det'
                idx = 0
                for key, val in getattr(self, sect).items():
                    idx = idx + 1
                    if isinstance(val, (list, tuple)):
                        val = ' || '.join(val)
                    out.append("%i = %s || %s"  % (idx, key, val))

            else:
                leg = LEGEND
                out.append(LEGEND)
                idx = 0
                for key, val in getattr(self, sect).items():
                    idx = idx + 1
                    if isinstance(val, (list, tuple)):
                        val = ' || '.join(val)
                    out.append("%i = %s || %s"  % (idx, key, val))
        out.append('#-----------------------#')
        f = open(fname, 'w')
        f.write('\n'.join(out))
        f.close()

    def sections(self):
        return self.__sects.keys()

