#!/usr/bin/python

import os
import copy
import numpy as np
from scipy.interpolate import UnivariateSpline

from larch import use_plugin_path, Group, param_value, Parameter
use_plugin_path('xrf')

from mca import MCA
from roi import ROI
from xrf_bgr import XRFBackground

def str2floats(s):
    return [float(i) for i in s.split()]

def str2ints(s):
    return [int(i) for i in str2floats(s)]

def str2str(s, delim=None):
    s = s.strip()
    return [i.strip() for i in s.split(delim) if len(i) > 0]

class GSEMCA_File(Group):
    """
    Read GSECARS style MCA / Multi-element MCA files
    """
    def __init__(self, filename=None, bad=None, nchans=2048, **kws):

        kwargs = {'name': 'GSE MCA File: %s' % filename}
        kwargs.update(kws)
        Group.__init__(self,  **kwargs)
        self.nchans = nchans
        self.mcas   = []
        self.bad    = bad
        if bad is None:
            self.bad = []
        self._det0      = -1  # main "good" detector for energy calibration

        self.filename = filename
        if filename:
            self.read(filename=filename)

    def _firstgood_mca(self, chan_min=2, min_counts=2):
        """ find first good detector for alignment
        'good' is defined as at least min_counts counts
        above channel chan_min
        """
        for mca in self.mcas:
            if mca.counts[chan_min:].sum() > min_counts:
                return mca

    def get_energy(self, imca=None):
        "get energy, optionally selecting which mca to use"
        if imca is None:
            mca = self._firstgood_mca()
        else:
            mca = self.mcas[imca]
        return mca.get_energy()


    def get_counts(self, dt_correct=True, align=True):
        """ get summed MCA spectra,

        Options:
        --------
          align   align spectra in energy before summing (True).
        """
        mca0 = self._firstgood_mca()
        en  = mca0.get_energy()
        dat = 0
        for mca in self.mcas:
            mdat = mca.counts
            if align and mca != mca0:
                _en  = mca.get_energy()
                mdat = UnivariateSpline(_en, mdat, s=0)(en)
            if dt_correct:
                mdat *= mca.dt_factor
            dat = dat + mdat
        return dat.astype(np.int)

    def read(self, filename=None, bad=None):
        """read GSE MCA file"""
        self.filename = filename
        if bad is None:
            bad = self.bad
        fh    = open(filename)
        lines = fh.readlines()
        fh.close()
        ndet       = 1  # Assume single element data
        nrow       = 0
        data_mode  = 0
        counts     = []
        rois       = []
        environ    = []
        head = {'live time':[], 'real time':[], 'start time':'',
                'offset':[], 'slope':[], 'quad':[]}
        for l in lines:
            l  = l.strip()
            if len(l) < 1: continue
            if data_mode == 1:
                counts.append(str2ints(l))
            else:
                pos = l.find(' ')
                if (pos == -1): pos = len(l)
                tag = l[0:pos].strip()
                val = l[pos:len(l)].strip()
                if tag == 'VERSION:':
                    pass
                elif tag == "DATE:":
                    head['start time'] = val
                elif tag == "ELEMENTS:":
                    self.nelems = int(val)
                elif tag == 'CHANNELS:':
                    self.nchans = int(val)
                elif tag == 'ROIS:':
                    self.nrois = max(str2ints(val))
                elif tag == 'REAL_TIME:':
                    head['real time']  = str2floats(val)
                elif tag == 'LIVE_TIME:':
                    head['live time']  = str2floats(val)
                elif tag == 'CAL_OFFSET:':
                    head['offset'] = str2floats(val)
                elif tag == 'CAL_SLOPE:':
                    head['slope']  = str2floats(val)
                elif tag == 'CAL_QUAD:':
                    head['quad']   = str2floats(val)
                elif tag == 'DATA:':
                    data_mode = 1
                elif tag == 'ENVIRONMENT:':
                    addr, val = val.split('="')
                    val, desc  = val.split('"')
                    val = val.strip()
                    desc = desc.strip()
                    if desc.startswith('(') and desc.endswith(')'):
                        desc = desc[1:-1]
                    environ.append((desc, val, addr))
                elif tag[0:4] == 'ROI_':
                    iroi = int(tag[4:5])
                    item = tag[6:]
                    if iroi >= len(rois):
                        for ir in range(1  + iroi - len(rois)):
                            rois.append({'label':[], 'right':[], 'left':[]})
                    if item == "LABEL:":
                        rois[iroi]['label'] = str2str(val, delim='&')
                    elif item == "LEFT:":
                        rois[iroi]['left']  = str2ints(val)
                    elif item == "RIGHT:":
                        rois[iroi]['right'] = str2ints(val)
                else:
                    pass # print " Warning: " , tag, " is not supported here!"

        #
        counts =  np.array(counts)

        ## Data has been read, now store in MCA objects
        start_time = head['start time']
        sum_mca = None
        for imca in range(self.nelems):
            offset = head['offset'][imca]
            slope  = head['slope'][imca]
            quad   = head['quad'][imca]
            rtime  = head['real time'][imca]
            ltime  = head['live time'][imca]
            thismca = MCA(name='mca%i' % (imca+1),
                          nchans=self.nchans,
                          counts=counts[:,imca],
                          start_time=start_time,
                          offset=offset, slope=slope, quad=quad,
                          real_time=rtime, live_time=ltime)

            for desc, val, addr in environ:
                thismca.add_environ(desc=desc, val=val, addr=addr)

            for roi in rois:
                left = roi['left'][imca]
                right = roi['right'][imca]
                label = roi['label'][imca]
                thismca.add_roi(name=label, left=left, right=right, sort=False)
            thismca.rois.sort()
            self.mcas.append(thismca)
            if sum_mca is None:
                sum_mca = copy.deepcopy(thismca)
        sum_mca.counts = self.get_counts()
        sum_mca.raw    = self.get_counts(dt_correct=False)
        sum_mca.name = 'mcasum'
        self.sum = sum_mca
        return

    def add_roi(self, name='', left=0, right=0, bgr_width=3, sort=True):
        """add an ROI to the sum spectra"""
        name = name.strip()
        roi = ROI(name=name, left=left, right=right, bgr_width=bgr_width)
        rnames = [r.name.lower() for r in self.sum.rois]
        if name.lower() in rnames:
            iroi = rnames.index(name.lower())
            self.sum.rois[iroi] = roi
        else:
            self.sum.rois.append(roi)
        if sort:
            self.sum.rois.sort()

    def save_columnfile(self, filename, headerlines=None):
        "write summed counts to simple ASCII  column file"
        self.sum.save_columnfile(filename, headerlines=headerlines)

    def save_mcafile(self, filename):
        """
        write multi-element MCA file
        Parameters:
        -----------
        * filename: output file name
        """
        nchans = len(self.sum.counts)
        ndet   = len(self.mcas)

        # formatted count times and calibration
        rtimes  = ["%f" % m.real_time for m in self.mcas]
        ltimes  = ["%f" % m.live_time for m in self.mcas]
        offsets = ["%e" % m.offset    for m in self.mcas]
        slopes  = ["%e" % m.slope     for m in self.mcas]
        quads   = ["%e" % m.quad      for m in self.mcas]

        fp = open(filename, 'w')
        fp.write('VERSION:    3.1\n')
        fp.write('ELEMENTS:   %i\n' % ndet)
        fp.write('DATE:       %s\n' % self.mcas[0].start_time)
        fp.write('CHANNELS:   %i\n' % nchans)
        fp.write('REAL_TIME:  %s\n' % ' '.join(rtimes))
        fp.write('LIVE_TIME:  %s\n' % ' '.join(ltimes))
        fp.write('CAL_OFFSET: %s\n' % ' '.join(offsets))
        fp.write('CAL_SLOPE:  %s\n' % ' '.join(slopes))
        fp.write('CAL_QUAD:   %s\n' % ' '.join(quads))

        # Write ROIS  in channel units
        nrois = ["%i" % len(m.rois) for m in self.mcas]
        rois = [m.rois for m in self.mcas]
        fp.write('ROIS:      %s\n' % ' '.join(nrois))

        # assume number of ROIS is same for all elements
        for i in range(len(rois[0])):
            names = ' &  '.join([r[i].name  for r in rois])
            left  = ' '.join(['%i' % r[i].left  for r in rois])
            right = ' '.join(['%i' % r[i].right for r in rois])
            fp.write('ROI_%i_LEFT:  %s\n' % (i, left))
            fp.write('ROI_%i_RIGHT:  %s\n' % (i, right))
            fp.write('ROI_%i_LABEL: %s &\n' % (i, names))

        # environment
        for e in self.sum.environ:
            fp.write('ENVIRONMENT: %s="%s" (%s)\n' % (e.addr, e.val, e.desc))
        # data
        fp.write('DATA: \n')
        for i in range(nchans):
            d = ' '.join(["%i" % m.counts[i] for m in self.mcas])
            fp.write(" %s\n" % d)
        fp.close()

def gsemca_group_old(fname, _larch=None, **kws):
    """read GSECARS MCA file to larch group"""
    if _larch is None:
        raise Warning("cannot read GSE XRF group -- larch broken?")

    xfile = GSEMCA_File(fname)
    group = _larch.symtable.create_group()
    group.__name__ ='GSE XRF Data file %s' % fname
    group.filename = xfile.filename
    group.save_columnfile = xfile.save_columnfile
    group.save_mcafile = xfile.save_mcafile
    group.mcas     = xfile.mcas
    group.calib    = {'offset': xfile.sum.offset,
                      'slope': xfile.sum.slope,
                      'quad': xfile.sum.quad}
    group.rois     = xfile.sum.rois
    group.get_roi_counts = xfile.sum.get_roi_counts
    group.add_roi  = xfile.add_roi
    for attr in ('rois', 'environ', 'energy', 'counts', 'dt_factor',
                 'icr_calc', 'input_counts', 'live_time', 'nchans',
                 'real_time', 'start_time', 'tau', 'raw'):
        setattr(group, attr, getattr(xfile.sum, attr))
    return group

def gsemca_group(fname, _larch=None, **kws):
    """read GSECARS MCA file to larch group"""
    return GSEMCA_File(fname)

def xrf_background(energy, counts, group=None, _larch=None,
                   bottom_width=4, compress=4, exponent=2, **kws):
    """fit background for XRF spectra"""
    if _larch is None:
        raise Warning("cannot calculate xrf background -- larch broken?")

    slope = (energy[-1] - energy[0])/len(energy)
    xbgr = XRFBackground(bottom_width=bottom_width,
                         compress=compress,
                         exponent=exponent, **kws)
    xbgr.calc(counts, slope=slope)
    if group is not None:
        group.bgr = xbgr.bgr

def registerLarchPlugin():
    return ('_io', {'read_gsemca': gsemca_group,
                    'xrf_background': xrf_background})
