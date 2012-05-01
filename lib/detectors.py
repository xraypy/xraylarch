"""
Triggers, Counters, Detectors for Step Scan
"""

import time
from epics import PV, caget, caput
from epics.devices import Scaler, Mca, Struck
from ordereddict import OrderedDict


class Trigger(object):
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

class Counter(object):
    """simple scan counter object --
    a value that will be counted at each point in the scan"""
    def __init__(self, pvname, label=None):
        self.pv  = PV(pvname)
        if label is None:
            label = pvname
        self.label = label
        self.clear()

    def __repr__(self):
        return "<Counter %s (%s)>" % (self.label, self.pv.pvname)

    def read(self):
        self.buff.append(self.pv.get())

    def clear(self):
        self.buff = []

    def get_buffers(self):
        return {self.label: self.buff}

class DeviceCounter():
    """Generic Multi-PV Counter to be base class for
    ScalerCounter, MCACounter, etc
    """
    invalid_device_msg = 'DeviceCounter of incorrect type'
    def __init__(self, prefix, rtype=None, fields=None, outpvs=None):
        if prefix.endswith('.VAL'):
            prefix = prefix[-4]
        self.prefix = prefix
        if rtype is not None:
            if not caget("%s.RTYP" % self.prefix) == rtype:
                raise TypeError(invalid_device_msg)
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
    invalid_device_msg = 'MotorCounter must use a motor'
    def __init__(self, prefix, label=None):
        pvname = '%s.RBV' % prefix
        if label is None:
            label = "%s(actual)" % caget('%s.DESC' % prefix)
        Counter.__init__(self, pvname, label=label)

class ScalerCounter(DeviceCounter):
    invalid_device_msg = 'ScalerCounter must use a scaler'
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
    invalid_device_msg = 'McaCounter must use a mca'
    def __init__(self, prefix, outpvs=None, nrois=32,
                 use_net=False,  use_unlabeled=False, use_full=True):
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
    invalid_device_msg = 'McaCounter must use a med'
    _dxp_fields = (('InputCountRate', 'ICR'),
                   ('OutputCountRate', 'OCR'))
    def __init__(self, prefix, outpvs=None, nmcas=4, nrois=32,
                 search_all = False,  use_net=False,
                 use_unlabeled=False, use_full=True):
        if not prefix.endswith(':'):
            prefix = "%s:" % prefix
        DeviceCounter.__init__(self, prefix, rtype=None, outpvs=outpvs)
        prefix = self.prefix
        fields = []
        extras = []
        for imca in range(1, nmcas+1):
            mcaname = 'mca%i' % imca
            dxpname = 'dxp%i' % imca
            extras.extend([("Calib  Offset (%s)" % (mcaname),
                            "%s%s.CALO" % (prefix, mcaname)),
                           ("Calib  Slope (%s)" % (mcaname),
                            "%s%s.CALS" % (prefix, mcaname)),
                           ("Calib  Quad (%s)" % (mcaname),
                            "%s%s.CALQ" % (prefix, mcaname)),
                           ("Peaking Time (%s)" % (dxpname),
                            "%s%s:PeakingTime" % (prefix, dxpname))])

        for i in range(nrois):
            for imca in range(1, nmcas+1):
                mcaname = 'mca%i' % imca
                dxpname = 'dxp%i' % imca
                roiname = caget('%s%s.R%iNM' % (prefix, mcaname, i)).strip()
                roi_hi  = caget('%s%s.R%iHI' % (prefix, mcaname, i))
                label = '%s (%s)'% (roiname, mcaname)
                if (len(roiname) > 0 and roi_hi > 0) or use_unlabeled:
                    suff = '%s.R%i' % (mcaname, i)
                    if use_net:
                        suff = '%s.R%iN' %  (mcaname, i)
                    fields.append((suff, label))
                if roi_hi < 1 and not search_all:
                    break

        for dsuff, dname in self._dxp_fields:
            for imca in range(1, nmcas +1):
                suff = '%s:%s' %  (dxpname, dsuff)
                label = '%s (%s)'% (dname, dxpname)
                fields.append((suff, label)) # ... add dxp

        if use_full:
            for imca in range(1, nmcas+1):
                fields.append(('%s.VAL' % mcaname, 'mca spectra (%s)' % mcaname))
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
        self.extra_pvs.extend(self._counter.extra_pvs)

    def pre_scan(self, **kws):
        self.scaler.OneShotMode()
        if (self.dwelltime is not None and
            isinstance(self.dwelltime_pv, PV)):
            self.dwelltime_pv.put(self.dwelltime)

    def post_scan(self, **kws):
        self.scaler.AutoCountMode()

class McaDetector(DetectorMixin):
    trigger_suffix = 'EraseStart'
    def __init__(self, prefix, save_spectra=True, **kws):
        DetectorMixin.__init__(self, prefix, **kws)
        self.mca = Mca(prefix)
        self.dwelltime_pv = PV('%s.PRTM' % prefix)
        self.dwelltime    = None
        self.trigger = Trigger("%sEraseStart" % prefix)
        self._counter = McaCounter(prefix, nchan=nchan, use_calc=use_calc)
        self.counters = self._counter.counters


    def pre_scan(self, **kws):
        if (self.dwelltime is not None and
            isinstance(self.dwelltime_pv, PV)):
            self.dwelltime_pv.put(self.dwelltime)
#
#
# class MultiMCACounter(DeviceCounter):
#     invalid_device_msg = 'MCACounter must use a med'
#     _dxp_fields = (('.InputCountRate', 'ICR'),
#                    ('.OutputCountRate', 'OCR'))
#     def __init__(self, prefix, outpvs=None, nmcas=4, nrois=32,
#                  search_all = False,  use_net=False,
#                  use_unlabeled=False, use_full=True):
#         DeviceCounter.__init__(self, prefix, rtype=None, outpvs=outpvs)
#         prefix = self.prefix
#         fields = []
#         for imca in range(1, nmcas+1):
#             mcaname = 'mca%i' % imca
#             dxpname = 'dxp%i' % imca
#             for i in range(nrois):
#                 roiname = caget('%s:%s.R%iNM' % (prefix, mcaname, i)).strip()
#                 roi_hi  = caget('%s:%s.R%iHI' % (prefix, mcaname, i))
#                 label = '%s (%s)'% (roiname, mcaname)
#                 if (len(roiname) > 0 and roi_hi > 0) or use_unlabeled:
#                     suff = ':%s.R%i' % (mcaname, i)
#                     if use_net:
#                         suff = ':%s.R%iN' %  (mcaname, i)
#                     fields.append((suff, label))
#                 if roi_hi < 1 and not search_all:
#                     break
#             # for dsuff, dname in self._dxp_fields:
#             #     fields.append()... add dxp
#             if use_full:
#                 fields.append((':%s.VAL' % mcaname, 'mca spectra (%s)' % mcaname))
#         self.set_counters(fields)
#
# ;
class MultiMcaDetector(DetectorMixin):
    trigger_suffix = 'EraseStart'
    collect_mode = 'CollectMode'

    def __init__(self, prefix, label=None, nmcas=4, nrois=32,
                 search_all=False,  use_net=False,
                 use_unlabeled=False, use_full=True):
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

    def pre_scan(self, **kws):
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

def genericDetector(name, kind=None, label=None, **kws):
    """returns best guess of which Detector class to use
           Mca, MultiMca, Motor, Scaler, Simple
    based on kind and/or record type.
    """
    if kind is None:
        prefix = name
        if prefix.endswith('.VAL'):
            prefix = prefix[-4]
        rtyp == caget("%s.RTYP", prefix)
        if rtyp in ('motor', 'mca', 'scaler'):
            kind = rtyp
    builder = SimpleDetector
    kind = kind.lower()
    if kind == 'scaler':
        builder = ScalerDetector
    elif kind == 'motor':
        builder = MotorDetector
    elif kind == 'mca':
        builder = MCADetector
    elif kind in ('med', 'multimca'):
        builder = MultiMcaDetector
    return builder(name, label=None, **kws)
