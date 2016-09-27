#!/usr/bin/env python
"""
timer helps profile how long it takes to run
portions of code, and writes a simple report
"""

import time
import sys
from larch import ValidateLarchPlugin

class DebugTimer(object):
    def __init__(self, _larch=None):
        self._larch = _larch
        self.clear()

    def clear(self):
        self.times = []
        self.add('started timer')
        
    def add(self,msg=''):
        # print(msg)
        self.times.append((msg,time.time()))

    def get_report(self, ):
        m0,t0 = self.times[0]
        tlast= t0
        buff = []
        buff.append("# %s  %s " % (m0,time.ctime(t0)))
        buff.append("#----------------")
        buff.append("#   Message                           Total    Delta")
        for m,t in self.times[1:]:
            tt = t-t0
            dt = t-tlast
            if len(m)<32:
                m = m + ' '*(32-len(m))
            buff.append("  %32s    %.3f    %.3f" % (m,tt, dt))
            tlast = t
        buff.append('')
        return '\n'.join(buff)

    def show_report(self, clear=True):
        writer = sys.stdout
        if self._larch is not None:
            writer = self._larch.writer
        writer.write(self.get_report())
        if clear:
            self.clear()

@ValidateLarchPlugin
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
    return DebugTimer(_larch=_larch)

   
def registerLarchPlugin():
    return ('_builtin', {'debugtimer': debugtimer})
