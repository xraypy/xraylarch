#!/usr/bin/env python

import os
import sys
import copy
import time
import gc

import numpy as np
from larch import ValidateLarchPlugin, use_plugin_path
from larch.utils import OrderedDict

use_plugin_path('io')
from xdi import XDIFile

XSPRESS3_TAUS = [109.e-9, 91.e-9, 99.e-9, 98.e-9]

def estimate_icr(ocr, tau, niter=3):
    maxicr = 1.0/tau
    maxocr = 1/(tau*np.exp(1.0))
    ocr[np.where(ocr>2*maxocr)[0]] = 2*maxocr
    icr = 1.0*ocr
    for c in range(niter):
        delta = (icr - ocr*np.exp(icr*tau))/(icr*tau - 1)
        delta[np.where(delta < 0)[0]] = 0.0
        icr = icr + delta
        icr[np.where(icr>5*maxicr)[0]] = 5*maxicr
    #endfor
    return icr
#enddef


@ValidateLarchPlugin
def read_gsexdi(fname, _larch=None, nmca=4, **kws):
    """Read GSE XDI Scan Data to larch group,
    summing ROI data for MCAs and apply deadtime corrections
    """
    xdi = XDIFile(fname)

    group = _larch.symtable.create_group()
    group.__name__ ='GSE XDI Data file %s' % fname
    group._xdi = xdi
    group.filename = fname
    group.npts = xdi.npts
    for family in ('scan', 'mono', 'facility'):
        for key, val in xdi.attrs[family].items():
            if '||' in val:
                val, addr = val.split('||')
            try:
                val = float(val)
            except:
                pass
            setattr(group, "%s_%s" % (family, key), val)

        
    ocrs, icrs = [], []
    ctime = xdi.CountTime
    is_xspress3 = any(['13QX4' in a[1] for a in xdi.attrs['column'].items()])
    group.with_xspress3 = is_xspress3
    for i in range(nmca):
        ocr = getattr(xdi, 'OutputCounts_mca%i' % (i+1), None)
        if ocr is None:
            ocr = ctime
        ocr = ocr/ctime
        icr = getattr(xdi, 'InputCounts_mca%i' % (i+1), None)
        if icr is not None:
            icr = icr/ctime
        else:
            icr = 1.0*ocr
            if is_xspress3:
                icr = estimate_icr(ocr, XSPRESS3_TAUS[i], niter=5)
        ocrs.append(ocr)
        icrs.append(icr)
            
    labels = []
    sums = OrderedDict()
    for i, arrname in enumerate(xdi.array_labels):
        dat = getattr(xdi, arrname)
        aname = sumname = arrname.lower()
        if ('_mca' in aname and
            'outputcounts' not in aname and
            'clock' not in aname):
            sumname, imca = sumname.split('_mca')
            imca = int(imca) - 1
            dtcorr = icrs[imca]/ ocrs[imca]
            dat = dat * dtcorr
                
        setattr(group, aname, dat)
        if sumname not in labels:
            labels.append(sumname)
            sums[sumname] = dat
        else:
            sums[sumname] = sums[sumname] + dat
        
    for name, dat in sums.items():
        if not hasattr(group, name):
            setattr(group, name, dat)
            
    for arrname in xdi.array_labels:
        sname = arrname.lower()
        if sname not in labels:
            labels.append(sname)
            
    group.array_labels = labels
    return group

def registerLarchPlugin():
    return ('_io', {'read_gsexdi': read_gsexdi})

