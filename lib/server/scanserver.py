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
from ..scandb import ScanDB, ScanDBException, make_datetime
from ..utils import get_units
from ..file_utils import fix_varname

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
            scan.add_counter(pvs1[1], label="%s_read" % label1)
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
    scan.scantime  = sdict.get('scantime', -1)
    scan.filename  = sdict.get('filename', 'scan.dat')
    scan.pos_settle_time = sdict.get('pos_settle_time', 0.01)
    scan.det_settle_time = sdict.get('det_settle_time', 0.01)
    if scan.dwelltime is None:
        scan.set_dwelltime(sdict.get('dwelltime', 1))

    return scan

class ScanWatcher(threading.Thread):
    """ Thread to watch for scandb status requests (Abort, Pause, Resume)
    and pass them to the current StepScan"""
    scan_timeout  = 3*86400.0
    start_timeout =     300.0
    def __init__(self, scandb, scan=None, imsg=None, **kws):
        threading.Thread.__init__(self)
        self.scandb = scandb
        self.get_info = scandb.get_info
        self.scan = scan
        self.imsg = imsg
        
    def set_scan_message(self, msg, verbose=False):
        self.scandb.set_info('scan_message', msg)
        if verbose:
            print 'ScanWatcher: ', msg
        self.scandb.commit()

    def run(self):
        """execute thread, watching for abort/pause/resume"""
        t0 = time.time()
        scan = self.scan
        scan_started = False
        last_imsg = -10
        npts = int(self.get_info('scan_total_points') )
        while True:
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                return
            if time.time()-t0 > self.scan_timeout or scan is None:
                return
            # if scan has not yet started
            if scan.cpt > 1:
                scan_started = True
            if self.get_info('request_command_killall', as_bool=True):
                return
            if self.imsg is not None:
                self.set_scan_message('Point %i / %i' % (scan.cpt, npts))
                if scan.cpt % self.imsg == 0 and scan.cpt > last_imsg:
                    # print '%i / %i ' % (scan.cpt, npts)
                    last_imsg = scan.cpt
                    
            if not scan_started:
                if time.time()-t0 > self.start_timeout:
                    return
                continue
            # saw scan begin, and it is now complete!
            if scan_started and scan.complete:
                self.set_scan_message('Scan Complete.', verbose=True)
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
        if scan is None:
            return
        # print '  scan  ', cpt, npts, scan.filename
        time_left = (npts-cpt)* (scan.pos_settle_time + scan.det_settle_time )
        if scan.dwelltime_varys:
            time_left += scan.dwelltime[cpt:].sum()
        else:
            time_left += (npts-cpt)*scan.dwelltime
        self.scandb.set_info('scan_time_estimate', time_left)
        if cpt < 4:
            self.scandb.set_info('filename', scan.filename)
        for c in scan.counters:
            self.scandb.set_scandata(fix_varname(c.label), c.buff)

    def scan_prescan(self, scan=None, **kws):
        pass

    def set_scan_message(self, msg, verbose=True):
        self.scandb.set_info('scan_message', msg)
        if verbose:
            print 'ScanServer: ', msg
        self.scandb.commit()

    def do_scan(self, scanname, filename=None):
        self.set_scan_message('Preparing Scan (loading def)')
        self.scan = load_dbscan(self.scandb, scanname)

        self.scan.complete = False
        self.scan.pre_scan_methods.append(self.scan_prescan)
        self.scandb.clear_scandata()
        npts = -1
        names = []
        self.set_scan_message('Preparing Scan (positioners)')

        for p in self.scan.positioners:
            units = get_units(p.pv, 'unknown')
            npts = max(npts, len(p.array))
            name = fix_varname(p.label)
            if name in names:
                name += '_2'
            if name not in names:
                self.scandb.add_scandata(name, p.array.tolist(),
                                         pvname=p.pv.pvname,
                                         units=units, notes='positioner')
                names.append(name)
        names = []                
        self.set_scan_message('Preparing Scan (counters)')
        for c in self.scan.counters:
            units = get_units(c.pv, 'counts')
            name = fix_varname(c.label)
            if name in names:
                name += '_2'
            if name not in names:
                self.scandb.add_scandata(name, [],
                                         pvname=c.pv.pvname,
                                         units=units, notes='counter')
                names.append(name)
                
        if not hasattr(self.scan, 'scantime') or self.scan.scantime < 0:
            self.scan.scantime = npts*(self.scan.pos_settle_time +
                                       self.scan.det_settle_time +
                                       self.scan.dwelltime)
        self.scandb.set_info('scan_time_estimate', self.scan.scantime)
        self.scandb.set_info('scan_total_points', npts)
        self.scandb.set_info('request_command_abort', 0)
        self.scan.messenger = self.scan_messenger
        self.set_scan_message('Preparing Scan (watcher)')

        self.scanwatcher = ScanWatcher(self.scandb, scan=self.scan, imsg=25)

        self.scanwatcher.start()
        self.scandb.update_where('scandefs', {'name': scanname},
                                 {'last_used_time': make_datetime()})

        self.scan.filename = filename
        self.scandb.set_info('filename', filename)
        self.set_scan_message('Starting Scan')

        self.scan.run(filename=filename)
        self.set_scan_message('Finishing')
        self.scandb.commit()

        if self.scanwatcher is not None:
            self.scanwatcher.join()
        self.set_scan_message('Scan Complete. Wrote %s' % self.scan.filename)
        # print 'scan complete (do_scan), Wrote %s' % self.scan.filename

    def do_caput(self, pvname, value, wait=False, timeout=30.0):
        epics.caput(pvname, value, wait=wait, timeout=timeout)

    def sleep(self, t=0.05):
        try:
            time.sleep(t)
        except KeyboardInterrupt:
            self.abort = True

    def finish(self):
        print 'shutting down!'

    def execute_command(self, req):
        print 'Execute: ', req.id, req.command, req.arguments, req.output_file
        #print 'req.id      = ', req.id
        #print 'req.arguments = ', req.arguments
        #print 'req.status_id, req.status = ', req.status_id
        #print 'req.request_time = ', req.request_time
        #print 'req.start_time = ', req.start_time
        #print 'req.modify_time = ', req.modify_time
        #print 'req.output_value = ', req.output_value
        #print 'req.output_file = ', req.output_file

        cmd_thread = threading.Thread(target=self.do_command,
                                      kwargs=dict(req=req),
                                      name='cmd_thread')
        self.scandb.set_info('scan_status', 'starting')
        self.scandb.set_command_status(req.id, 'starting')
        req_id = req.id
        self.command_in_progress = True
        cmd_thread.start()
        cmd_thread.join()
        self.scandb.set_command_status(req.id, 'finished')
        self.scandb.set_info('scan_status', 'idle')
        self.scandb.commit()
        self.command_in_progress = False

    def do_command(self, req=None, **kws):
        self.scandb.set_info('scan_status', 'running')
        self.scandb.set_command_status(req.id, 'running')
        if req.command == 'doscan':
            self.do_scan(str(req.arguments), filename=req.output_file)
        else: 
            print 'unknown command ', req.command
        time.sleep(3.0)
        self.scandb.set_command_status(req.id, 'stopping')

    def look_for_interrupt_requests(self):
        """set interrupt requests:
        abort / pause / resume
        it is expected that
        """
        def isset(infostr):
            return self.db.get_info(infostr, as_bool=True)
        self.abort_request = isset('request_command_abort')
        self.pause_request = isset('request_command_pause')
        self.resume_request = isset('request_command_resume')

    def mainloop(self):
        self.set_scan_message('Server Starting')
        self.scandb.set_info('scan_status', 'idle')
        msgtime = time.time()
        self.set_scan_message('Server Ready')
        while True:
            self.sleep(0.25)
            if self.abort:   
                break
            reqs = self.scandb.get_commands('requested')
            if (time.time() - msgtime )> 300:
                print '#Server Alive, nrequests = ', len(reqs)
                msgtime = time.time()
            if self.command_in_progress:
                self.look_for_interrupt_requests()
                if self.abort_request:
                    print '#Abort request'
                elif self.pause_request:
                    print '#Pause Request'
                elif self.resume_request:
                    print '#Resume Request'
            elif len(reqs) > 0: # and not self.command_in_progress:
                print '#Execute Next Command: '
                self.execute_command(reqs.pop(0))

        # mainloop end
        self.finish()
        sys.exit()




if __name__  == '__main__':
    s = ScanServer(dbname='A.sdb')
    s.mainloop()


