"""
Triggers, Counters, Detectors for Step Scan
"""

import time
from epics import PV, caget
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
    _fields = (('.InputCountRate', 'ICR'),
               ('.OutputCountRate', 'OCR'))
    def __init__(self, prefix, outpvs=None):
        DeviceCounter.__init__(self, prefix, rtype=None, outpvs=outpvs)
        prefix = self.prefix
        self.set_counters(self._fields)

class MCACounter(DeviceCounter):
    """Simple MCA Counter: saves all ROIs (total or net) and, optionally full spectra
    """
    invalid_device_msg = 'MCACounter must use a mca'
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

class MultiMCACounter(DeviceCounter):
    invalid_device_msg = 'MCACounter must use a med'
    _dxp_fields = (('.InputCountRate', 'ICR'),
                   ('.OutputCountRate', 'OCR'))
    def __init__(self, prefix, outpvs=None, nmcas=4, nrois=32,
                 search_all = False,  use_net=False,
                 use_unlabeled=False, use_full=True):
        DeviceCounter.__init__(self, prefix, rtype=None, outpvs=outpvs)
        prefix = self.prefix
        fields = []
        for imca in range(1, nmcas+1):
            mcaname = 'mca%i' % imca
            dxpname = 'dxp%i' % imca
            for i in range(nrois):
                roiname = caget('%s:%s.R%iNM' % (prefix, mcaname, i)).strip()
                roi_hi  = caget('%s:%s.R%iHI' % (prefix, mcaname, i))
                label = '%s (%s)'% (roiname, mcaname)
                if (len(roiname) > 0 and roi_hi > 0) or use_unlabeled:
                    suff = ':%s.R%i' % (mcaname, i)
                    if use_net:
                        suff = ':%s.R%iN' %  (mcaname, i)
                    fields.append((suff, label))
                if roi_hi < 1 and not search_all:
                    break
            # for dsuff, dname in self._dxp_fields:
            #     fields.append()... add dxp
            if use_full:
                fields.append((':%s.VAL' % mcaname, 'mca spectra (%s)' % mcaname))
        self.set_counters(fields)

class DetectorMixin(object):
    trigger_suffix = None
    def __init__(self, prefix, **kws):
        self.prefix = prefix
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
    def __init__(self, prefix):
        DetectorMixin.__init__(self, prefix)
        self.counters = [Counter(prefix)]


class MotorDetector(DetectorMixin):
    "Motor Detector: a Counter for  Motor Readback, no trigger"
    trigger_suffix = None
    def __init__(self, prefix):
        DetectorMixin.__init__(self, prefix)
        self.counters = [MotorCounter(prefix)]


class ScalerDetector(DetectorMixin):
    trigger_suffix = '.CNT'

    def __init__(self, prefix, nchan=8, use_calc=True):
        DetectorMixin.__init__(self, prefix)
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
    def __init__(self, prefix, save_spectra=True):
        DetectorMixin.__init__(self, prefix)
        self.mca = Mca(prefix)
        self.dwelltime_pv = PV('%s.PRTM' % prefix)
        self.dwelltime    = None
        self.trigger = Trigger("%sEraseStart" % prefix)
        self.counters = ScalerCounter(prefix, nchan=nchan, use_calc=use_calc)

    def pre_scan(self, **kws):
        if (self.dwelltime is not None and
            isinstance(self.dwelltime_pv, PV)):
            self.dwelltime_pv.put(self.dwelltime)


