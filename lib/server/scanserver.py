#!/usr/bin/env python

import time
import threading

import time
import sys
import json
import numpy as np

import epics
from ..detectors import get_detector
from ..positioner import Positioner
from ..stepscan import StepScan
from ..xafs_scan import XAFS_Scan
from ..scandb import ScanDB, ScanDBException
from ..utils import get_units
from ..file_utils import fix_filename

def load_dbscan(scandb, scanname):
    """load a scan definition from the database
    return a stepscan object with hooks into database.
    """
    try:
        sdict = scandb.get_scandict(scanname)
    except ScanDBException:
        return None
    scan = StepScan()
    if sdict['type'] == 'xafs':
        scan  = XAFS_Scan(energy_pv=sdict['energy_drive'],
                          read_pv=sdict['energy_read'],
                          e0=sdict['e0'])
        t_kw  = sdict['time_kw']
        t_max = sdict['max_time']
        nreg  = len(sdict['regions'])
        kws  = {'relative': sdict['is_relative']}
        for i, det in enumerate(sdict['regions']):
            start, stop, npts, dt, units = det
            kws['dtime'] =  dt
            kws['use_k'] =  units.lower() !='ev'
            if i == nreg-1: # final reg
                if t_max > dt and t_kw>0 and kws['use_k']:
                    kws['dtime_final'] = t_max
                    kws['dtime_wt'] = t_kw
            scan.add_region(start, stop, npts=npts, **kws)

    elif sdict['type'] == 'linear':
        for pos in sdict['positioners']:
            label, pvs, start, stop, npts = pos
            p = Positioner(pvs[0], label=label)
            p.array = np.linspace(start, stop, npts)
            scan.add_positioner(p)
            if len(pvs) > 0:
                scan.add_counter(pvs[1], label="%s_read" % label)
                    
    elif sdict['type'] == 'mesh':
        label1, pvs1, start1, stop1, npts1 = sdict['inner']
        label2, pvs2, start2, stop2, npts2 = sdict['outer']
        p1 = Positioner(pvs1[0], label=label1)
        p2 = Positioner(pvs2[0], label=label2)
        
        inner = npts2* [np.linspace(start1, stop1, npts1)]
        outer = [[i]*npts1 for i in np.linspace(start2, stop2, npts2)]
        
        p1.array = np.array(inner).flatten()
        p2.array = np.array(outer).flatten()
        scan.add_positioner(p1)
        scan.add_positioner(p2)
        if len(pvs1) > 0:
            scan.add_counter(pvs1[1], label="%s_read" % label1)
        if len(pvs2) > 0:
            scan.add_counter(pvs2[1], label="%s_read" % label2)

    elif sdict['type'] == 'slew':
        label1, pvs1, start1, stop1, npts1 = sdict['inner']
        p1 = Positioner(pvs1[0], label=label1)
        p1.array = np.linspace(start1, stop1, npts1)
        scan.add_positioner(p1)
        if len(pvs1) > 0:
            scan.add_counter(pvs[1], label="%s_read" % label1)
        if sdict['dimension'] >=2:
            label2, pvs2, start2, stop2, npts2 = sdict['outer']
            p2 = Positioner(pvs2[0], label=label2)
            p2.array = np.linspace(start2, stop2, npts2)
            scan.add_positioner(p2)
            if len(pvs2) > 0:
                scan.add_counter(pvs2[1], label="%s_read" % label2)

    
    for dpars in sdict['detectors']:
        scan.add_detector(get_detector(**dpars))

    if 'counters' in sdict:
        for label, pvname  in sdict['counters']:
            scan.add_counter(pvname, label=label)
    
    scan.add_extra_pvs(sdict['extra_pvs'])
    scan.dwelltime = sdict.get('dwelltime', 1)
    scan.comments  = sdict.get('user_comments', '')
    scan.filename  = sdict.get('filename', 'scan.dat')
    scan.pos_settle_time = sdict.get('pos_settle_time', 0.01)
    scan.det_settle_time = sdict.get('det_settle_time', 0.01)
    return scan

class ScanWatcher(threading.Thread):
    """ Thread to watch for scandb status requests (Abort, Pause, Resume)
    and pass them to the current StepScan"""
    scan_timeout  = 3*86400.0
    start_timeout =    3600.0
    def __init__(self, scandb, scan=None, **kws):
        threading.Thread.__init__(self)
        self.get_info = scandb.get_info
        self.scan = scan
        
    def run(self):
        """execute thread, watching for abort/pause/resume"""
        t0 = time.time()
        scan = self.scan
        scan_started = False
        while True:
            time.sleep(0.5)
            if time.time()-t0 > self.scan_timeout or scan is None:
                return
            # if scan has not yet started
            if scan.cpt > 1:
                scan_started = True
            if not scan_started:
                if time.time()-t0 > self.start_timeout:
                    return
                continue
            # saw scan begin, and it is now complete!
            if scan_started and scan.complete:
                return
            scan.abort = self.get_info('request_command_abort', as_bool=True)
            scan.pause = self.get_info('request_command_pause', as_bool=True)

class ScanServer():
    def __init__(self, dbname=None, **kws):
        self.scandb = None
        self.abort = False
        self.command_in_progress = False
        if dbname is not None:
            self.connect(dbname, **kws)

    def connect(self, dbname, **kws):
        """connect to Scan Database"""
        self.scandb = ScanDB(dbname, **kws)

    def scan_messenger(self, cpt, npts=0, scan=None, **kws):
        # print 'ScanServer.scan_messenger  ', cpt, scan, scan.filename
        if scan is None:
            return
        if cpt < 3:
            self.scandb.set_info('filename', scan.filename)
        for c in scan.counters:
            self.scandb.set_scandata(fix_filename(c.label), c.buff)

    def scan_prescan(self, scan=None, **kws):
        pass
        

    def do_scan(self, scanname, filename=None):
        self.scan = load_dbscan(self.scandb, scanname)
        self.scan.complete = False
        self.scan.pre_scan_methods.append(self.scan_prescan)
        self.scandb.clear_scandata()
        for p in self.scan.positioners:
            units = get_units(p.pv, 'unknown')
            self.scandb.add_scandata(fix_filename(p.label),
                                     p.array.tolist(),
                                     pvname=p.pv.pvname,
                                     notes=units)
        for c in self.scan.counters:
            units = get_units(c.pv, 'counts')
            self.scandb.add_scandata(fix_filename(c.label), [],
                                     pvname=c.pv.pvname,
                                     units=units)
            
        self.scandb.set_info('request_command_abort', 0)
        self.scandb.set_info('request_command_pause', 0)        
        self.scan.messenger = self.scan_messenger

        self.scanwatcher = ScanWatcher(self.scandb, scan=self.scan)
        self.scanwatcher.start()

        self.scan.run(filename=filename)

        if self.scanwatcher is not None:
            self.scanwatcher.join()
        
    def do_caput(self, pvname, value, wait=False, timeout=30.0):
        print 'do caput ', pvname, value, wait
        epics.caput(pvname, value, wait=wait, timeout=timeout)
        
    def sleep(self, t=0.05):
        try:
            time.sleep(t)
        except KeyboardInterrupt:
            self.abort = True

    def finish(self):
        print 'shutting down!'

    def execute_command(self, req):
        print 'EXECUTE Command ', req
        print 'req.command = ', req.command
        print 'req.arguments = ', req.arguments
        print 'req.status_id, req.status = ', req.status_id, req.status
        print 'req.scandefs = ', req.scandefs
        print 'req.request_time = ', req.request_time
        print 'req.start_time = ', req.start_time
        print 'req.modify_time = ', req.modify_time
        print 'req.output_value = ', req.output_value
        print 'req.output_file = ', req.output_file

        cmd_thread = Thread(target=self.do_command,
                            kwargs=dict(req=req),
                            name='cmd_thread')

        self.db.set_command_status(req.id, 'starting')
        self.command_in_progress = True
        cmd_thread.start()
        cmd_thread.join()
        self.db.set_command_status(req.id, 'finished')
        self.command_in_progress = False

    def do_command(self, req):
        print 'IN do_command ', req
        time.sleep(3.0)
        print 'command done!'

    def look_for_interrupt_requests(self):
        """set interrupt requests:
        abort / pause / resume
        it is expected that
        """
        get = self.db.get_info
        self.abort_request = get('request_command_abort') == '1'
        self.pause_request = get('request_command_pause') == '1'
        self.resume_request = get('request_command_resume') == '1'

    def mainloop(self):
        print "starting server"

        while True:
            self.sleep()
            print 'tick'
            if self.abort:   break
            reqs = self.db.get_commands('requested')
            if self.command_in_progress:
                self.look_for_interrupt_requests()
                self.sleep(t=0.10)
            if len(reqs) == 0 or self.command_in_progress:
                self.sleep(t=0.10)
            else:
                nextreq = reqs.pop()
                print 'Will do next request: ', nextreq
                self.execute_command(nextreq)

        # mainloop end
        self.finish()




if __name__  == '__main__':
    s = ScanServer(dbname='A.sdb')
    s.mainloop()


