#!/usr/bin/env python
"""
Output data file layer for Step Scan

Different output formats can be supported, but the basic file
defined here is a plaintext, ASCII format using newlines as
delimiters and '#' as comment characters, and a fairly strict,
parsable format.

ScanFile supports several methods:

  open()
  close()
  write_extrapvs()
  write_comments()
  write_legend()
  write_timestamp()
  write_data()

which  can be overridden to create a new Output file type
"""
import os
import time
import numpy as np

from .file_utils import new_filename, get_timestamp
from .ordereddict import OrderedDict

COM1 = '#'
COM2 = '##'
SEP  = '||'   # separater between value, pvname in header
FILETOP = '##Epics StepScan File'

class StepScanData(object):
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
        self._valid = False
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
            print 'cannot find column %s' % repr(key)
            return None
        return self.data[icol]

    def read(self, filename=None):
        if filename is not None:
            self.filename = filename
        self._valid = False
        fh = open(self.filename, 'r')


        lines = fh.readlines()
        line0 = lines.pop(0)
        if not line0.startswith(FILETOP):
            print '%s is not a valid Epics Scan file' % self.filename
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
        self._valid = True

class ScanFile(object):
    """base Scan File -- intended to be inherited and
    overrwritten for multiple ScanFile types (ASCII, HDF5) to be
    supported with compatible methods
    """
    def __init__(self, name=None, scan=None):
        self.filename = name
        self.fh = None
        self.scan = scan

    def open_for_read(self, mode='r'):
        "open file for read"
        self.fh = open(self.filename, mode)
        return self.fh

    def open_for_write(self, filename=None, mode='a'):
        """open file for write or append,
        ensuring the filename is auto-incremented so as to
        not clobber an existing file name"""
        if filename is not None:
            self.filename  = filename
        if 'a' in mode or 'w' in mode:
            self.filename = new_filename(self.filename)

        if isinstance(self.fh, file):
            self.fh.close()
        self.fh = open(self.filename, mode)
        return self.fh

    def check_writeable(self):
        "check that output file is open and writeable"
        return (isinstance(self.fh, file) and
                not self.fh.closed and
                ('a' in self.fh.mode or 'w' in self.fh.mode))

    def flush(self):
        "flush file"
        if self.fh is not None:
            self.fh.flush()

    def write(self, s):
        "write to file"
        if self.fh is not None:
            self.fh.write(s)

    def close(self):
        "close file"
        if self.fh is not None:
            self.fh.close()

    def write_extrapvs(self):
        "write extra PVS"
        pass

    def write_comments(self):
        "write legend"
        pass

    def write_legend(self):
        "write legend"
        pass

    def write_timestamp(self):
        "write timestamp"
        pass

    def write_data(self, breakpoint=0, clear=False):
        "write data"
        pass

class ASCIIScanFile(ScanFile):
    """basis ASCII Column File, line-ending delimited,
    using '#' for comment lines
    """
    num_format = "% 15f"
    version = '2.0'
    def __init__(self, name=None, scan=None,
                 comments=None,
                 auto_increment=True):
        ScanFile.__init__(self, name=name, scan=scan)
        if name is None:
            self.filename = 'test.dat'
        self.auto_increment = auto_increment
        self.comments = comments

    def write_lines(self, buff):
        "write array of text lines"
        if not self.check_writeable():
            self.open_for_write(mode='a')
            self.write("%s / %s\n" % (FILETOP, self.version))
        self.write('%s\n' % '\n'.join(buff))
        self.flush()

    def write_extrapvs(self):
        "write extra PVS"
        out = ['%sExtraPVs Start:' % COM2]
        for desc, pvname, val in self.scan.read_extra_pvs():
            if not isinstance(val, (str, unicode)):
                val = repr(val)
            out.append("%s %s: %s %s %s" % (COM1, desc, val, SEP, pvname))

        out.append('%sExtraPVs End' % COM2)
        self.write_lines(out)

    def write_timestamp(self, label='Time'):
        "write timestamp"
        self.write_lines(["%s%s: %s" % (COM2, label, get_timestamp())])

    def write_comments(self):
        "write comment lines"
        if self.comments is None:
            return
        lines = self.comments.split('\n')
        self.write_lines(['%s %s' % (COM1, l) for l in lines])

    def write_legend(self):
        "write legend"
        cols = []
        out = ['%sLegend Start: Column: Name || EpicsPV || units' % COM2]
        fmt = "%s %s: %s %s %s %s %s"
        for i, pos in enumerate(self.scan.positioners):
            key = 'p%i' % (i+1)
            cols.append("   %s  " % (key))
            if pos.units in (None, 'None', ''):
                pos.units = ''
                try:
                    pos.units = pos.pv.units
                except TypeError:
                    time.sleep(0.02)
                    try:
                        pos.units = pos.pv.units
                    except:
                        pass

            out.append(fmt % (COM1, key, pos.label,
                              SEP, pos.pv.pvname,
                              SEP, pos.units))
        for i, det in enumerate(self.scan.counters):
            key = 'd%i' % (i+1)
            cols.append("   %s  " % (key))
            if det.units in (None, 'None', ''):
                det.units = ''
                try:
                    det.units = det.pv.units
                except TypeError:
                    time.sleep(0.02)
                    try:
                        det.units = det.pv.units
                    except:
                        pass

            out.append(fmt % (COM1, key, det.label,
                              SEP, det.pv.pvname,
                              SEP, det.units))
        out.append('%sLegend End' % COM2)
        self.write_lines(out)
        self.column_label = '%s %s' % (COM1, '\t'.join(cols))

    def write_data(self, breakpoint=0, clear=False, close_file=False, verbose=False):
        "write data"
        if breakpoint == 0:
            self.write_timestamp(label='Time_Start')
            self.write_comments()
            self.write_legend()
            return
        self.write_timestamp(label='Time_End')
        self.write_extrapvs()
        out = ['%s%s' % (COM1, '-'*66)]

        out.append(self.column_label)

        for i in range(len(self.scan.counters[0].buff)):
            words =  self.scan.pos_actual[i][:]
            words.extend([c.buff[i] for c in self.scan.counters])
            try:
                thisline = ' '.join([self.num_format % w for w in words])
            except:
                thisline = ' '.join([repr(w) for w in words])
            out.append(thisline)

        self.write_lines(out)
        if clear:
            self.scan.clear_data()


        if close_file:
            self.close()
            if verbose:
                print "Wrote and closed %s" % self.filename

    def read(self, filename=None):
        return StepScanData(filename)
