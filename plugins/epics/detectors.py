"""
Triggers, Counters, Detectors for Step Scan
"""

import time
from numpy import ndarray

from epics import PV, get_pv, caget, caput, poll
from epics.devices import Scaler, MCA, Struck
from larch.utils.ordereddict import OrderedDict

DET_DEFAULT_OPTS = {'scaler': {'use_calc': True, 'nchans': 8},
                    'areadetector': {'file_plugin': 'TIFF1',
                                     'auto_increment': True},
                    'mca': {'nrois': 32, 'use_full': False,
                            'use_net': False},
                    'xspress3': {'nrois': 32, 'nmcas': 4, 
                                 'use_full': False},
                    'multimca': {'nrois': 32, 'nmcas': 4,
                                 'use_full': False, 'use_net': False}}

AD_FILE_PLUGINS = ('TIFF1', 'JPEG1', 'NetCDF1',
                   'HDF1', 'Nexus1', 'Magick1')


class Trigger(object):
    """Detector Trigger for a scan. The interface is:
    trig = Trigger(pvname, value=1)
           defines a trigger PV and trigger value

    trig.start(value=None)
          starts the trigger (value will override value set on creation)

    trig.done       True if the start has completed.
    trig.runtime    time for last .start() to complete

Example usage:
    trig = ScanTrigger(pvname)
    trig.start()
    while not trig.done:
        time.sleep(1.e-4)
    <read detector data>
    """
    def __init__(self, pvname, value=1, label=None, **kws):
        self.pv  = get_pv(pvname)
        self._val = value
        self.done = False
        self._t0 = 0
        self.runtime = -1
        self.stop = None

    def __repr__(self):
        return "<Trigger (%s)>" % (self.pv.pvname)

    def __onComplete(self, pvname=None, **kws):
        self.done = True
        self.runtime = time.time() - self._t0

    def start(self, value=1):
        """triggers detector"""
        self.done = False
        self.runtime = -1
        self._t0 = time.time()
        if value is None:
            value = self._val
        self.pv.put(value, callback=self.__onComplete)
        time.sleep(0.001)
        poll()

class Counter(object):
    """simple scan counter object --
    a value that will be counted at each point in the scan"""
    def __init__(self, pvname, label=None, units=''):
        self.pv  = get_pv(pvname)
        if label is None:
            label = pvname
        self.label = label
        self.units = units
        self.clear()

    def __repr__(self):
        return "<Counter %s (%s)>" % (self.label, self.pv.pvname)

    def read(self, nbins=None, full=False, **kws):
        val = self.pv.get(**kws)
        self.buff.append(val)
        return val

    def clear(self):
        self.buff = []

    def get_buffers(self):
        return {self.label: self.buff}

class DeviceCounter(object):
    """Generic Multi-PV Counter to be base class for
    ScalerCounter, MCACounter, etc
    """
    invalid_device_msg = 'DeviceCounter of incorrect Record Type'
    def __init__(self, prefix, rtype=None, fields=None, outpvs=None):
        if prefix.endswith('.VAL'):
            prefix = prefix[-4]
        self.prefix = prefix
        if rtype is not None:
            if caget("%s.RTYP" % self.prefix) != rtype:
                raise TypeError(self.invalid_device_msg)
        self.outpvs = outpvs
        self.set_counters(fields)

    def set_counters(self, fields):
        self.counters = []
        if hasattr(fields, '__iter__'):
            for suf, lab in fields:
                self.counters.append(Counter("%s%s" % (self.prefix, suf),
                                             label=lab))

    def postvalues(self):
        """post first N counter values to output PVs
        (N being the number of output PVs)

        May want ot override this method....
        """
        if self.outpvs is not None:
            for counter, pv in zip(self.counters, self.outpvs):
                pv.put(counter.buff)

    def read(self, **kws):
        "read counters"
        for c in self.counters:
            c.read(**kws)
        self.postvalues()

    def clear(self):
        "clear counters"
        for c in self.counters:
            c.clear()

    def get_buffers(self):
        o = OrderedDict()
        for c in self.counters:
            o[c.label] = c.buff
        return o

class MotorCounter(Counter):
    """Motor Counter: save Readback value
    """
    invalid_device_msg = 'MotorCounter must use an Epics Motor'
    def __init__(self, prefix, label=None):
        pvname = '%s.RBV' % prefix
        if label is None:
            label = "%s(actual)" % caget('%s.DESC' % prefix)
        Counter.__init__(self, pvname, label=label) # , rtype='motor')

class ScalerCounter(DeviceCounter):
    invalid_device_msg = 'ScalerCounter must use an Epics Scaler'
    def __init__(self, prefix, outpvs=None, nchan=8,
                 use_calc=False,  use_unlabeled=False):
        DeviceCounter.__init__(self, prefix, rtype='scaler',
                               outpvs=outpvs)
        prefix = self.prefix
        fields = [('.T', 'CountTime')]
        extra_pvs = []
        nchan = int(nchan)
        for i in range(1, nchan+1):
            label = caget('%s.NM%i' % (prefix, i))
            if len(label) > 0 or use_unlabeled:
                suff = '.S%i' % i
                if use_calc:
                    suff = '_calc%i.VAL' % i
                    extra_pvs.append(('Scaler.Calc%i' % i,
                                      '%s_calc%i.CALC' % (prefix, i)))
                fields.append((suff, label))
        self.extra_pvs = extra_pvs
        self.set_counters(fields)

class DXPCounter(DeviceCounter):
    """DXP Counter: saves all input and output count rates"""
    _fields = (('InputCountRate', 'ICR'),
               ('OutputCountRate', 'OCR'))
    def __init__(self, prefix, outpvs=None):
        DeviceCounter.__init__(self, prefix, rtype=None, outpvs=outpvs)
        prefix = self.prefix
        self.set_counters(self._fields)

class McaCounter(DeviceCounter):
    """Simple MCA Counter: saves all ROIs (total or net) and, optionally full spectra
    """
    invalid_device_msg = 'McaCounter must use an Epics MCA'
    def __init__(self, prefix, outpvs=None, nrois=32, rois=None,
                 use_net=False,  use_unlabeled=False, use_full=False):
        nrois = int(nrois)
        DeviceCounter.__init__(self, prefix, rtype='mca', outpvs=outpvs)

        # use roilist to limit ROI to those listed:
        roilist = None
        if rois is not None and len(rois)>0:
            roilist = [s.lower().strip() for s in rois]

        prefix = self.prefix
        fields = []
        for i in range(nrois):
            label = caget('%s.R%iNM' % (prefix, i))
            if roilist is not None and label.lower().strip() not in roilist:
                continue

            if len(label) > 0 or use_unlabeled:
                suff = '.R%i' % i
                if use_net:
                    suff = '.R%iN' % i
                fields.append((suff, label))
        if use_full:
            fields.append(('.VAL', 'mca spectra'))
        self.set_counters(fields)

class MultiMcaCounter(DeviceCounter):
    invalid_device_msg = 'McaCounter must use an Epics Multi-Element MCA'
    _dxp_fields = (('InputCountRate', 'ICR'),
                   ('OutputCountRate', 'OCR'))
    def __init__(self, prefix, outpvs=None, nmcas=4, nrois=32, rois=None,
                 search_all = False,  use_net=False,
                 use_unlabeled=False, use_full=False):
        if not prefix.endswith(':'):
            prefix = "%s:" % prefix
        nmcas, nrois = int(nmcas), int(nrois)
        DeviceCounter.__init__(self, prefix, rtype=None, outpvs=outpvs)

        # use roilist to limit ROI to those listed:
        roilist = []
        if rois is not None and len(rois)>0:
            roilist = [s.lower().strip() for s in rois]

        prefix = self.prefix
        fields = []
        extras = []
        for imca in range(1, nmcas+1):
            mca = 'mca%i' % imca
            dxp = 'dxp%i' % imca
            extras.extend([
                ("%s.Calib_Offset" % mca, "%s%s.CALO" % (prefix, mca)),
                ("%s.Calib_Slope"  % mca, "%s%s.CALS" % (prefix, mca)),
                ("%s.Calib_Quad"   % mca, "%s%s.CALQ" % (prefix, mca)),
                ("%s.Peaking_Time" % dxp, "%s%s:PeakingTime" % (prefix, dxp))
                ])

        pvs = {}
        t0 = time.time()
        for imca in range(1, nmcas+1):
            mca = 'mca%i' % imca
            for i in range(nrois):
                for suf in ('NM', 'HI'):
                    pvname = '%s%s.R%i%s' % (prefix, mca, i, suf)
                    pvs[pvname] = get_pv(pvname)

        poll()
        time.sleep(0.001)

        for i in range(nrois):
            should_break = False
            for imca in range(1, nmcas+1):
                mca = 'mca%i' % imca
                namepv = '%s%s.R%iNM' % (prefix, mca, i)
                rhipv  = '%s%s.R%iHI' % (prefix, mca, i)
                roi    = pvs[namepv].get()
                if roi.lower().strip() not in roilist:
                    continue
                roi_hi = pvs[rhipv].get()
                label = '%s %s'% (roi, mca)
                if (roi is not None and (len(roi) > 0 and roi_hi > 0) or
                    use_unlabeled):
                    suff = '%s.R%i' % (mca, i)
                    if use_net:
                        suff = '%s.R%iN' %  (mca, i)
                    fields.append((suff, label))
                if roi_hi < 1 and not search_all:
                    should_break = True
                    break
            if should_break:
                break

        for dsuff, dname in self._dxp_fields:
            for imca in range(1, nmcas +1):
                suff = 'dxp%i:%s' %  (imca, dsuff)
                label = '%s%i' % (dname, imca)
                fields.append((suff, label))

        if use_full:
            for imca in range(1, nmcas+1):
                mca = 'mca%i.VAL' % imca
                fields.append((mca, 'spectra%i' % imca))
        self.extra_pvs = extras
        self.set_counters(fields)

class DetectorMixin(object):
    trigger_suffix = None
    def __init__(self, prefix, label=None, **kws):
        self.prefix = prefix
        self.label = label
        if self.label is None:
            self.label = self.prefix
        self.trigger = None
        if self.trigger_suffix is not None:
            self.trigger = Trigger("%s%s" % (prefix, self.trigger_suffix))
        self.counters = []
        self.dwelltime_pv = None
        self.dwelltime = None
        self.extra_pvs = []
        self._repr_extra = ''

    def __repr__(self):
        return "<%s: '%s', prefix='%s'%s>" % (self.__class__.__name__,
                                              self.label, self.prefix,
                                              self._repr_extra)

    def connect_counters(self):
        pass

    def pre_scan(self, **kws):
        pass

    def post_scan(self, **kws):
        pass

    def at_break(self, breakpoint=None, **kws):
        pass

    def set_dwelltime(self, val):
        "set detector dwelltime"
        self.dwelltime = val
        if self.dwelltime_pv is not None:
            self.dwelltime_pv.put(val)

class SimpleDetector(DetectorMixin):
    "Simple Detector: a single Counter without a trigger"
    trigger_suffix = None
    def __init__(self, prefix, **kws):
        DetectorMixin.__init__(self, prefix, **kws)
        self.counters = [Counter(prefix)]

class MotorDetector(DetectorMixin):
    "Motor Detector: a Counter for  Motor Readback, no trigger"
    trigger_suffix = None
    def __init__(self, prefix, **kws):
        DetectorMixin.__init__(self, prefix, **kws)
        self.counters = [MotorCounter(prefix)]

class ScalerDetector(DetectorMixin):
    trigger_suffix = '.CNT'
    def __init__(self, prefix, nchan=8, use_calc=True, **kws):
        DetectorMixin.__init__(self, prefix, **kws)
        nchan = int(nchan)
        self.scaler = Scaler(prefix, nchan=nchan)
        self._counter = ScalerCounter(prefix, nchan=nchan,
                                      use_calc=use_calc)
        self.dwelltime_pv = get_pv('%s.TP' % prefix)
        self.dwelltime    = None
        self.counters = self._counter.counters
        self.extra_pvs = [('Scaler.frequency', '%s.FREQ' % prefix),
                          ('Scaler.read_delay', '%s.DLY' % prefix)]
        self._repr_extra = ', nchans=%i, use_calc=%s' % (nchan,
                                                         repr(use_calc))

        self.extra_pvs.extend(self._counter.extra_pvs)

    def pre_scan(self, scan=None, **kws):
        self.scaler.OneShotMode()
        if (self.dwelltime is not None and
            isinstance(self.dwelltime_pv, PV)):
            self.dwelltime_pv.put(self.dwelltime)

    def post_scan(self, **kws):
        self.scaler.AutoCountMode()

class AreaDetector(DetectorMixin):
    """very simple area detector interface...
    trigger / dwelltime, uses array counter as only counter
    """
    trigger_suffix = 'Acquire'
    def __init__(self, prefix, file_plugin=None, **kws):
        if not prefix.endswith(':'):
            prefix = "%s:" % prefix
        DetectorMixin.__init__(self, prefix, **kws)
        self.dwelltime_pv = get_pv('%scam1:AcquireTime' % prefix)
        self.dwelltime    = None
        self.file_plugin  = None
        self.counters = [Counter("%scam1:ArrayCounter_RBV" % prefix,
                                 label='Image Counter')]
        if file_plugin in AD_FILE_PLUGINS:
            self.file_plugin = file_plugin
            f_counter = Counter("%s%s:FileNumebr_RBV" % (prefix, file_plugin),
                                label='File Counter')
            self.counters.append(f_counter)
        self._repr_extra = ', file_plugin=%s' % repr(file_plugin)

    def pre_scan(self, scan=None, **kws):
        if (self.dwelltime is not None and
            isinstance(self.dwelltime_pv, PV)):
            self.dwelltime_pv.put(self.dwelltime)
        caput("%scam1:ImageMode" % (self.prefix), 0)      # single image capture
        caput("%scam1:ArrayCallbacks" % (self.prefix), 1) # enable callbacks
        if self.file_plugin is not None:
            fpre = "%s%s" % (sself.prefix, self.file_plugin)
            pref = scan.filename.replace('.', '_')
            ext = self.file_plugin[:-1]
            caput("%s:FileName" % fpre, pref)
            caput("%s:FileTemplate" % fpre, '%%s%%s_%%4.4d.%s' % ext)
            caput("%s:EnableCallbacks" % fpre, 1)
            caput("%s:AutoIncrement" % fpre, 1)
            caput("%s:AutoSave" % fpre, 1)

    def post_scan(self, **kws):
        if self.file_plugin is not None:
            fpre = "%s%s" % (sself.prefix, self.file_plugin)
            caput("%s:EnableCallbacks" % fpre, 0)
            caput("%s:AutoSave" % fpre, 0)


class McaDetector(DetectorMixin):
    trigger_suffix = 'EraseStart'
    repr_fmt = ', nrois=%i, use_net=%s, use_full=%s'
    def __init__(self, prefix, save_spectra=True, nrois=32, rois=None,
                 use_net=False,use_full=False, **kws):
        nrois = int(nrois)
        DetectorMixin.__init__(self, prefix, **kws)
        self.mca = MCA(prefix)
        self.dwelltime_pv = get_pv('%s.PRTM' % prefix)
        self.dwelltime    = None
        self.trigger = Trigger("%sEraseStart" % prefix)
        self._counter = McaCounter(prefix, nrois=nrois, rois=rois,
                                   use_full=use_full, use_net=use_net)
        self.counters = self._counter.counters
        self._repr_extra = self.repr_fmt % (nrois, repr(use_net), repr(use_full))

    def pre_scan(self, scan=None, **kws):
        if (self.dwelltime is not None and
            isinstance(self.dwelltime_pv, PV)):
            self.dwelltime_pv.put(self.dwelltime)

class MultiMcaDetector(DetectorMixin):
    trigger_suffix = 'EraseStart'
    collect_mode = 'CollectMode'
    repr_fmt = ', nmcas=%i, nrois=%i, use_net=%s, use_full=%s'

    def __init__(self, prefix, label=None, nmcas=4, nrois=32, rois=None,
                 search_all=False,  use_net=False, use=True,
                 use_unlabeled=False, use_full=False, **kws):
        DetectorMixin.__init__(self, prefix, label=label)
        nmcas, nrois = int(nmcas), int(nrois)
        if not prefix.endswith(':'):
            prefix = "%s:" % prefix
        self.prefix        = prefix
        self.dwelltime_pv  = get_pv('%sPresetReal' % prefix)
        self.trigger       = Trigger("%sEraseStart" % prefix)
        self.dwelltime     = None
        self.extra_pvs     = None
        self._counter      = None
        self._connect_args = dict(nmcas=nmcas, nrois=nrois, rois=rois,
                                  search_all=search_all, use_net=use_net,
                                  use_unlabeled=use_unlabeled,
                                  use_full=use_full)
        self._repr_extra = self.repr_fmt % (nmcas, nrois,
                                            repr(use_net), repr(use_full))

    def connect_counters(self):
        self._counter = MultiMcaCounter(self.prefix, **self._connect_args)
        self.counters = self._counter.counters
        self.extra_pvs = self._counter.extra_pvs


    def pre_scan(self, scan=None, **kws):
        if self._counter is None:
            self.connect_counters()
        if (self.dwelltime is not None and
            isinstance(self.dwelltime_pv, PV)):
            self.dwelltime_pv.put(self.dwelltime)
        caput("%sCollectMode" % (self.prefix), 0)   # mca spectra
        caput("%sPresetMode"  % (self.prefix), 1)   # real time
        caput("%sReadBaselineHistograms.SCAN" % (self.prefix), 0)
        caput("%sReadTraces.SCAN" % (self.prefix), 0)
        caput("%sReadLLParams.SCAN" % (self.prefix), 0)
        caput("%sReadAll.SCAN"   % (self.prefix), 9)
        caput("%sStatusAll.SCAN" % (self.prefix), 9)



class Xspress3Trigger(Trigger):
    """Triggers for Xspress3:  has separate ERASE and Acquire
    which correspond to EraseStart.
    """
    def __init__(self, prefix, value=1, label=None, **kws):
        Trigger.__init__(self, prefix, label=label, value=value, **kws)
        self._start = get_pv(prefix + 'Acquire')
        self._erase = get_pv(prefix + 'ERASE')
        self.prefix = prefix
        self._val = value
        self.done = False
        self._t0 = 0
        self.runtime = -1

    def __repr__(self):
        return "<Xspress3Trigger(%s)>" % (self.prefix)

    def __onComplete(self, pvname=None, **kws):
        self.done = True
        self.runtime = time.time() - self._t0

    def start(self, value=None):
        """ERASE and start Xspress3"""
        self.done = False
        runtime = -1
        self._t0 = time.time()
        if value is None:
            value = self._val
        self._erase.put(1, wait=True)
        time.sleep(0.005)
        self._start.put(value, callback=self.__onComplete)
        time.sleep(0.005)


class Xspress3Detector(DetectorMixin):
    """
    Xspress 3 MultiMCA detector, 3.1.10
    """
    repr_fmt = ', nmcas=%i, nrois=%i, use_dtc=%s, use_full=%s'

    def __init__(self, prefix, label=None, nmcas=4,
                 nrois=32, rois=None, pixeltime=0.1, use_dtc=False,
                 use=True, use_unlabeled=False, use_full=False, **kws):

        if not prefix.endswith(':'):
            prefix = "%s:" % prefix

        self.nmcas = nmcas = int(nmcas)
        self.nrois = nrois = int(nrois)

        self.prefix     = prefix
        self.dwelltime  = None
        self.dwelltime_pv = get_pv('%sAcquireTime' % prefix)
        self.trigger    = Xspress3Trigger(prefix)
        self.extra_pvs  = None
        self.use_dtc    = use_dtc
        self.label      = label
        if self.label is None:
            self.label = self.prefix

        self._counter = None
        self.counters = []
        self._repr_extra = self.repr_fmt % (nmcas, nrois,
                                            repr(use_dtc),
                                            repr(use_full))

        self._connect_args = dict(nmcas=nmcas, nrois=nrois, rois=rois,
                                  use_unlabeled=use_unlabeled,
                                  use_full=use_full)

    def __repr__(self):
        return "<%s: '%s', prefix='%s'%s>" % (self.__class__.__name__,
                                              self.label, self.prefix,
                                              self._repr_extra)

    def connect_counters(self):
        self._counter = Xspress3Counter(self.prefix, **self._connect_args)
        self.counters = self._counter.counters
        self.extra_pvs = self._counter.extra_pvs

    def pre_scan(self, scan=None, **kws):
        if self._counter is None:
            self.connect_counters()
        if (self.dwelltime is not None and
            isinstance(self.dwelltime_pv, PV)):
            self.dwelltime_pv.put(self.dwelltime)

        caput("%sERASE"   % (self.prefix), 1)
        caput("%sAcquire"   % (self.prefix), 0)
        for i in range(1, self.nmcas+1):
            card = "%sC%i" % (self.prefix, i)
            caput("%s_PluginControlValExtraROI" % (card), 0)
            caput("%s_PluginControlVal"         % (card), 1)

        caput("%sTriggerMode" % (self.prefix), 1)   # Internal Mode
        caput("%sNumImages"   % (self.prefix), 1)   # 1 Image

        caput("%sCTRL_MCA_ROI"  % (self.prefix), 1)
        caput("%sCTRL_DTC"      % (self.prefix), self.use_dtc)
        time.sleep(0.01)
        caput("%sUPDATE"        % (self.prefix), 1)
        time.sleep(0.01)


class Xspress3Counter(DeviceCounter):
    """Counters for Xspress3-1-10 (weird ROIs / areaDetector hybrid)
    """
    sca_labels = ('Clock', 'ResetTicks', 'ResetCounts',
                  'AllEvent', 'AllGood', 'Window1', 'Window2', 'Pileup')

    def __init__(self, prefix, outpvs=None, nmcas=4,
                 nrois=32, rois=None, nscas=1, use_unlabeled=False,
                 use_full=False):

        if not prefix.endswith(':'):
            prefix = "%s:" % prefix

        self.nmcas, self.nrois = int(nmcas), int(nrois)
        self.nscas =  int(nscas)
        self.use_full = use_full
        self.use_unlabeled = False
        DeviceCounter.__init__(self, prefix, rtype=None, outpvs=outpvs)

        prefix = self.prefix
        self._fields = []
        self.extra_pvs = []
        pvs = self._pvs = {}

        time.sleep(0.01)
        # use roilist to limit ROI to those listed:
        self.roilist = []
        if rois is not None and len(rois)>0:
            self.roilist = [s.lower().strip() for s in rois]
        self._get_counters()

    def _get_counters(self):
        prefix = self.prefix
        self.counters = []
        def add_counter(pv, lab):
            self.counters.append(Counter(pv, label=lab))

        try:
            nmax = len(caget('%sARR1:ArrayData' % prefix))
        except ValueError:
            nmax = 2048

        roidata = OrderedDict()
        for roiname in self.roilist:
            roidata[roiname.lower().strip()] = (False, roiname, -1, -1)
        if len(roidata) < 4:
            roidata['ocr'] = (True, 'OutputCounts', 25, nmax-25)
        for iroi in range(1, self.nrois+1):
            label = caget("%smca1.R%iNM" % (prefix, iroi))
            slab = label.lower().strip()
            if slab in roidata and not roidata[slab][0]:
                lo = caget("%smca1.R%iLO" % (prefix, iroi))
                hi = caget("%smca1.R%iHI" % (prefix, iroi))
                roidata[slab] = (True, label, lo, hi)
                if all([rdat[0] for rdat in roidata.values()]):
                    break

        iroi = 0
        for sname, dat in roidata.items():
            found, label, lo, hi = dat
            if found:
                iroi += 1
                for imca in range(1, 1+self.nmcas):
                    pref = "%sC%i" % (prefix, imca)
                    caput('%s_MCA_ROI%i_LLM' % (pref, iroi), lo)
                    caput('%s_MCA_ROI%i_HLM' % (pref, iroi), hi)
                    caput('%s_ROI%i:ValueSum_RBV.DESC' % (pref, iroi), label)
                    xlab = "%s mca%i" % (label, imca)
                    add_counter('%s_ROI%i:Value_RBV' % (pref, iroi), xlab)

        for isca in range(self.nscas):  # these start counting at 0!!
            for imca in range(1, self.nmcas+1):
                pv    = '%sC%i_SCA%i:Value_RBV' % (prefix, imca, isca)
                label = '%s mca%i' % (self.sca_labels[isca], imca)
                add_counter(pv, label)

        if self.use_full:
            for imca in range(1, self.nmcas+1):
                pv = '%sARR%i.ArrayData' % (prefix, imca)
                add_counter(pv, 'spectra%i' % imca)


class ArrayCounter(Counter):
    """Xspress3 Array Counters -- read converts array to scaler,
    trimming lo and hi pixels
    """

    def __init__(self, pvname, label=None, lo=1, hi=-1):
        Counter.__init__(self, pvname, label=label)
        self.clear()
        self.pv.get()
        self._lab = label
        self.lo = int(lo)
        self.hi = int(hi)

    def __repr__(self):
        return "<ArrayCounter %s (%s)>" % (self.label, self.pv.pvname)

    def read(self, nbins=None, full=False, **kws):
        if nbins is not None:
            kws['count'] = nbins+1
        val = self.pv.get(**kws)
        if not full and isinstance(val, ndarray):
            val = val[1:nbins].sum()
        self.buff.append(val)
        return val

def get_detector(prefix, kind=None, label=None, **kws):
    """returns best guess of which Detector class to use
           Mca, MultiMca, Motor, Scaler, Simple
    based on kind and/or record type.
    """
    dtypes = {'scaler': ScalerDetector,
              'motor': MotorDetector,
              'area': AreaDetector,
              'mca': McaDetector,
              'med': MultiMcaDetector,
              'multimca': MultiMcaDetector,
              'xspress3': Xspress3Detector,
              None: SimpleDetector}

    if kind is None:
        if prefix.endswith('.VAL'):
            prefix = prefix[-4]
        rtyp = caget("%s.RTYP" % prefix)
        if rtyp in ('motor', 'mca', 'scaler'):
            kind = rtyp
    else:
        kind = kind.lower()
    builder = dtypes.get(kind, SimpleDetector)
    return builder(prefix, label=label, **kws)
