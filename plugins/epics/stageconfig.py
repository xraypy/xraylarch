#!/usr/bin/python
# read gsecars samplestage file
import os
import time
from ConfigParser import  ConfigParser
from collections import OrderedDict


from larch import use_plugin_path, ValidateLarchPlugin
use_plugin_path('epics')

from epics_plugin import caget, caput


conf_sects = {'setup':{'bools': ('verify_move','verify_erase', 'verify_overwrite'),
                       'ints': ('finex_dir', 'finey_dir')},
              'camera': {'ordered':False},
              'stages': {'ordered':True},
              'positions': {'ordered':True} }

conf_objs = OrderedDict( (('setup', ('verify_move', 'verify_erase', 'verify_overwrite',
                                      'finex_dir', 'finey_dir')),
                          ('camera', ('type', 'image_folder', 'ad_prefix', 'ad_format', 'web_url')),
                          ('stages', None),
                          ('positions', None)) )

class StageConfig(object):
    def __init__(self, filename='SampleStage_autosave.ini'):
        self.config = {}
        self.cp = ConfigParser()
        self.nstages = 0
        self.stages = []
        self.modtime = 0.0
        self.positions  = []
        conf_found = False
        if (filename is None and
            os.path.exists(filename) and os.path.isfile(filename)):
            self.Read(fname=filename)

    def Read(self, fname=None):
        if fname is None:
            return
        modtime = os.stat(fname).st_mtime
        if modtime < self.modtime and fname == self.filename:
            return

        ret = self.cp.read(fname)
        self.modtime = modtime
        self.filename = fname
        self._process_data()

    def _process_data(self):
        for sect, opts in conf_sects.items():
            if not self.cp.has_section(sect):
                # print 'skipping section ' ,sect
                continue
            bools = opts.get('bools',[])
            floats= opts.get('floats',[])
            ints  = opts.get('ints',[])
            thissect = {}
            is_ordered = False
            if 'ordered' in opts:
                is_ordered = True

            for opt in self.cp.options(sect):
                get = self.cp.get
                if opt in bools:
                    get = self.cp.getboolean
                elif opt in floats:
                    get = self.cp.getfloat
                elif opt in ints:
                    get = self.cp.getint
                val = get(sect,opt)
                if is_ordered and '||' in val:
                    nam, val = val.split('||', 1)
                    opt = opt.strip()
                    val = nam, val.strip()
                thissect[opt] = val
            self.config[sect] = thissect

        if 'positions' in self.config:
            out = OrderedDict()
            poskeys = list(self.config['positions'].keys())
            poskeys.sort()
            for key in poskeys:
                name, val = self.config['positions'][key]
                name = name.strip()
                img, posval = val.strip().split('||')
                pos = [float(i) for i in posval.split(',')]
                out[name] = dict(image=img.strip(), position= pos)
            self.positions = out

        if 'stages' in self.config:
            out = OrderedDict()
            skeys = list(self.config['stages'].keys())
            skeys.sort()
            for key in skeys:
                name, val = self.config['stages'][key]
                name = name.strip()
                label, desc, sign = val.split('||')
                out[name] = dict(label=label.strip(), desc=desc.strip(), sign=int(sign))
            self.stages = out
            self.nstages = len(out)

    def section(self,section):
        return self.config[section]

    def get(self,section,value=None):
        if value is None:
            return self.config[section]
        else:
            return self.config[section][value]


@ValidateLarchPlugin
def read_gsestage(filename='SampleStage_autosave.ini', _larch=None):
    "read positions from XYZ Sample stage config file"

    if not hasattr(_larch.symtable._epics, 'stageconfig'):
        _larch.symtable._epics.stageconfig = StageConfig()
    config = _larch.symtable._epics.stageconfig
    config.Read(filename)
    return config

@ValidateLarchPlugin
def move_stage(pos, filename='SampleStage_autosave.ini',
               wait=True, _larch=None):
    """move GSE sample stage to named position

    options:  filename (default 'SampleStage_autosave.ini')
              wait     (default True)
    """
    config =  read_gsestage(filename=filename, _larch=_larch)

    thisval = None
    posname = pos.strip().lower()
    for poskey, posval in config.positions.items():
        if posname == poskey.strip().lower():
            thisval = posval
            break
    if thisval is None:
        print 'Position  %s not found!' % pos
        return

    motornames = config.stages.key()
    for pvname, target in zip(motornames, thisval):
        caput(pvname, target)
    if wait:
        for pvname, target in zip(motornames, thisval):
            caput(pvname, target, wait=True)


def registerLarchPlugin():
    return ('_epics', {'read_gsestage': read_gsestage,
                       'move_stage': move_stage})
