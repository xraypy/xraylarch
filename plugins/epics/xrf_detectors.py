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
    """multi-element MCA detector using Quantum Xspress3 electronics
    AND a triggering Struck SIS multi-channel scaler
    """
    def __init__(self, prefix=None, nmca=4, sis_prefix=None, **kws):
        self.nmca = nmca
        self.prefix = prefix
        self.sis_prefix = sis_prefix
        self.mcas = []
        self.energies = []
        self.connected = False
        self.elapsed_real = None
        self.needs_refresh = False
        if self.prefix is not None:
            self.connect()

    @EpicsFunction
    def connect(self):
        self._sis = None
        if self.sis_prefix is not None:
            self._sis = Struck(self.sis_prefix)
        self._xsp3 = Xspress3(self.prefix)
        self._xmap.PV('DeadTime')
        time.sleep(0.001)
        self.mcas = self._xmap.mcas
        self.connected = True
        self._xmap.SpectraMode()
        self.rois = self._xmap.mcas[0].get_rois()

    def get_mca(self, mca=1):
        raise NotImplemented

    def get_energy(self, mca=1):
        raise NotImplemented

    def get_array(self, mca=1):
        raise NotImplemented

    def save_rois(self, roifile):
        raise NotImplemented

    def restore_rois(self, roifile):
        raise NotImplemented

    def connect_displays(self, status=None, elapsed=None,
                         deadtime=None):
        raise NotImplemented

    def set_dwelltime(self,dtime=1):
        raise NotImplemented

    def start(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def erase(self):
        raise NotImplemented

    def del_roi(self, roiname):
        raise NotImplemented

    def add_roi(self, nam, lo=-1, hi=-1):
        raise NotImplemented




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
        self._xmap.SpectraMode()
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
        if self.elapsed_textwidget is not None:
            self.elapsed_textwidget.SetLabel("  %8.2f" % value)


    def set_dwelltime(self, dtime=0):
        if dtime <= 1.e-3:
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
        return 1.0*self._xmap.mcas[mca-1].get('VAL')

    def get_energy(self, mca=1):
        return self._xmap.mcas[mca-1].get_energy()

    def get_mca(self, mca=1):
        """return an MCA object """
        emca = self._xmap.mcas[mca-1]
        emca.get_rois()
        counts = 1.0*emca.VAL
        if max(counts) < 1.0:
            npts = len(counts)
            counts = counts + np.arange(npts)/(1.0*npts)

        thismca = MCA(counts=counts, offset=emca.CALO, slope=emca.CALS)
        thismca.energy = emca.get_energy()
        thismca.counts = counts
        thismca.rois = []
        for eroi in emca.rois:
            thismca.rois.append(ROI(name=eroi.name, address=eroi.address,
                                    left=eroi.left, right=eroi.right))

        return thismca

    def clear_rois(self):
        for mca in self._xmap.mcas:
            mca.clear_rois()
        self.rois = self._xmap.mcas[0].get_rois()

    def del_roi(self, roiname):
        for mca in self._xmap.mcas:
            mca.del_roi(roiname)
        self.rois = self._xmap.mcas[0].get_rois()

    def add_roi(self, roiname, lo=-1, hi=-1):
        calib = self._xmap.mcas[0].get_calib()
        for mca in self._xmap.mcas:
            mca.add_roi(roiname, lo=lo, hi=hi, calib=calib)
        self.rois = self._xmap.mcas[0].get_rois()

    def restore_rois(self, roifile):
        self._xmap.restore_rois(roifile)
        self.rois = self._xmap.mcas[0].get_rois()

    def save_rois(self, roifile):
        buff = self._xmap.roi_calib_info()
        with open(roifile, 'w') as fout:
            fout.write("%s\n" % "\n".join(buff))

