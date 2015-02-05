#!/usr/bin/env python
# slew scan code for GSECARS / Newport XPS 

MODNAME = '_scan'

import time
from epics import caput, caget
from larch import ValidateLarchPlugin

@ValidateLarchPlugin
def do_fastmap(scan='CurrentScan.ini', datafile='default.dat',
               mapper='13XRM:map:', _larch=None):
    #  execute a fast map
    caput(mapper + 'filename', datafile)
    caput(mapper + 'scanfile', scan)
    time.sleep(0.5)
    caput(mapper + 'Start',  1)

    # step 1: wait for collecting to start (status == 2)
    status = 0
    t0 = time.time()
    while status != 2 and time.time()-t0 < 300:
        status = caget(mapper + 'status')
        time.sleep(0.25)

    print 'fastmap has now started. Waiting for it to finish:'
    maxrow = caget(mapper + 'maxrow')
    time.sleep(1.0)

    # wait for map to finish: must 
    # see "status=Idle" for each of 10 seconds
    collecting_map = True
    nrowx, nrow = 0, 0
    t0 = time.time()
    while collecting_map:
        time.sleep(0.5)
        status = caget(mapper + 'status')        
        nrow = = caget(mapper + 'nrow')
        if nrowx != nrow:
            print ' map at row %i of %i' % (nrow, maxrow)
            nrowx = nrow
        if status == 0:
            collecting_map = ((time.time() - t0) < 10.0)
        else:
            t0 = time.time()
    print ' fastmap has finished!'

def registerLarchPlugin():
    return (MODNAME, {'do_fastmap': do_fastmap})

