#!/usr/bin/python
"""
config file for Scan and Scan GUI
"""

import os
import time
from ConfigParser import  ConfigParser
from cStringIO import StringIO
from ordereddict import OrderedDict
from file_utils import get_homedir, get_timestamp

LEGEND     = '# index = label || PVname'
DET_LEGEND = '# index = label || DetectorPV || options '

DEFAULT_CONF = """
### Epics Scan Configuration
[setup]
filename_prefix = test
filemode        = increment
#--------------------------#
[positioners]
# index = label || PVname
1 = MotorX || 13IDE:m10
2 = MotorY || 13IDE:m11
3 = Energy || 13IDA:E:En:Energy
#--------------------------#
[detectors]
# index = label || DetectorPV  || options
1 = scaler1 || 13IDE:scaler1  || kind=scaler, use_calc=True
#--------------------------#
[counters]
# index = label || PVname
1 = MotorX_Steps  || 13IDE:m11.RRBV
#--------------------------#
[extra_pvs]
# index = label || PVname
1 = Ring Current || S:SRcurrentAI.VAL
2 = I0 Preamp Sensitivity Number || 13IDE:A1sens_num.VAL
3 = I0 Preamp Sensitivity Units  || 13IDE:A1sens_unit.VAL
"""

DEF_CONFFILE = os.path.join(get_homedir(), '.pyscan', 'scan_config.ini')

class ScanConfig(object):
    #  sections            name      ordered?
    __sects = OrderedDict((('setup',       False),
                           ('positioners', True),
                           ('detectors',   True),
                           ('extra_pvs',   True),
                           ('counters',    True)))

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
            opt_keys = self._cp.options(sect)
            if ordered:
                thissect = OrderedDict()
                opt_keys.sort()
            for opt in opt_keys:
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

        out = ['### Epics Scan Configuration: %s' % (get_timestamp())]
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

