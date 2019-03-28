#!/usr/bin/python

import os
import sys
import time
from configparser import  ConfigParser
from io import StringIO

from larch.utils import OrderedDict


conf_sects = {'general': {},
              'xps':{'bools':('use_ftp',)},
              'fast_positioners': {'ordered':True},
              'slow_positioners': {'ordered':True},
              'xrf': {},
              'scan': {'ints': ('dimension',),
                       'floats':('start1','stop1', 'step1','time1',
                                 'start2','stop2', 'step2')}}

__c = (('general', ('mapdb', 'struck', 'scaler', 'xmap', 'mono',
                   'fileplugin', 'basedir', 'scandir', 'envfile')),
       ('xps',  ('host', 'user', 'passwd', 'group', 'positioners')),
       ('scan', ('filename', 'dimension', 'comments', 'pos1', 'start1', 'stop1',
                 'step1', 'time1', 'pos2', 'start2', 'stop2', 'step2')),
       ('xrf',      ('use', 'type', 'prefix', 'plugin')),
       ('fast_positioners', None),
       ('slow_positioners', None))

conf_objs = OrderedDict(__c)

conf_files = ('Scan.ini',)


default_conf = """# FastMap configuration file (default)
[general]
basedir=
envfile =
[xps]
type = NewportXPS
mode =
host =
user =
passwd =
group =
positioners=
[scan]
filename = scan.001
comments =
dimension = 2
pos1 =
start1 = -1.0
stop1 = 1.0
step1 = 0.01
time1 = 20.0
pos2 =
start2 = -1.0
stop2 = 1.0
step2 = 0.01
[fast_positioners]
1 = X | X
2 = Y | Y
[slow_positioners]
1 = X | X
2 = Y | Y
"""

class FastMapConfig(object):
    def __init__(self, filename=None, conftext=None):
        self.config = {}
        self.cp =  ConfigParser()
        conf_found = False
        if filename is not None:
            self.Read(fname=filename)
        else:
            for fname in conf_files:
                if os.path.exists(fname) and os.path.isfile(fname):
                    self.Read(fname)
                    conf_found = True
                    break
        if not conf_found:
            self.cp.readfp(StringIO(default_conf))
            self._process_data()

    def Read(self,fname=None):
        if fname is not None:
            ret = self.cp.read(fname)
            if len(ret)==0:
                time.sleep(0.5)
                ret = self.cp.read(fname)
            self.filename = fname
            self._process_data()

    def _process_data(self):
        for sect,opts in conf_sects.items():
            # if sect == 'scan': print( opts)
            if not self.cp.has_section(sect):
                continue
            bools = opts.get('bools',[])
            floats= opts.get('floats',[])
            ints  = opts.get('ints',[])
            thissect = {}
            is_ordered = False
            if 'ordered' in opts:
                thissect = OrderedDict()
                is_ordered = True
            for opt in self.cp.options(sect):
                get = self.cp.get
                if opt in bools:    get = self.cp.getboolean
                elif opt in floats: get = self.cp.getfloat
                elif opt in ints:   get = self.cp.getint
                val = get(sect,opt)
                if is_ordered and '|' in val:
                    opt,val = val.split('|',1)
                    opt = opt.strip()
                    val = val.strip()
                thissect[opt] = val
            self.config[sect] = thissect

    def Save(self,fname):
        o = []
        cnf = self.config
        self.filename = fname
        o.append('# FastMap configuration file (saved: %s)'  % (time.ctime()))
        for sect,optlist in conf_objs.items():
            o.append('#------------------#\n[%s]'%sect)
            if optlist is not None:
                for opt in optlist:
                    try:
                        val = cnf[sect].get(opt,'<unknown>')
                        if not isinstance(val, str):
                            val = str(val)
                        o.append("%s = %s" % (opt,val))
                    except:
                        pass
            else:
                for i,x in enumerate(cnf[sect]):
                    o.append("%i = %s | %s" % (i+1,x,
                                               cnf[sect].get(x,'<unknown>')))
        o.append('#------------------#\n')
        f = open(fname,'w')
        f.write('\n'.join(o))
        f.close()

    def SaveScanParams(self,fname):
        "save only scan parameters to a file"
        o = []
        o.append('# FastMap Scan Parameter file (saved: %s)'  % (time.ctime()))
        sect = 'scan'
        optlist = conf_objs[sect]
        o.append('#------------------#\n[%s]'%sect)
        scan =self.config['scan']
        for opt in optlist:
            val = scan.get(opt,None)
            if val is not None:
                if not isinstance(val, str):
                    val = str(val)
                o.append("%s = %s" % (opt,val))
        o.append('#------------------#\n')
        f = open(fname,'w')
        f.write('\n'.join(o))
        f.close()

    def sections(self):
        return self.config.keys()

    def section(self, section):
        return self.config[section]

    def get(self, section, value=None):
        if value is None:
            return self.config[section]
        else:
            return self.config[section][value]


if __name__ == "__main__":
    a = FastMapConfig()
    a.Read('default.ini')
    for k,v in a.config.items():
           print( k,v, type(v))
    a.Read('xmap.001.ini')
    print( a.config['scan'])
    a.SaveScanParams('xmap.002.ini')
