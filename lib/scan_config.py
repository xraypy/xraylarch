#!/usr/bin/python
"""
config file for Scan and Scan GUI
"""

import os
import time
from ConfigParser import  ConfigParser
from cStringIO import StringIO
from .ordereddict import OrderedDict
from .file_utils import get_homedir, get_timestamp

LEGEND     = '# index = label || PVname'
DET_LEGEND = '# index = label || DetectorPV || options '

DEFAULT_CONF = """
### Epics Scan Configuration
[setup]
filename = test.dat
filemode = increment
basedir = //cars5/Data/xas_user/Nov2012/
extrapvs_file =
#--------------------------#
[positioners]
# index = label || drivePV  || readbackPV
1 = MotorX || 13IDE:m10  || 13IDE:m10.RBV
2 = MotorY || 13IDE:m11  || 13IDE:m11.RBV
3 = Energy || 13IDA:E:En:Energy  || 13IDA:E:En:E_RBV
#--------------------------#
[xafs]
energy_drive = 13IDA:E:En:Energy.VAL
energy_read  = 13IDA:E:En:E_RBV
#--------------------------#
[slewscan]
type = NewportXPS
mode = PVTGroup
host = 164.54.160.180
user   = Administrator
passwd = Administrator
group = FINE
positioners= X, Y, Theta
#--------------------------#
[slewscan_positioners]
# index = label || drivePV || readbackPV
1 = MotorX || 13IDE:m10  || 13IDE:m10.RBV
2 = MotorY || 13IDE:m11  || 13IDE:m11.RBV
#--------------------------#
[detectors]
# index = label || DetectorPV  || options
1 = scaler1 || 13IDE:scaler1 || kind=scaler, use_calc=True
### 2 = mcs1    || 13IDE:SIS1    || kind=mcs
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
    __sects = OrderedDict((('setup',     False),
                           ('positioners', True),
                           ('detectors',   True),
                           ('counters',    True),
                           ('xafs',      False),
                           ('slewscan',  False),
                           ('slewscan_positioners',  True),
                           ('extra_pvs',   True),
                           ))

    def __init__(self, filename=None, text=None):
        for s in self.__sects:
           setattr(self, s, {})

        self._cp = ConfigParser()
        if filename is None:
            filename = DEF_CONFFILE
        self.filename = filename
        if (os.path.exists(filename) and
            os.path.isfile(filename)):
            ret = self._cp.read(fname)
            if len(ret) == 0:
                time.sleep(0.1)
                self._cp.read(fname)
        else:
            self._cp.readfp(StringIO(DEFAULT_CONF))
        self.Read()

    def Read(self, filename=None):
        "read config"
        if (filename is not None and
            (os.path.exists(filename) and
             os.path.isfile(filename))):
            ret = self._cp.read(fname)
            if len(ret) == 0:
                time.sleep(0.1)
                self._cp.read(fname)
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

