import time
import numpy as np
from functools import partial

try:
    import epics
    from epics.devices.mca import  MultiXMAP
    from epics.devices.struck import Struck
    from epics.wx import EpicsFunction, DelayedEpicsCallback
    HAS_EPICS = True
except (NameError, ImportError, AttributeError):
    HAS_EPICS = False
    EpicsFunction = lambda fcn: fcn
    DelayedEpicsCallback = lambda fcn: fcn

from .xspress3 import Xspress3, Xspress310

from ..xrf import MCA, ROI, Environment

def save_gsemcafile(filename, mcas, rois, environ=None):
    """save GSECARS-style MCA file

    rois = self._xsp3.get_rois()
    realtime = self._xsp3.AcquireTime * self._xsp3.ArrayCounter_RBV
    nelem = len(self._xsp3.mcas)
    mcas = [self.get_mca(mca=i+1, with_rois=False) for i in range(nelem)]

    npts = len(mcas[0].counts)
    nrois = len(rois[0])
    nelem = len(mcas)
    """
    nelem = len(mcas)
    npts  = len(mcas[0].counts)
    nrois = len(rois[0])

    s_rtime = " ".join(["%.4f" % m.real_time for m in mcas])
    s_off   = " ".join(["%.6f" % m.offset    for m in mcas])
    s_quad  = " ".join(["%.6f" % m.quad      for m in mcas])
    s_slope = " ".join(["%.6f" % m.slope     for m in mcas])
    s_rois  = " ".join(["%i"   % nrois       for m in mcas])

    buff = []
    buff.append('VERSION:    3.1')
    buff.append('ELEMENTS:   %i' % nelem)
    buff.append('DATE:       %s' % time.ctime())
    buff.append('CHANNELS:   %i' % npts)
    buff.append('REAL_TIME:  %s' % s_rtime)
    buff.append('LIVE_TIME:  %s' % s_rtime)
    buff.append('CAL_OFFSET: %s' % s_off)
    buff.append('CAL_SLOPE:  %s' % s_slope)
    buff.append('CAL_QUAD:   %s' % s_quad)

    # Write ROIS  in channel units
    buff.append('ROIS:       %s' % s_rois)
    for iroi, roi in enumerate(rois[0]):
        name = [roi.name]
        left = ['%i' % roi.left]
        right = ['%i' % roi.right]
        for other in rois[1:]:
            name.append(other[iroi].name)
            left.append('%i' % other[iroi].left)
            right.append('%i' % other[iroi].right)
        name = '& '.join(name)
        left = '& '.join(left)
        right = '& '.join(right)
        buff.append('ROI_%i_LEFT:  %s' % (iroi, left))
        buff.append('ROI_%i_RIGHT: %s' % (iroi, right))
        buff.append('ROI_%i_LABEL: %s' % (iroi, name))

    # environment
    if environ is None:
        environ = []
    for addr, val, desc in environ:
        buff.append('ENVIRONMENT: %s="%s" (%s)' % (addr, val, desc))

    # data
    buff.append('DATA: ')
    for i in range(npts):
        x = ['%i' % m.counts[i] for m in mcas]
        buff.append("%s" % ' '.join(x))

    # write file
    buff.append('')
    fp = open(filename, 'w')
    fp.write("\n".join(buff))
    fp.close()

class Epics_Xspress3(object):
    """
    multi-element MCA detector using Quantum Xspress3 electronics
    and Epics IOC based on AreaDetector2 IOC (3.2?)
    """
    MIN_FRAMETIME = 0.25
    MAX_FRAMES    = 12000
    def __init__(self, prefix=None, nmca=4, version=2, use_sum=True, **kws):
        self.nmca = nmca
        self.prefix = prefix
        self.version = version
        self.mca_array_name = 'MCASUM%i:ArrayData'
        if not use_sum:
            self.mca_array_name = 'MCA%i:ArrayData'
        if version < 2:
            self.mca_array_name = 'ARRSUM%i:ArrayData'
        self.environ = []
        self.mcas = []
        self.npts  = 4096
        self.energies = []
        self.connected = False
        self.elapsed_real = None
        self.elapsed_textwidget = None
        self.needs_refresh = False
        self._xsp3 = None
        if self.prefix is not None:
            self.connect()

        self.nframes = 1
        self.frametime = 1.0

        # determine max frames
        self.frametime = self.MIN_FRAMETIME
        self._xsp3._pvs['NumImages'].put(self.MAX_FRAMES, wait=True)
        time.sleep(0.05)
        rbv = self._xsp3.NumImages_RBV
        while rbv != self.MAX_FRAMES:
            self.MAX_FRAMES = self.MAX_FRAMES - 500.0
            self._xsp3._pvs['NumImages'].put(self.MAX_FRAMES, wait=True)
            time.sleep(0.1)
            rbv = self._xsp3.NumImages_RBV
            if self.MAX_FRAMES < 4000:
                break

    # @EpicsFunction
    def connect(self):
        Creator = Xspress3
        if self.version < 2:
            Creator = Xspress310
        self._xsp3 = Creator(self.prefix, nmca=self.nmca)

        counterpv = self._xsp3.PV('ArrayCounter_RBV')
        counterpv.clear_callbacks()
        counterpv.add_callback(self.onRealTime)
        for imca in range(1, self.nmca+1):
            self._xsp3.PV(self.mca_array_name % imca)
        time.sleep(0.001)
        self.connected = True
        self.mcas = self._xsp3.mcas

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

    def get_deadtime(self, mca=1):
        """return % deadtime"""
        try:
            dval = self._xsp3.get("C%i:DeadTime_RBV" % (mca))
        except:
            dval = 0.0
        return dval

    def set_usesum(self, use_sum=True):
        self.mca_array_name = 'MCASUM%i:ArrayData'
        if not use_sum:
            self.mca_array_name = 'MCA%i:ArrayData'

    def set_dwelltime(self, dtime=1.0, nframes=None, **kws):
        self._xsp3.useInternalTrigger()
        self._xsp3.FileCaptureOff()

        if nframes is None:
            # count forever, or close to it
            frametime = self.MIN_FRAMETIME
            if dtime < self.MIN_FRAMETIME:
                nframes = self.MAX_FRAMES
            elif dtime > self.MAX_FRAMES*self.MIN_FRAMETIME:
                nframes   = self.MAX_FRAMES
                frametime = 1.0*dtime/nframes
            else:
                nframes   = int((dtime+frametime*0.1)/frametime)
        else:
            frametime = dtime

        self._xsp3.NumImages   = self.nframes   = nframes
        self._xsp3.AcquireTime = self.frametime = frametime

    def get_frametime(self):
        self.nframes = self._xsp3.NumImages
        self.frametime = self._xsp3.AcquireTime
        return self.frametime, self.nframes

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
        thismca.quad   = 0.0
        thismca.rois = []
        if with_rois:
            for eroi in emca.rois:
                thismca.rois.append(ROI(name=eroi.name, address=eroi._prefix,
                                        left=eroi.left, right=eroi.right))
        return thismca

    def get_energy(self, mca=1):
        return np.arange(self.npts)*.010

    def get_array(self, mca=1):
        try:
            out = 1.0*self._xsp3.get(self.mca_array_name % mca)
        except TypeError:
            out = np.arange(self.npts)*0.91

        if len(out) < 1:
            out = np.ones(self.npts)*1.7 + np.sin(np.arange(self.npts)/177.0)*0.8



        if len(out) != self.npts and len(out)>0:
            self.npts = len(out)
        out[np.where(out<0.91)]= 0.91
        return out

    def start(self, erase=True):
        'xspress3 start '
        self.stop()
        if erase:
            self._xsp3.ERASE = 1
            time.sleep(0.01)

        return self._xsp3.start(capture=False)

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
        for mca in self._xsp3.mcas:
            roi = mca.rois[i]
            roi.Name = newname

    def restore_rois(self, roifile):
        self._xsp3.restore_rois(roifile)
        self.rois = self._xsp3.mcas[0].get_rois()

    def save_rois(self, roifile):
        buff = self._xsp3.roi_calib_info()
        with open(roifile, 'w') as fout:
            fout.write("%s\n" % "\n".join(buff))

    def save_columnfile(self, filename, headerlines=None):
        "write summed counts to simple ASCII column file for mca counts"
        f = open(filename, "w+")
        f.write("#XRF counts for %s\n" % self.name)
        if headerlines is not None:
            for i in headerlines:
                f.write("#%s\n" % i)
        f.write("#\n")
        f.write("#EnergyCalib.offset = %.9g \n" % self.offset)
        f.write("#EnergyCalib.slope = %.9g \n" % self.slope)
        f.write("#EnergyCalib.quad  = %.9g \n" % self.quad)
        f.write("#Acquire.RealTime  = %.9g \n" % self.real_time)
        f.write("#Acquire.LiveTime  = %.9g \n" % self.live_time)
        roiform = "#ROI_%i '%s': [%i, %i]\n"
        for i, r in enumerate(self.rois):
            f.write(roiform % (i+1, r.name, r.left, r.right))

        f.write("#-----------------------------------------\n")
        f.write("#    energy       counts     log_counts\n")

        for e, d in zip(self.energy, self.counts):
            dlog = 0.
            if  d > 0: dlog = np.log10(max(d, 1))
            f.write(" %10.4f  %12i  %12.6g\n" % (e, d, dlog))
        f.write("\n")
        f.close()

    def save_mcafile(self, filename, environ=None):
        """write MultiChannel MCA file

        Parameters:
        -----------
        * filename: output file name
        """
        rois = self._xsp3.get_rois()
        nelem = len(self._xsp3.mcas)
        mcas = [self.get_mca(mca=i+1, with_rois=False) for i in range(nelem)]

        realtime = self._xsp3.AcquireTime * self._xsp3.ArrayCounter_RBV
        for m in mcas:
            m.real_time = realtime
            m.live_time = realtime

        save_gsemcafile(filename, mcas, rois, environ=environ)


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
        self.elapsed_textwidget = None
        self.needs_refresh = False
        self.frametime = 1.0
        self.nframes = 1
        if self.prefix is not None:
            self.connect()

    # @EpicsFunction
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
    def onRealTime(self, pvname, value=None, char_value=None, **kws):
        self.elapsed_real = value
        self.needs_refresh = True
        self.frametime = value
        if self.elapsed_textwidget is not None:
            self.elapsed_textwidget.SetLabel(" %8.2f" % value)

    def set_usesum(self, usesum=True):
        pass

    def get_deadtime(self, mca=1):
        """return deadtime info"""
        return self._xmap.get("DeadTime")

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
        thismca.real_time = emca.ERTM
        thismca.live_time = emca.ELTM
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

    def save_mcafile(self, filename, environ=None):
        """write MultiChannel MCA file

        Parameters:
        -----------
        * filename: output file name
        """
        nelem = len(self.mcas)
        rois = self._xmap.get_rois()
        mcas = [self.get_mca(mca=i+1, with_rois=False) for i in range(nelem)]


        save_gsemcafile(filename, mcas, rois, environ=environ)
