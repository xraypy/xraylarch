#!/usr/bin/python

import os
import sys
import copy
import numpy as np
from scipy.interpolate import UnivariateSpline

from mca import MCA

MIN_SLOPE   = 1.e-12
MIN_EN     = -1.   # in keV
MAX_EN     = 511.  # in keV

def str2floats(s):
    return [float(i) for i in s.split()]

def str2ints(s):
    return [int(i) for i in str2floats(s)]

def str2str(s, delim=None):
    s = s.strip()
    return [i.strip() for i in s.split(delim) if len(i) > 0]

class MCA_ROI(object):
    """Region of Interest for an MCA or Multi-Element MCA"""
    def __init__(self, name=None, left=None, right=None, counts=None):
        self.name = name
        self.left = left
        self.right = right
    def get_counts(self, spectra):
        """get integrated roi from specta"""

class GSE_MCAFile:
    """
    Read GSECARS style MCA / Multi-element MCA files

    """
    def __init__(self, filename=None, bad=None, nchans=2048):

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
            if mca.data[chan_min:].sum() > min_counts:
                return mca

    def get_energy(self, imca=None):
        "get energy, optionally selecting which mca to use"
        if imca is None:
            mca = self._firstgood_mca()
        else:
            mca = self.mcas[imca]
        return mca.get_energy()


    def get_data(self, align=True):
        """ get summed MCA spectra,

        Options:
        --------
          align   align spectra in energy before summing (True).
        """
        if self.nelems == 1:
            return self.data
        mca0 = self._firstgood_mca()
        en  = mca0.get_energy()
        dat = 0
        for mca in self.mcas:
            mdat = mca.data
            if align and mca != mca0:
                _en  = mca.get_energy()
                mdat = UnivariateSpline(_en, mdat, s=0)(en)
            dat = dat + mdat
        return dat

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
        data       = []
        rois       = []
        environ    = []
        head = {'live time':[], 'real time':[], 'start time':'',
                'offset':[], 'slope':[], 'quad':[]}
        for l in lines:
            l  = l.strip()
            if len(l) < 1: continue
            if data_mode == 1:
                data.append(str2ints(l))
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
                    val.strip()
                    desc.strip()
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

        #  find first valid detector, identify bad detectors
        data =  np.array(data)
        if self.nelems == 1:
            data = data[0]

        ## Data has been read, now store in MCA objects
        start_time = head['start time']
        for imca in range(self.nelems):
            offset = head['offset'][imca]
            slope  = head['slope'][imca]
            quad   = head['quad'][imca]
            rtime  = head['real time'][imca]
            ltime  = head['real time'][imca]
            thismca = MCA(name='mca%i' % (imca+1),
                          nchans=self.nchans,
                          data=data[:,imca],
                          start_time=start_time,
                          offset=offset, slope=slope, quad=quad,
                          real_time=rtime, live_time=ltime)

            for desc, val, add in environ:
                thismca.add_environ(desc=desc, val=val, addr=addr)

            for roi in rois:
                left = roi['left'][imca]
                right = roi['right'][imca]
                label = roi['label'][imca]
                thismca.add_roi(name=label, left=left, right=right)
            thismca.rois.sort()
            self.mcas.append(thismca)
        return

    def write_ascii(self, file=None, elem=None, all=1, det=[]):
        if file is None:
            return -1
        f = open(file, "w+")
        f.write("# XRF data from %s\n" % (self.filename))

        f.write("# energy calibration (offset/slope/quad)= (%.9g/%.9g%.9g)\n"\
                %  self.get_calibration())
        f.write("# Live Time, Real Time = %f, %f\n" %
                (self.elapsed['real time'][0],   self.elapsed['live time'][0]))
        f.write("# %i ROIS:\n" % self.nrois)
        for r in self.rois:
            try:
                label = r['label'][0]
                left  = r['left'][0]
                right = r['right'][0]
                f.write("#   %s : [%i, %i]\n" % (label, left, right))
            except IndexError:
                pass

        f.write("#-------------------------\n")
        f.write("#    energy       counts     log10(counts)\n")

        e = self.get_energy()

        if all == 1:
            d = self.get_data(align=1)
        else:
            if elem is not None: elem = 0
            d = self.get_data(detector=elem)

        for i in range(len(e)-1):
            xlog = 0.
            if  d[i] > 0:   xlog = np.log10(d[i])
            f.write(" %10.4f  %12.3f  %10.5f\n" % (e[i],d[i],xlog))
        f.write("\n")
        f.close()

def gsemca_group(fname, _larch=None, **kws):
    """simple mapping of GSECARS MCA file to larch groups"""
    if _larch is None:
        raise Warning("cannot read GSE XRF group -- larch broken?")

    xfile = GSE_MCAFile(fname)
    group = _larch.symtable.create_group()
    group.__name__ ='GSE XRF Data file %s' % fname
    group.energy = xfile.get_energy()
    group.data  = xfile.get_data()
    for key, val in xfile.__dict__.items():
        if not key.startswith('_'):
            setattr(group, key, val)
    return group

def registerLarchPlugin():
    return ('_io', {'read_gsemca': gsemca_group})

