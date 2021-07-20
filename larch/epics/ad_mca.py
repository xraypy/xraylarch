import numpy as np
import time

from epics import PV, caget, caput, poll, Device, get_pv

MAX_CHAN = 4096
MAX_ROIS = 48
TOOMANY_ROIS = 'Too many ROIS, only %i ROIS allowed.' % (MAX_ROIS)

class ADMCAROI(Device):
    """
    MCA ROI using ROIStat plugin from areaDetector2,
    as used for Xspress3 detector.
    """

    _attrs =('Use', 'Name', 'MinX', 'SizeX',
             'BgdWidth', 'SizeX_RBV', 'MinX_RBV',
             'Total_RBV', 'Net_RBV')

    _aliases = {'left': 'MinX',
                'width': 'SizeX',
                'name': 'Name',
                'sum': 'Total_RBV',
                'net': 'Net_RBV'}

    _nonpvs = ('_prefix', '_pvs', '_delim', '_init',
               '_aliases', 'data_pv')

    _reprfmt = "<ADMCAROI '%s', name='%s', range=[%s:%s]>"
    def __init__(self, prefix, roi=1, bgr_width=3, data_pv=None, with_poll=False):
        self._prefix = '%s:%i' % (prefix, roi)
        Device.__init__(self, self._prefix, delim=':',
                        attrs=('Name', 'MinX'), with_poll=with_poll)
        self._aliases = {'left': 'MinX',
                         'width': 'SizeX',
                         'name': 'Name',
                         'sum': 'Total_RBV',
                         'net': 'Net_RBV'}

        self.data_pv = data_pv

    def __eq__(self, other):
        """used for comparisons"""
        return (self.MinX     == getattr(other, 'MinX', None) and
                self.SizeX    == getattr(other, 'SizeX', None) and
                self.BgdWidth == getattr(other, 'BgdWidth', None) )

    def __ne__(self, other): return not self.__eq__(other)
    def __lt__(self, other): return self.MinX <  getattr(other, 'MinX', None)
    def __le__(self, other): return self.MinX <= getattr(other, 'MinX', None)
    def __gt__(self, other): return self.MinX >  getattr(other, 'MinX', None)
    def __ge__(self, other): return self.MinX >= getattr(other, 'MinX', None)

    def __repr__(self):
        "string representation"
        pref = self._prefix
        if pref.endswith('.'):
            pref = pref[:-1]

        return self._reprfmt % (pref, self.Name, self.MinX,
                                self.MinX+self.SizeX)

    def get_right(self):
        return self.MinX + self.SizeX

    def set_right(self, val):
        """set the upper ROI limit (adjusting size, leaving left unchanged)"""
        self._pvs['SizeX'].put(val - self.MinX)

    right = property(get_right, set_right)

    def get_center(self):
        return int(round(self.MinX + self.SizeX/2.0))

    def set_center(self, val):
        """set the ROI center (adjusting left, leaving width unchanged)"""
        self._pvs['MinX'].put(int(round(val  - self.SizeX/2.0)))

    center = property(get_center, set_center)

    def clear(self):
        self.Name = ''
        self.MinX = 0
        self.SizeX = 0

    def get_counts(self, data=None, net=False):
        """
        calculate total and net counts for a spectra

        Parameters:
        -----------
         data   numpy array of spectra or None to read from PV
         net    bool to set net counts (default=False: total counts returned)
        """
        if data is None and self.data_pv is not None:
            data = self.data_pv.get()
        out = self.Total_RBV
        if net:
            out = self.Net_RBV
        if isinstance(data, np.ndarray):
            lo = self.MinX
            hi = self.MinX + self.SizeX
            out = data[lo:hi+1].sum()
            if net:
                wid = int(self.bgr_width)
                jlo = max((lo - wid), 0)
                jhi = min((hi + wid), len(data)-1) + 1
                bgr = np.concatenate((data[jlo:lo],
                                       data[hi+1:jhi])).mean()
                out = out - bgr*(hi-lo)
        return out

class ADMCA(Device):
    """
    MCA using ROIStat plugin from areaDetector2,
    as used for Xspress3 detector.
    """
    _attrs =('AcquireTime', 'Acquire', 'NumImages')
    _nonpvs = ('_prefix', '_pvs', '_delim', '_roi_prefix',
               '_npts', 'rois', '_nrois', 'rois', '_calib')
    _calib = (0.00, 0.01, 0.00)
    def __init__(self, prefix, data_pv=None, nrois=None, roi_prefix=None):

        self._prefix = prefix
        Device.__init__(self, self._prefix, delim='',
                              attrs=self._attrs, with_poll=False)
        if data_pv is not None:
            self._pvs['VAL'] = PV(data_pv, auto_monitor=False)
        self._npts = None
        self._nrois = nrois
        if self._nrois is None:
            self._nrois = MAX_ROIS

        self._roi_prefix = roi_prefix
        for i in range(self._nrois):
            p = get_pv('%s:%i:Name' % (self._roi_prefix, i+1))
            p = get_pv('%s:%i:MinX' % (self._roi_prefix, i+1))
            p = get_pv('%s:%i:SizeX' % (self._roi_prefix, i+1))
        self.get_rois()
        poll()

    def start(self):
        "Start AD MCA"
        self.Acquire = 1
        poll()
        return self.Acquire

    def stop(self):
        "Stop AD MCA"
        self.Acquire = 0
        return self.Acquire

    def get_calib(self):
        """get energy calibration tuple (offset, slope, quad)"""
        return self._calib

    def get_energy(self):
        """return energy for AD MCA"""
        if self._npts is None and self._pvs['VAL'] is not None:
            self._npts = len(self.get('VAL'))
        en = np.arange(self._npts, dtype='f8')
        cal = self._calib
        return cal[0] + en*(cal[1] + en*cal[2])

    def clear_rois(self, nrois=None):
        "clear all rois"
        if self.rois is None:
            self.get_rois()
        for roi in self.rois:
            roi.clear()
        self.rois = []

    def get_rois(self, nrois=None):
        "get all rois"
        self.rois = []
        data_pv = self._pvs['VAL']
        poll()
        data_pv.connect()
        prefix = self._roi_prefix
        if prefix is None:
            return self.rois

        if nrois is None:
            nrois = self._nrois
        for i in range(nrois):
            roi = ADMCAROI(prefix=self._roi_prefix, roi=i+1, data_pv=data_pv)
            if roi.Name is None:
                roi = ADMCAROI(prefix=self._roi_prefix, roi=i+1,
                               data_pv=data_pv, with_poll=True)
            if roi.Name is None:
                continue
            if len(roi.Name.strip()) > 0 and roi.MinX > 0 and roi.SizeX > 0:
                self.rois.append(roi)
            else:
                break
            poll(0.001, 1.0)
        return self.rois

    def del_roi(self, roiname):
        "delete an roi by name"
        if self.rois is None:
            self.get_rois()
        for roi in self.rois:
            if roi.Name.strip().lower() == roiname.strip().lower():
                roi.clear()
        poll(0.010, 1.0)
        self.sort_rois()

    def add_roi(self, roiname, lo, wid=None, hi=None, sort=True):
        """
        add an roi, given name, lo, and hi channels.
        """
        if lo is None or (hi is None and wid is None):
            return
        if self.rois is None:
            self.get_rois()

        try:
            iroi = len(self.rois) + 1
        except:
            iroi = 0

        if iroi > MAX_ROIS:
            raise ValueError(TOOMANY_ROIS)
        data_pv = self._pvs['VAL']
        prefix = self._roi_prefix

        roi = ADMCAROI(prefix=prefix, roi=iroi, data_pv=data_pv)
        roi.Name = roiname.strip()

        nmax = MAX_CHAN
        if self._npts is None and self._pvs['VAL'] is not None:
            nmax = self._npts = len(self.get('VAL'))

        roi.MinX = min(nmax-1, lo)
        if hi is not None:
            hi = min(nmax, hi)
            roi.SizeX = hi-lo
        elif wid is not None:
            roi.SizeX = min(nmax, wid+roi.MinX) - roi.MinX
        self.rois.append(roi)
        if sort:
            self.sort_rois()

    def sort_rois(self):
        """
        make sure rois are sorted, and Epics PVs are cleared
        """
        if self.rois is None:
            self.get_rois()

        poll(0.05, 1.0)
        unsorted = []
        empties  = 0
        for roi in self.rois:
            if len(roi.Name) > 0 and roi.right > 0:
                unsorted.append(roi)
            else:
                empties =+ 1
            if empties > 3:
                break

        self.rois = sorted(unsorted)
        rpref = self._roi_prefix
        roidat = [(r.Name, r.MinX, r.SizeX) for r in self.rois]

        for iroi, roi in enumerate(roidat):
            caput("%s:%i:Name"  % (rpref, iroi+1), roi[0])
            caput("%s:%i:MinX"  % (rpref, iroi+1), roi[1])
            caput("%s:%i:SizeX" % (rpref, iroi+1), roi[2])

        iroi = len(roidat)
        caput("%s:%i:Name" % (rpref, iroi+1), '')
        caput("%s:%i:MinX" % (rpref, iroi+1),  0)
        caput("%s:%i:SizeX" % (rpref, iroi+1), 0)
        self.get_rois()

    def set_rois(self, roidata):
        """
        set all rois from list/tuple of (Name, Lo, Hi),
        and ensures they are ordered and contiguous.
        """
        data_pv = self._pvs['VAL']

        iroi = 0
        self.clear_rois()
        for name, lo, hi in roidata:
            if len(name) > 0 and hi > lo and hi > 0:
                iroi +=1
                if iroi >= MAX_ROIS:
                    raise ValueError(TOOMANY_ROIS)
                self.add_roi(name, lo, hi=hi, sort=False)
        self.sort_rois()
