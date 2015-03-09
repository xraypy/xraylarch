import time
import numpy as np
from functools import partial
import epics
from epics.devices.mca import  MultiXMAP
from epics.devices.struck import Struck

from epics.wx import EpicsFunction, DelayedEpicsCallback

from larch import use_plugin_path

use_plugin_path('xrf')
from mca import MCA
from roi import ROI

use_plugin_path('epics')
from xspress3 import Xspress3

class Epics_Xspress3(object):
    """multi-element MCA detector using Quantum Xspress3 electronics 3-1-10
    """
    MAX_FRAMES    = 4000
    MIN_FRAMETIME = 0.20

    def __init__(self, prefix=None, nmca=4, **kws):
        self.nmca = nmca
        self.prefix = prefix
        self.mcas = []
        self.npts  = 4096
        self.energies = []
        self.connected = False
        self.elapsed_real = None
        self.elapsed_textwidget = None
        self.frametime = self.MIN_FRAMETIME
        self.needs_refresh = False
        self._xsp3 = None
        if self.prefix is not None:
            self.connect()

    # @EpicsFunction
    def connect(self):
        self._xsp3 = Xspress3(self.prefix)
        counterpv = self._xsp3.PV('ArrayCounter_RBV')
        counterpv.clear_callbacks()
        counterpv.add_callback(self.onRealTime)
        for imca in range(1, self.nmca+1):
            self._xsp3.PV('ARRSUM%i:ArrayData' % imca)
        time.sleep(0.001)
        self.connected = True

    @EpicsFunction
    def connect_displays(self, status=None, elapsed=None, deadtime=None):
        if elapsed is not None:
            self.elapsed_textwidget = elapsed
        if status is not None:
            pvs = self._xsp3._pvs
            attr = 'StatusMessage_RBV'
            pvs[attr].add_callback(partial(self.update_widget, wid=status))

    @DelayedEpicsCallback
    def update_widget(self, pvname, char_value=None,  wid=None, **kws):
        if wid is not None:
            wid.SetLabel(char_value)

    @DelayedEpicsCallback
    def onRealTime(self, pvname, value=None, **kws):
        self.elapsed_real = value * self.frametime
        self.needs_refresh = True
        if self.elapsed_textwidget is not None:
            self.elapsed_textwidget.SetLabel("  %8.2f" % self.elapsed_real)

    def set_dwelltime(self, dtime=1.0, **kws):
        self._xsp3.useInternalTrigger()
        self._xsp3.FileCaptureOff()

        # count forever, or close to it
        frametime = self.MIN_FRAMETIME
        if dtime < self.MIN_FRAMETIME:
            nframes = self.MAX_FRAMES
        elif dtime > self.MAX_FRAMES*self.MIN_FRAMETIME:
            nframes   = self.MAX_FRAMES
            frametime = 1.0*dtime/nframes
        else:
            nframes   = int((dtime+frametime*0.1)/frametime)
        self._xsp3.NumImages = nframes
        self._xsp3.AcquireTime = self.frametime = frametime
        
    def get_mca(self, mca=1, with_rois=True):
        if self._xsp3 is None:
            self.connect()
            time.sleep(0.5)

        emca = self._xsp3.mcas[mca-1]
        if with_rois:
            emca.get_rois()
        counts = self.get_array(mca=mca)
        if max(counts) < 1.0:
            counts    = 0.5*np.ones(len(counts))
            counts[0] = 2.0

        thismca = MCA(counts=counts, offset=0.0, slope=0.01)
        thismca.energy = self.get_energy()
        thismca.counts = counts
        thismca.rois = []
        if with_rois:
            for eroi in emca.rois:
                thismca.rois.append(ROI(name=eroi.NM, address=eroi.address,
                                        left=eroi.LO, right=eroi.HI))
        return thismca

    def get_energy(self, mca=1):
        return np.arange(self.npts)*.010

    def get_array(self, mca=1):
        try:
            out = 1.0*self._xsp3.get('ARRSUM%i:ArrayData' % mca)
        except TypeError:
            out = np.arange(self.npts)*0.91
            
        if len(out) != self.npts:
            self.npts = len(out)
        out[np.where(out<0.91)]= 0.91
        return out

    def start(self):
        'xspress3 start '
        self.stop()
        self._xsp3.start(capture=False) 
        time.sleep(0.01)

    def stop(self, timeout=0.5):
        self._xsp3.stop()
        t0 = time.time()
        while self._xsp3.Acquire_RBV == 1 and time.time()-t0 < timeout:
            self._xsp3.stop()                
            time.sleep(0.005)

    def erase(self):
        self.stop()
        self._xsp3.ERASE = 1

    def del_roi(self, roiname):
        for mca in self._xsp3.mcas:
            mca.del_roi(roiname)
        self.rois = self._xsp3.mcas[0].get_rois()

    def add_roi(self, roiname, lo=-1, hi=-1):
        for mca in self._xsp3.mcas:
            mca.add_roi(roiname, lo=lo, hi=hi)
        self.rois = self._xsp3.mcas[0].get_rois()

    @EpicsFunction
    def rename_roi(self, i, newname):
        roi = self._xsp3.mcas[0].rois[i]
        roi.NM = newname
        rootname = roi._prefix
        for imca in range(1, len(self._xmap.mcas)):
            pvname = rootname.replace('mca1', 'mca%i'  % (1+imca))
            epics.caput(pvname+'NM', newname)

    def restore_rois(self, roifile):
        print 'restore rois from ', roifile
        self._xsp3.restore_rois(roifile)
        self.rois = self._xsp3.mcas[0].get_rois()

    def save_rois(self, roifile):
        buff = self._xsp3.roi_calib_info()
        with open(roifile, 'w') as fout:
            fout.write("%s\n" % "\n".join(buff))


class Epics_MultiXMAP(object):
    """multi-element MCA detector using XIA xMAP electronics
    and epics dxp 3.x series of software

    mcas    list of MCA objects

    connect()
    set_dwelltime(dtime=0)
    start()
    stop()
    erase()
    add_roi(roiname, lo, hi)
    del_roi(roiname)
    clear_rois()
    save_ascii(filename)
    get_energy(mca=1)
    get_array(mca=1)
    """
    def __init__(self, prefix=None, nmca=4, **kws):
        self.nmca = nmca
        self.prefix = prefix
        self.mcas = []
        self.energies = []
        self.connected = False
        self.elapsed_real = None
        self.needs_refresh = False
        if self.prefix is not None:
            self.connect()

    @EpicsFunction
    def connect(self):
        self._xmap = MultiXMAP(self.prefix, nmca=self.nmca)
        self._xmap.PV('ElapsedReal', callback=self.onRealTime)
        self._xmap.PV('DeadTime')
        time.sleep(0.001)
        self.mcas = self._xmap.mcas
        self.connected = True
        # self._xmap.SpectraMode()
        self.rois = self._xmap.mcas[0].get_rois()

    @EpicsFunction
    def connect_displays(self, status=None, elapsed=None, deadtime=None):
        pvs = self._xmap._pvs
        if elapsed is not None:
            self.elapsed_textwidget = elapsed
        for wid, attr in ((status, 'Acquiring'),(deadtime, 'DeadTime')):
            if wid is not None:
                pvs[attr].add_callback(partial(self.update_widget, wid=wid))

    @DelayedEpicsCallback
    def update_widget(self, pvname, char_value=None,  wid=None, **kws):
        if wid is not None:
            wid.SetLabel(char_value)

    @DelayedEpicsCallback
    def onRealTime(self, pvname, value=None, **kws):
        self.elapsed_real = value
        self.needs_refresh = True
        # print(" onRealTime ", pvname, value)
        if self.elapsed_textwidget is not None:
            self.elapsed_textwidget.SetLabel("  %8.2f" % value)


    def set_dwelltime(self, dtime=0):
        if dtime <= 0.1:
            self._xmap.PresetMode = 0
        else:
            self._xmap.PresetMode = 1
            self._xmap.PresetReal = dtime

    def start(self):
        return self._xmap.start()

    def stop(self):
        return self._xmap.stop()

    def erase(self):
        self._xmap.put('EraseAll', 1)

    def get_array(self, mca=1):
        out = 1.0*self._xmap.mcas[mca-1].get('VAL')
        out[np.where(out<0.91)]= 0.91
        return out

    def get_energy(self, mca=1):
        return self._xmap.mcas[mca-1].get_energy()

    def get_mca(self, mca=1, with_rois=True):
        """return an MCA object """
        emca = self._xmap.mcas[mca-1]
        if with_rois:
            emca.get_rois()
        counts = self.get_array(mca=mca)
        if max(counts) < 1.0:
            counts    = 0.5*np.ones(len(counts))
            counts[0] = 2.0

        thismca = MCA(counts=counts, offset=emca.CALO, slope=emca.CALS)
        thismca.energy = emca.get_energy()
        thismca.counts = counts
        thismca.rois = []
        if with_rois:
            for eroi in emca.rois:
                thismca.rois.append(ROI(name=eroi.NM, address=eroi.address,
                                        left=eroi.LO, right=eroi.HI))
        return thismca

    def clear_rois(self):
        for mca in self._xmap.mcas:
            mca.clear_rois()
        self.rois = self._xmap.mcas[0].get_rois()

    @EpicsFunction
    def del_roi(self, roiname):
        for mca in self._xmap.mcas:
            mca.del_roi(roiname)
        self.rois = self._xmap.mcas[0].get_rois()

    def add_roi(self, roiname, lo=-1, hi=-1):
        calib = self._xmap.mcas[0].get_calib()
        for mca in self._xmap.mcas:
            mca.add_roi(roiname, lo=lo, hi=hi, calib=calib)
        self.rois = self._xmap.mcas[0].get_rois()

    @EpicsFunction
    def rename_roi(self, i, newname):
        roi = self._xmap.mcas[0].rois[i]
        roi.NM = newname
        rootname = roi._prefix
        for imca in range(1, len(self._xmap.mcas)):
            pvname = rootname.replace('mca1', 'mca%i'  % (1+imca))
            epics.caput(pvname+'NM', newname)

    def restore_rois(self, roifile):
        self._xmap.restore_rois(roifile)
        self.rois = self._xmap.mcas[0].get_rois()

    def save_rois(self, roifile):
        buff = self._xmap.roi_calib_info()
        with open(roifile, 'w') as fout:
            fout.write("%s\n" % "\n".join(buff))

    def save_mca(self, fname):
        buff = self._xmap
        
