#!/usr/bin/env python
from __future__ import print_function

import time

class debugtime(object):
    def __init__(self, verbose=False):
        self.clear()
        self.verbose = verbose
        self.add('init')

    def clear(self):
        self.times = []

    def add(self,msg=''):
        if self.verbose:
            print(msg, time.ctime())
        self.times.append((msg,time.time()))

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
        print(self.get_report())
        
    def save(self, fname='debugtimer.dat'):
        dat = self.get_report()
        with open(fname, 'w') as fh:
            fh.write('%s\n' % dat)
        
            
