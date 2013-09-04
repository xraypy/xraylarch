#!/usr/bin/python
"""
Station Configuration file for StepScan

The Station Configuration describes overall
settings for StepScan, including the list of
positioners and detectors that can be used,
the Extra PVs to be cached, and file directory names.

"""

import os
import time
from ConfigParser import  ConfigParser
from cStringIO import StringIO
from .ordereddict import OrderedDict
from .file_utils import get_homedir, get_timestamp

LEGEND     = '# index = label || PVname'
DET_LEGEND = '# index = label || DetectorPV || options '
TITLE  = "Epics StepScan Station Configuration"

DEFAULT_CONF = """
### %s
[setup]
filename = test.dat
filemode = increment
pos_settle_time = 0.01
det_settle_time = 0.01
#--------------------------#
[pg_server]
use    = true
dbname = epics_scan
host   = mini.cars.aps.anl.gov
user   = epics
passwd = epics
port   = 5432
#--------------------------#
[positioners]
# index = label || drivePV  || readbackPV
1 = Fine X || 13XRM:m1  || 13XRM:m1.RBV
2 = Fine Y || 13XRM:m2  || 13XRM:m2.RBV
3 = Energy || 13IDE:En:Energy  || 13IDE:En:E_RBV
4 = Theta  || 13XRM:m3  || 13XRM:m3.RBV
5 = Focus Z || 13XRM:pm1 || 13XRM:pm1.RBV
6 = Coarse X || 13XRM:pm2 || 13XRM:pm2.RBV
7 = Coarse Y  || 13XRM:m6  || 13XRM:m6.RBV
#--------------------------#
[xafs]
energy_drive = 13IDE:En:Energy.VAL
energy_read  = 13IDE:En:E_RBV
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
1 = Fine X || 13XRM:m1  || 13XRM:m1.RBV
2 = Fine Y || 13XRM:m2  || 13XRM:m2.RBV
#--------------------------#
[detectors]
# index = label || DetectorPV  || options
1 = scaler1     || 13IDE:scaler1  || kind=scaler, nchan=8, use_calc=True
2 = me4         || 13SDD1:        || kind=multimca, nmcas=4, nrois=32, use_net=False, use_full=False
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
""" % TITLE

DEF_CONFFILE = os.path.join(get_homedir(), '.pyscan', 'station_config.ini')

def opts2dict(opts_string):
    """convert options string like
    x = a, n = 3, w = True
    into a dictionary.  Rules are:
      1. split to key=val on ','
      2. split to key, val
      3. trim all words
      4. convert True/False/None strings to python objects
      5. convert integers to python ints"""
    d = {}
    for expr in opts_string.split(','):
        words = expr.split('=')
        key = words[0]
        if len(words) == 1:
            val = 'True'
        else:
            val = words[1]
        val.strip()
        if val == 'True':
            val = True
        elif val == 'False':
            val = False
        elif val == 'None':
            val = None
        else:
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
        d[key.strip()] = val
    return d

def dict2opts(d):
    """convert options dict to options string
    sorts keys alphabetically, so output order is consistent
    """
    w = []
    for key in sorted(d.keys()):
        w.append("%s=%s" % (key, repr(d[key])))
    return ', '.join(w)


class StationConfig(object):
    #  sections            name      ordered?
    __sects = OrderedDict((('setup',       False),
                           ('pg_server',   False),
                           ('positioners', True),
                           ('detectors',   True),
                           ('counters',    True),
                           ('xafs',        False),
                           ('slewscan',    False),
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
        # print 'StationConfig ', filename, os.path.abspath(filename)
        # print os.path.exists(filename),   os.path.isfile(filename)
        if (os.path.exists(filename) and
            os.path.isfile(filename)):
            ret = self._cp.read(filename)
            if len(ret) == 0:
                time.sleep(0.1)
                self._cp.read(filename)
        else:
            self._cp.readfp(StringIO(DEFAULT_CONF))
        self.Read()

    def Read(self, filename=None):
        "read config"
        if (filename is not None and
            (os.path.exists(filename) and
             os.path.isfile(filename))):
            ret = self._cp.read(filename)
            if len(ret) == 0:
                time.sleep(0.1)
                self._cp.read(filename)
            self.filename = filename

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
                        tmp = []
                        for w in words:
                            if ',' in w and '=' in w:
                                tmp.append(opts2dict(w))
                            else:
                                tmp.append(w)
                        words = tuple(tmp)
                    thissect[label] = words
                else:
                    thissect[opt] = val
                setattr(self, sect, thissect)
        for key, val in self.positioners.items():
            fi = []
            if isinstance(val, (list, tuple)):
                for v in val:
                    if '.' not in v: v = '%s.VAL' % v
                    fi.append(v)
            else:
                if '.' not in val:
                    val = '%s.VAL' % val
                fi = [val, val]
            self.positioners[key] = tuple(fi)

    def Save(self, fname=None):
        "save config file"
        if fname is not None:
            self.filename = fname
        if fname is None:
            fname = self.filename = DEF_CONFFILE
            path, fn = os.path.split(fname)
            if not os.path.exists(path):
                os.makedirs(path, mode=0755)

        out = ['### %s: %s' % (TITLE, get_timestamp())]
        for sect, ordered in self.__sects.items():
            out.append('#------------------------------#\n[%s]' % sect)
            if sect in ('setup', 'pg_server', 'slewscan', 'xafs'):
                for name, val in self.setup.items():
                    out.append("%s = %s" % (name, val))
            elif sect == 'detectors':
                out.append(DET_LEGEND)
                idx = 0
                for key, val in getattr(self, sect).items():
                    idx = idx + 1
                    if isinstance(val, (list, tuple)):
                        wout = []
                        for w in val:
                            if isinstance(w, dict):
                                wout.append(dict2opts(w))
                            elif isinstance(w, (str, unicode)):
                                wout.append(w)
                            else:
                                wout.append(repr(w))
                        val = ' || '.join(wout)
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

