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
from file_utils import new_filename, get_timestamp

class ScanFile(object):
    """base Scan File -- will need to inherti and
    overrwrite methods.
    """
    def __init__(self, name=None, scan=None):
        self.filename = name
        self.fh = None
        self.scan = scan

    def open(self, mode='a', new_file=True):
        "open file"
        if new_file:
            self.filename = new_filename(self.filename)
        if os.path.exists(self.filename) and mode != 'a':
            mode = 'a'
        self.fh = open(self.filename, mode)
        return self.fh

    def check_writeable(self):
        "check that output file is open and writeable"
        if not isinstance(self.fh, file):
            self.open()
        return (not self.fh.closed and
                'w' in self.fh.mode)

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
    def __init__(self, name=None, scan=None,
                 comchar='#', comments=None,
                 mode='increment'):
        ScanFile.__init__(self, name=name, scan=scan)
        if name is None:
            self.filename = 'test.dat'
        self.comchar= comchar
        self.com2 = '%s%s' % (comchar, comchar)
        self.filemode = mode
        self.comments = comments

    def open(self, mode='a', new_file=None):
        "open file"
        if new_file is None:
            new_file = ('increment' == self.filemode)
        if new_file:
            self.filename = new_filename(self.filename)
        
        is_new = not os.path.exists(self.filename)
        self.fh = open(self.filename, mode)
        if is_new:
            self.write("%sEpics StepScan File /version=2.0\n" % self.com2)
        return self.fh

    def write_lines(self, buff):
        "write array of text lines"
        self.check_writeable()
        self.write('%s\n' % '\n'.join(buff))
        self.flush()

    def write_extrapvs(self):
        "write extra PVS"
        self.check_writeable()
        out = ['%sExtraPVs Start:' % (self.com2)]
        for desc, pvname, val in self.scan.read_extra_pvs():
            if not isinstance(val, (str, unicode)):
                val = repr(val)
            out.append("%s %s |%s|  %s" % (self.comchar,
                                           desc, pvname, val))

        out.append('%sExtraPVs End' % (self.com2))
        self.write_lines(out)

    def write_timestamp(self, label='Time'):
        "write timestamp"
        self.check_writeable()
        self.write("%s%s: %s\n" % (self.com2, label, get_timestamp()))

    def write_comments(self):
        "write comment lines"
        if self.comments is None:
            return
        self.check_writeable()
        lines = self.comments.split('\n')
        self.write_lines(['%s %s' % (self.comchar, l) for l in lines])


    def write_legend(self):
        "write legend"
        self.check_writeable()
        cols = []
        legend = []
        for i, pos in enumerate(self.scan.positioners):
            key = 'p%i' % (i+1)
            cols.append("   %s  " % (key))
            legend.append("%s %s |%s| %s" % (self.comchar, key,
                                             pos.pv.pvname,
                                             pos.label))
            
        for i, det in enumerate(self.scan.counters):
            key = 'd%i' % (i+1)
            cols.append("   %s  " % (key))
            legend.append("%s %s |%s| %s" % (self.comchar, key,
                                             det.pv.pvname, det.label))

        out = ['%sLegend Start:' % self.com2]
        for l in legend:
            out.append(l)
        self.column_label = '%s %s' % (self.comchar, '\t'.join(cols))
        out.append('%sLegend End' % self.com2)
        self.write_lines(out)

    def write_data(self, breakpoint=0, clear=False, close_file=False, verbose=False):
        "write data"
        if breakpoint == 0:
            self.write_timestamp(label='Time_Start')
            self.write_comments()
            self.write_legend()
            return
        self.write_timestamp(label='Time_End')
        self.write_extrapvs()
        out = ['%s%s' % (self.comchar, '-'*66)]

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
                            
