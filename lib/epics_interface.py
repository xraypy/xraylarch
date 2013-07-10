##

USE_EPICS_EMULATOR = False

import time

from epics import PV, caget, caput, poll

def dummy_caget(pv, **kws):
    return pv

def dummy_caput(pv, value, **kws):
    return value

def dummy_poll(**kws):
    time.sleep(0.001)
    return True

class DummyPV:
    def __init__(self, pvname, **kws):
        self.pvname = pvname
        self.value  =  0
        self.connected = True
        self.upper_ctrl_limit = +1.e99
        self.lower_ctrl_limit = -1.e99
        self.units = ''
        
    def connect(self, **kws):
        return True
    
    def get(self, use_monitor=True, **kws):
        return self.value

    def get_ctrlvars(self, **kws):
        return self.value
    
    def put(self, value, wait=False, callback=None, **kws):
        self.value = value
        if callback is not None:
            callback(pvname=self.pvname, value=value)
            

if USE_EPICS_EMULATOR:
    PV = DummyPV
    caget = dummy_caget
    caput = dummy_caput
    poll  = dummy_poll


