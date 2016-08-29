#!/usr/bin/env python
"""
Wrapper for pyFAI integration and saving of xy 1D XRD data
mkak 2016.07.06 // updated 2013.08.23
"""
import time
import os

import fabio
from pyFAI.multi_geometry import MultiGeometry
import pyFAI.calibrant
import pyFAI

def integrate_xrd(xrd_map, calfile, aname, unit='q', steps=10000, fnum=None, verbose=False):
    
    if unit == 'q':
        iunit = 'q_A^-1'
    elif unit == '2th':
        iunit='2th_deg'
    else:
        print 'Unknown unit: %s. Using q.' % unit
        unit = 'q'
        iunit = 'q_A^-1'
    
    path, cali = os.path.split(str(calfile))
    counter = 1
    while os.path.exists('%s/XRD-%s-%03d.xy' % (path,aname,counter)):
            counter += 1

    t0 = time.time()
    ai = pyFAI.load(calfile)   
    fname = '%s/XRD-%s-%03d.xy' % (path,aname,counter)
    print '\nSaving %s data in file: %s\n' % (unit,fname)
    q,I = ai.integrate1d(xrd_map, steps, unit=iunit,filename=fname)    
    
    t1 = time.time()
    if verbose:
        print('\ttime to integrate data = %7.1f ms' % ((t1-t0)*1000))
        
    return q,I
    