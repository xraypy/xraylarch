import time
import numpy as np
from epics.devices.mca import MCA
from epics import PV, caget
from collections import deque



mca = MCA('13SDD1:', mca=1)
mca.get_rois(nrois=31)

 
class ROI_Averager():
    "A ring buffer using numpy arrays"
    MAX_TIME = 604800.0  # 1 week
    def __init__(self, roi_pv, reset_pv=None, nsamples=21):
        self.pv = None
        self.nsamples  = nsamples
        self.time_offset = time.time()
        self.set_pv(roi_pv)
        if reset_pv is not None:
            self.reset = PV(reset_pv, callback=self._onreset)
            
    def clear(self):
        self.index = -1
        self.lastval = 0
        self.data  = np.zeros(self.nsamples, dtype='i32')
        self.times = np.ones(self.nsamples, dtype='f32') * 0.0
        
    def append(self, x):
        "adds array x to ring buffer"
        idx = (self.index + 1) % self.data.size
        self.data[idx] = max(0, (x - self.lastval))
        self.lastval = x
        newtime = time.time() - self.time_offset
        self.times[idx] =  newtime
        if newtime > self.MAX_TIME:
            self.times       -= self.MAX_TIME
            self.time_offset += self.MAX_TIME
        self.index = idx
        
    def _onreset(self, pvname, value=None, **kws):
        if value==1:
            pass

    def _onupdate(self, pvname=None, value=None, **kws):
        self.append(value)
        
    def set_pv(self, pvname):
        if self.pv is not None:
            self.pv.clear_callbacks()
            del self.pv
        self.clear()
        self.pv = PV(pvname, callback=self._onupdate)
        
    def average(self):
        return self.data.sum() / self.times.ptp()
    
roi_buff = ROI_Averager('13SDD1:mca1.R12',  nsamples=11)   
    
for i in (5, 7, 9, 10, 12):
    print ' === ', i ,    caget('13SDD1:mca1.R%iNM' % i)
    roi_buff.set_pv('13SDD1:mca1.R%i' % i)
    t0 = time.time()
    while time.time()-t0 < 6:
        time.sleep(0.25)
        # print roi_buff.times.ptp(),  roi_buff.data[:5], roi_buff.data.max(),  roi_buff.average()
        print "{:s}: {:,.1f}".format(roi_buff.pv.pvname, roi_buff.average())
