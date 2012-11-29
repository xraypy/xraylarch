import time
import numpy as np
import lib as scan
import sys
sscan = scan.StepScan()
from .detectors import Counter, get_detector
from .positioner import Positioner
from .datafile import ASCIIScanFile
from .stepscan import StepScan
from .xafs_scan import XAFS_Scan
import json


def run_scanfile(scanfile):
    print 'running scan from ', scanfile
    fh = open(scanfile, 'r')
    text = fh.read()
    fh.close()
    run_scan(text)

def js2ascii(inp):
    """convert unicode in json text to ASCII"""
    if isinstance(inp, dict):
        return dict([(js2ascii(k), js2ascii(v)) for k, v in inp.iteritems()])
    elif isinstance(inp, list):
        return [js2ascii(k) for k in inp]
    elif isinstance(inp, unicode):
        return inp.encode('utf-8')
    else:
        return inp

def messenger(cpt=0, npts=1, scan=None, **kws):
    if cpt == 1:
        print dir(scan)
    msg = '%i,' % cpt
    if cpt % 15 == 0: msg = "%s\n" % msg
    # print [d.buff for d in scan.counters]
    sys.stdout.write(msg)
    sys.stdout.flush()
    
def run_scan(json_text):
    conf = json.loads(json_text, object_hook=js2ascii)

    if conf['type'] == 'xafs':
        scan  = XAFS_Scan()
        isrel = conf['is_relative']
        e0    = conf['e0']
        t_kw  = conf['time_kw']
        t_max = conf['max_time']
        nreg  = len(conf['regions'])
        kws   = {'relative': isrel, 'e0':e0}
        
        for i, det in enumerate(conf['regions']):
            start, stop, npts, dt, units = det
            kws['dtime'] =  dt
            kws['use_k'] =  units.lower() !='ev'
            if i == nreg-1: # final reg
                if t_max > 0.01 and t_kw>0 and kws['use_k']:
                    kws['dtime_final'] = t_max
                    kws['dtime_wt'] = t_kw
            scan.add_region(start, stop, npts=npts, **kws)

    elif conf['type'] == 'linear':
        scan = StepScan()
        for pos in conf['positioners']:
            label, pvs, start, stop, npts = pos
            p = Positioner(pvs[0], label=label)
            p.array = np.linspace(start, stop, npts)
            scan.add_positioner(p)
            if len(pvs) > 0:
                scan.add_counter(pvs[1], label="%s(read)" % label)

    for det in conf['detectors']:
        name = det.pop('prefix')
        scan.add_detector(get_detector(name, **det))

    for label, pvname  in conf['counters']:
        scan.add_counter(pvname, label=label)

    scan.add_extra_pvs(conf['extra_pvs'])

    #for attr in dir(scan):
    #    if not attr.startswith('_'):
    #        print attr, getattr(scan, attr)
    
    scan.dwelltime = conf['dwelltime']
    scan.comments  = conf['user_comments']
    scan.filename  = conf['filename']
    scan.pos_settle_time = conf['pos_settle_time']
    scan.det_settle_time = conf['det_settle_time']
    scan.messenger = messenger
    
    # print 'Scan:: ', conf['filename'], conf['nscans']
    for i in range(conf['nscans']):
        outfile = scan.run(conf['filename'], comments=conf['user_comments'])
        print 'wrote %s' % outfile
        
