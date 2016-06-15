import time
import numpy as np

from epics import PV
import larch
larch.use_plugin_path('wx')
from xrfdisplay_utils import ROI_Averager

x = PV('13SDD1:mca1.R16')
ave = ROI_Averager(nsamples=11)

t0 = time.clock()

count = 0
last_val = 0
while time.clock()-t0 < 60:
    count += 1
    time.sleep(0.01)
    val = x.get()
    if val != last_val:
        ave.update(val)
        last_val = val
        print ' ==> %7.1f %7.1f      %7.1f' % ( val, ave.get_cps(),  ave.get_mean())
               
