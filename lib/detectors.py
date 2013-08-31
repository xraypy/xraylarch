"""
Triggers, Counters, Detectors for Step Scan
"""

import time
from epics_interface import PV, caget, caput, poll
from epics.devices import Scaler, Mca, Struck
from ordereddict import OrderedDict

from .saveable import Saveable

class Trigger(Saveable):
    """Detector Trigger for a scan. The interface is:
    trig = ScanTrigger(pvname, value=1)
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
        Saveable.__init__(self, pvname, label=label, value=value, **kws)
        self.pv  = PV(pvname)
        self._val = value
        self.done = False
        self._t0 = 0
        self.runtime = -1

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

class Counter(Saveable):
    """simple scan counter object --
    a value that will be counted at each point in the scan"""
    def __init__(self, pvname, label=None, units=''):
        Saveable.__init__(self, pvname, label=label, units=units)
        self.pv  = PV(pvname)
        if label is None:
            label = pvname
        self.label = label
        self.units = units
        self.clear()

    def __repr__(self):
        return "<Counter %s (%s)>" % (self.label, self.pv.pvname)

    def read(self):
        val = self.pv.get(use_monitor=False)
        self.buff.append(val)
        return val

    def clear(self):
        self.buff = []

    def get_buffers(self):
        return {self.label: self.buff}

class DeviceCounter():
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

    def read(self):
        "read counters"
        for c in self.counters:
            c.read()
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
        for i in range(1, nchan+1):
            label = caget('%s.NM%i' % (prefix, i))
            if len(label) > 0 or use_unlabeled:
                suff = '.S%i' % i
                if use_calc:
                    suff = '_calc%i.VAL' % i
                    extra_pvs.append(('scaler calc%i' % i,
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
    def __init__(self, prefix, outpvs=None, nrois=32,
                 use_net=False,  use_unlabeled=False, use_full=False):
        DeviceCounter.__init__(self, prefix, rtype='mca', outpvs=outpvs)
        prefix = self.prefix
        fields = []
        for i in range(nrois):
            label = caget('%s.R%iNM' % (prefix, i))
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
    def __init__(self, prefix, outpvs=None, nmcas=4, nrois=32,
                 search_all = False,  use_net=False,
                 use_unlabeled=False, use_full=False):
        if not prefix.endswith(':'):
            prefix = "%s:" % prefix
        DeviceCounter.__init__(self, prefix, rtype=None, outpvs=outpvs)
        prefix = self.prefix
        fields = []
        extras = []
        for imca in range(1, nmcas+1):
            mca = 'mca%i' % imca
            dxp = 'dxp%i' % imca
            extras.extend([
                ("Calib_Offset (%s)" % mca, "%s%s.CALO" % (prefix, mca)),
                ("Calib_Slope (%s)" % mca, "%s%s.CALS" % (prefix, mca)),
                ("Calib_Quad (%s)" % mca, "%s%s.CALQ" % (prefix, mca)),
                ("Peaking_Time (%s)" % dxp, "%s%s:PeakingTime" % (prefix, dxp))
                ])

        pvs = {}
        t0 = time.time()
        for imca in range(1, nmcas+1):
            mca = 'mca%i' % imca
            for i in range(nrois):
                for suf in ('NM', 'HI'):
                    pvname = '%s%s.R%i%s' % (prefix, mca, i, suf)
                    pvs[pvname] = PV(pvname)

        poll()
        time.sleep(0.001)

        for i in range(nrois):
            should_break = False
            for imca in range(1, nmcas+1):
                mca = 'mca%i' % imca
                namepv = '%s%s.R%iNM' % (prefix, mca, i)
                rhipv  = '%s%s.R%iHI' % (prefix, mca, i)
                roi    = pvs[namepv].get()
                roi_hi = pvs[rhipv].get()
                label = '%s (%s)'% (roi, mca)
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

class DetectorMixin(Saveable):
    trigger_suffix = None
    def __init__(self, prefix, label=None, **kws):
        Saveable.__init__(self, prefix, label=label, **kws)
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

    def pre_scan(self, **kws):
        pass

    def post_scan(self, **kws):
        pass

    def at_break(self, breakpoint=None, **kws):
        pass

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
        self.scaler = Scaler(prefix, nchan=nchan)
        self._counter = ScalerCounter(prefix, nchan=nchan,
                                      use_calc=use_calc)
        self.dwelltime_pv = PV('%s.TP' % prefix)
        self.dwelltime    = None
        self.counters = self._counter.counters
        self.extra_pvs = [('scaler frequency', '%s.FREQ' % prefix),
                          ('scaler read_delay', '%s.DLY' % prefix)]
        self._repr_extra = ', nchannels=%i, use_calc=%s' % (nchan,
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
    _valid_file_plugins = ('TIFF1', 'JPEG1', 'NetCDF1',
                           'HDF1', 'Nexus1', 'Magick1')
    def __init__(self, prefix, file_plugin=None, **kws):
        if not prefix.endswith(':'):
            prefix = "%s:" % prefix
        DetectorMixin.__init__(self, prefix, **kws)
        self.dwelltime_pv = PV('%scam1:AcquireTime' % prefix)
        self.dwelltime    = None
        self.file_plugin  = None
        self.counters = [Counter("%scam1:ArrayCounter_RBV" % prefix,
                                 label='Image Counter')]
        if file_plugin in self._valid_file_plugins:
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
    def __init__(self, prefix, save_spectra=True, nrois=32, use_net=False,
                 use_full=False, **kws):

        DetectorMixin.__init__(self, prefix, **kws)
        self.mca = Mca(prefix)
        self.dwelltime_pv = PV('%s.PRTM' % prefix)
        self.dwelltime    = None
        self.trigger = Trigger("%sEraseStart" % prefix)
        self._counter = McaCounter(prefix, nrois=nrois, use_full=use_full,
                                   use_net=use_net)
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

    def __init__(self, prefix, label=None, nmcas=4, nrois=32,
                 search_all=False,  use_net=False, use=True,
                 use_unlabeled=False, use_full=False):
        DetectorMixin.__init__(self, prefix, label=label)

        if not prefix.endswith(':'):
            prefix = "%s:" % prefix
        self.prefix = prefix
        self.dwelltime_pv = PV('%sPresetReal' % prefix)
        self.dwelltime    = None
        self.trigger = Trigger("%sEraseStart" % prefix)
        self._counter = MultiMcaCounter(prefix, nmcas=nmcas, nrois=nrois,
                                        search_all=search_all,
                                        use_net=use_net,
                                        use_unlabeled=use_unlabeled,
                                        use_full=use_full)

        self.counters = self._counter.counters
        self.extra_pvs = self._counter.extra_pvs
        self._repr_extra = self.repr_fmt % (nmcas, nrois,
                                             repr(use_net), repr(use_full))

    def pre_scan(self, scan=None, **kws):
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
    print 'DETECTOR ', prefix, kind, builder
    try:
        return builder(prefix, label=label, **kws)
    except TypeError:
        return None
