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
  write_legend()
  write_timestamp()
  write_data()

which  can be overridden to create a new Output file type
"""
import os
import time

class ScanFile(object):
    """base Scan File -- will need to inherti and
    overrwrite methods.
    """
    def __init__(self, filename=None, scan=None):
        self.filename = filename
        self.fh = None
        self.scan = scan

    def open(self, mode='a'):
        "open file"
        if os.path.exists(self.filename) and '+' not in mode:
            mode = mode + '+'
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

    def write_legend(self):
        "write legend"
        pass

    def write_timestamp(self):
        "write timestamp"
        pass

    def write_data(self, breakpoint=0, clear=True):
        "write data"
        pass

        
class ASCIIScanFile(ScanFile):
    """basis ASCII Column File, line-ending delimited,
    using '#' for comment lines
    """
    def __init__(self, filename=None, scan=None,
                 comchar='#'):
        ScanFile.__init__(self, filename=filename, scan=scan)
        if filename is None:
            self.filename = 'test.dat'
        self.comchar= comchar
        self.com2 = '%s%s' % (comchar, comchar)
        
    def open(self, mode='a'):
        "open file"
        self.fh = open(self.filename, mode)
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
            out.append("%s %s (%s):\t %s" % (self.comchar,
                                             desc, pvname, repr(val)))
            
        out.append('%sExtraPVs End' % (self.com2))
        self.write_lines(out)

    def write_timestamp(self):
        "write timestamp"
        self.check_writeable()
        self.write("%sTime: %s\n" % (self.com2, time.ctime()))

    def write_legend(self):
        "write legend"
        self.check_writeable()
        cols = []
        legend = []
        for i, pos in enumerate(self.scan.positioners):
            key = 'p%i' % (i+1)
            cols.append(" %s%s " % (key, ' '*7))            
            legend.append("%s %s = %s (%s)" % (self.comchar, key,
                                               pos.label,
                                               pos.pv.pvname))
        for i, det in enumerate(self.scan.counters):
            key = 'd%i' % (i)               
            cols.append(" %s%s " % (key, ' '*7))
            legend.append("%s %s = %s (%s)" % (self.comchar, key,
                                               det.label,
                                               det.pv.pvname))
        out = ['%sLegend Start:' % self.com2]
        for l in legend:
            out.append(l)
        self.column_label = '%s %s' % (self.comchar, '\t'.join(cols))
        out.append('%sLegend End' % self.com2)
        self.write_lines(out)        

    def write_data(self, breakpoint=0, clear=True, close_file=False):
        "write data"
        self.write_timestamp()
        if breakpoint == 0:
            self.write_legend()
            return
        
        self.write_extrapvs()
        out = ['%s%s' % (self.comchar, '-'*66)]
        out.append(self.column_label)
        
        n = len(self.scan.counters[0].buff)
        for i in range(n):
            words =  ["%9f" % curpos for curpos in self.scan.pos_actual[i]]
            words.extend(["%9f" % c.buff[i] for c in self.scan.counters])
            out.append('\t'.join(words))
        self.write_lines(out)
        if clear:
            [c.clear() for c in self.scan.counters]
            self.scan.pos_actual = []
        
        if close_file:
            self.close()
