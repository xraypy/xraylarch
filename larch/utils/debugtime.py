#!/usr/bin/env python
from __future__ import print_function

import time
import sys

class debugtime(object):
    def __init__(self, verbose=False, _larch=None):
        self._larch = _larch
        self.clear()
        self.verbose = verbose
        self.add('init')

    def clear(self):
        self.times = []

    def _print(self, *args):
        writer = sys.stdout
        if self._larch is not None:
            writer = self._larch.writer
        writer.write(*args)


    def add(self,msg=''):
        if self.verbose:
            self._print(msg, time.ctime())
        self.times.append((msg, time.time()))

    def get_report(self):
        m0, t0 = self.times[0]
        tlast= t0
        out = []
        add = out.append
        add("# %s  %s " % (m0,time.ctime(t0)))
        add("#----------------")
        add("#       Message                       Total     Delta")
        for m,t in self.times[1:]:
            tt = t-t0
            dt = t-tlast
            if len(m)<32:
                m = m + ' '*(32-len(m))
            add("  %32s    %.3f    %.3f" % (m,tt, dt))
            tlast = t
        return "\n".join(out)

    def show(self):
        self._print(self.get_report())

    def save(self, fname='debugtimer.dat'):
        dat = self.get_report()
        with open(fname, 'w') as fh:
            fh.write('%s\n' % dat)

def debugtimer(_larch=None):
    """debugtimer returns a Timer object that can be used
    to time the running of portions of code, and then
    write a simple report of the results.  the Timer object
    has methods:

      clear()   -- reset Timer
      add(msg)  -- record time, with message
      show_report -- print timer report

    An example:

      timer = debugtimer()
      x = 1
      timer.add('now run foo')
      foo()
      timer.add('now run bar')
      bar()
      timer.show_report()
    """
    return debugtime(_larch=_larch)
