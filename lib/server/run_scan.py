import time
import sys
import json
import numpy as np

from ..detectors import get_detector
from ..positioner import Positioner
from ..stepscan import StepScan
from ..xafs_scan import XAFS_Scan

from .utils import js2ascii

def read_scanconf(scanfile):
    """read a scan defined (with JSON-encoded string) in a file,
    return scan configuration dictionary"""
    fh = open(scanfile, 'r')
    text = fh.read()
    fh.close()
    return json.loads(text, object_hook=js2ascii)


def run_scanfile(scanfile):
    """run a scan defined (with JSON-encoded string) in a file"""
    run_scan(read_scanconf(scanfile))

def messenger(cpt=0, npts=1, scan=None, **kws):
    if cpt == 1:
        pass # print dir(scan)
    msg = '%i,' % cpt
    if cpt % 15 == 0:
        msg = "%s\n" % msg
    sys.stdout.write(msg)
    sys.stdout.flush()

def debug_scan(**conf):
    print 'debug scan !'
    print conf

def run_scan(conf):
    """runs a scan as specified in a scan configuration dictionary"""
    if conf['type'] == 'xafs':

        scan  = XAFS_Scan(energy_pv=conf['energy_drive'],
                          read_pv=conf['energy_read'],
                          e0 = conf['e0'])

        t_kw  = conf['time_kw']
        t_max = conf['max_time']
        nreg  = len(conf['regions'])
        kws  = {'relative': conf['is_relative']}
        for i, det in enumerate(conf['regions']):
            start, stop, npts, dt, units = det
            kws['dtime'] =  dt
            kws['use_k'] =  units.lower() !='ev'
            if i == nreg-1: # final reg
                if t_max > dt and t_kw>0 and kws['use_k']:
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

    elif conf['type'] == 'mesh':
        scan = StepScan()
        label1, pvs1, start1, stop1, npts1 = conf['inner']
        label2, pvs2, start2, stop2, npts2 = conf['outer']

        p1 = Positioner(pvs1[0], label=label1)
        p2 = Positioner(pvs2[0], label=label2)

        inner = npts2* [np.linspace(start1, stop1, npts1)]
        outer = [[i]*npts1 for i in np.linspace(start2, stop2, npts2)]

        p1.array = np.array(inner).flatten()
        p2.array = np.array(outer).flatten()

        scan.add_positioner(p1)
        scan.add_positioner(p2)
        if len(pvs1) > 0:
            scan.add_counter(pvs1[1], label="%s(read)" % label1)
        if len(pvs2) > 0:
            scan.add_counter(pvs2[1], label="%s(read)" % label2)

    elif conf['type'] == 'slew':
        scan = StepScan()
        label1, pvs1, start1, stop1, npts1 = conf['inner']
        p1 = Positioner(pvs1[0], label=label1)
        p1.array = np.linspace(start1, stop1, npts1)
        scan.add_positioner(p1)
        if len(pvs1) > 0:
            scan.add_counter(pvs1[1], label="%s(read)" % label1)
        if conf['dimension'] >=2:
            label2, pvs2, start2, stop2, npts2 = conf['outer']
            p2 = Positioner(pvs2[0], label=label2)
            p2.array = np.linspace(start2, stop2, npts2)
            scan.add_positioner(p2)
            if len(pvs2) > 0:
                scan.add_counter(pvs2[1], label="%s(read)" % label2)

    for dpars in conf['detectors']:
        det = get_detector(**dpars)
        scan.add_detector(det)

    if 'counters' in conf:
        for label, pvname  in conf['counters']:
            scan.add_counter(pvname, label=label)

    scan.add_extra_pvs(conf['extra_pvs'])

    scan.dwelltime = conf.get('dwelltime', 1)
    scan.comments  = conf.get('user_comments', '')
    scan.filename  = conf.get('filename', 'scan.dat')
    scan.pos_settle_time = conf.get('pos_settle_time', 0.01)
    scan.det_settle_time = conf.get('det_settle_time', 0.01)
    scan.messenger = messenger

    print 'READY TO RUN SCAN '
    return scan
    # print 'Scan:: ', conf['filename'], conf['nscans']
    #for i in range(conf['nscans']):
    #    outfile = scan.run(conf['filename'], comments=conf['user_comments'])
    #    print 'wrote %s' % outfile

