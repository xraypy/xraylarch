#!/usr/bin/env python
"""
Output data file from Epics Step Scan (slightly different from gse_escan)
"""

import time
import numpy as np
from .. import Group

COM1 = '#'
COM2 = '##'
SEP  = '||'   # separater between value, pvname in header
FILETOP = '##Epics StepScan File'

class EpicsScanData(object):
    """
    Holds data as read from a Scan Data File.
    """
    def __init__(self, filename=None, **kws):
        self.filename = filename
        self.extra_pvs = []
        self.comments  = []
        self.column_keys    = []
        self.column_names   = []
        self.column_units   = []
        self.column_pvnames = []
        self.breakpoints    = []
        self.breakpoint_times = []
        self.__arraymap = None
        self.start_time = None
        self.stop_time = None
        self.data = []
        if filename is not None:
            self.read(filename)

    def get_data(self, key, fold_breakpoints=False):
        """get positioner or detector array either by key, name, or index
        key can be any of (case-insensitive):
            column number, starting at 0
            column label, 'p1', 'd1', etc
            name of column
            pvname of column
        """
        # cache lower-case version of all keys and names
        if self.__arraymap is None:
            self.__arraymap = {}
            for a in (self.column_keys, self.column_names, self.column_pvnames):
                for i, nam in enumerate(a):
                    self.__arraymap[nam.lower()] = i
        #
        if isinstance(key, int) and key > -1 and key < len(self.column_keys):
            icol = key
        else:
            icol = self.__arraymap.get(key.lower(), None)

        if icol is None:
            print( 'cannot find column %s' % repr(key))
            return None
        return self.data[icol]

    def read(self, filename=None):
        if filename is not None:
            self.filename = filename
        try:
            fh = open(self.filename, 'r')
        except IOError:
            print( 'cannot open file %s for read' % self.filename)
            return
        lines = fh.readlines()
        line0 = lines.pop(0)
        if not line0.startswith(FILETOP):
            print( '%s is not a valid Epics Scan file' % self.filename)
            return

        def split_header(line):
            w = [k.strip() for k in line.replace('#', '').split(':', 1)]
            if len(w) == 1:
                w.append('')
            return w
        mode = None
        extras = {}
        modes = {'Time': 'comment', '----': 'data',
                 'Legend Start': 'legend', 'Legend End': 'legend_end',
                 'ExtraPVs Start': 'extras', 'ExtraPVs End': 'extras_end'}
        for line in lines:
            if line.startswith(COM1):
                key, val = split_header(line[:-1])
                if key.startswith('----'): key = '----'
                if key in modes:
                    mode = modes[key]
                    if mode == 'comment':
                        self.stop_time  = val
                        if self.start_time is None:
                            self.start_time = val
                    elif mode == 'extras':
                        self.breakpoints.append(len(self.data))
                        self.breakpoint_times.append(self.stop_time)
                    elif mode == 'extras_end':
                        self.extra_pvs.append(extras)
                        extras = {}
                    continue
                if mode == 'comment':
                    cmt = line[:-1].strip()
                    if cmt.startswith('#'):  cmt = line[1:].strip()
                    self.comments.append(cmt)
                elif mode in ('legend', 'extras'):
                    words = [w.strip() for w in val.split(SEP)]
                    if len(words) == 1: words.append('')
                    if mode == 'extras':
                        extras[key] = (words[0], words[1])
                    else:
                        if len(words) == 2: words.append('')
                        self.column_keys.append(key)
                        self.column_names.append(words[0])
                        self.column_units.append(words[1])
                        self.column_pvnames.append(words[2])

            else: # data!
                self.data.append([float(i) for i in line[:-1].split()])
        #
        self.comments = '\n'.join(self.comments)
        self.data = np.array(self.data).transpose()

def read_stepscan(fname, _larch=None, **kws):
    """read Epics Step Scan file to larch Group"""

    scan = EpicsScanData(fname)
    group = Group()
    group.__name__ ='Epics Step Sscan Data file %s' % fname
    for key, val in scan.__dict__.items():
        if not key.startswith('_'):
            setattr(group, key, val)

    group.get_data = scan.get_data
    return group
