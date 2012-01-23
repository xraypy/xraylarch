import time

class debugtime(object):
    def __init__(self):
        self.clear()
        self.add('init')

    def clear(self):
        self.times = []

    def add(self,msg=''):
        # print msg
        self.times.append((msg,time.time()))

    def show(self):
        m0,t0 = self.times[0]
        tlast= t0
        print "# %s  %s " % (m0,time.ctime(t0))
        print "#----------------"
        print "#       Message                       Total     Delta"
        for m,t in self.times[1:]:
            tt = t-t0
            dt = t-tlast
            if len(m)<32:
                m = m + ' '*(32-len(m))
            print "  %32s    %.3f    %.3f" % (m,tt, dt)
            tlast = t
