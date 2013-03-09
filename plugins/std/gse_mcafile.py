#!/usr/bin/python

import os
import sys
import copy
import bisect
import numpy

MIN_SLOPE   = 1.e-12
MIN_EN     = -1.   # in keV
MAX_EN     = 511.  # in keV

def str2float(str):
    return [float(i) for i in str.split()]

def str2int(str):
    return [int(i) for i in str2float(str)]

def str2str(str, delim=None):
    return [i.strip() for i in str.split(delim)]

class GSE_MCAFile:
    """
    Read GSECARS style MCA / Multi-element MCA files

    """
    def __init__(self, file=None, ndetectors=1, bad=None, maxpts=2048):

        self.ndetectors = ndetectors
        self.maxpts     = maxpts
        self.nrois      =  0

        self.data       = []
        self.rois       = []
        self.detectors  = []
        self.bad        = bad
        if bad is None:
            self.bad = []
        self._det0      = -1  # main "good" detector for energy calibration
        self.environ    = []
        self.elapsed    = {'live time':[], 'real time':[], 'start time':''}
        self.calibration= {'offset':[], 'slope':[], 'quad':[], 'twotheta':[]}

        if file: self.read(file=file)

    def get_calibration(self,detector=-1):
        if detector < 0: detector = self._det0
        if detector < 0:
            return (0,0,0)

        o = self.calibration['offset'][detector]
        s = self.calibration['slope'][detector]
        q = self.calibration['quad'][detector]
        s = max(s, MIN_SLOPE)
        return (o,s,q)

    def chan2energy(self,i,detector=None):
        d = detector
        if (not d): d = self._det0
        return (self.calibration['offset'][d] + i *
                (self.calibration['slope'][d] + i *
                 self.calibration['quad'][d]))

    def get_energy(self,detector=None):
        e = []
        d = detector
        if self._det0 == -1:
            # print " no data read"
            return numpy.zeros(self.maxpts)
        if not d:             d = self._det0
        e = numpy.arange(self.maxpts, dtype='f')

        e = (self.calibration['offset'][d] + e *
             (self.calibration['slope'][d] + e *
              self.calibration['quad'][d]))
        return e

    def get_data(self, detector=None, align=True):
        " get summed detectors, aligning to specified detector "
        if self.ndetectors == 1:
            return self.data
        d   = detector
        if d is None: d = self._det0
        dat = self.data[d]
        if align:
            (o1,s1,q1) = self.get_calibration(detector=d)
            for j in self.detectors:
                if (j != d):
                    (o2,s2,q2) = self.get_calibration(detector=j)
                    etmp = o2 + s2 * numpy.arange(len(dat),dtype='f')
                    for i in range(self.maxpts):
                        e = o1 + s1*i

                        ip = bisect.bisect(etmp,e)
                        if ip < 1: ip=1
                        if ip > 2047: ip=2047

                        x0 = o2 + s2*(ip-1)
                        y0 = self.data[j][ip-1]
                        y1 = self.data[j][ip]

                        dat[i]  = dat[i] + y0 + (y1-y0)*(e-x0)/(s2)
                dat = numpy.array(dat)
        return dat

    def get_element(self,detector=0):
        " get data from a single element"
        if self.ndetector == 1:
            return self.data
        return self.data[detector]

    def read(self, file=None, bad=[]):
        self.filename = file
        f    = open(file)
        lines = f.readlines()
        f.close()
        ndet        = 1  # Assume single element data
        nrow        = 0
        self.data   = []
        data_mode   = 0
        for l in lines:
            l  = l.strip()
            if len(l) < 1: continue
            if data_mode == 1:
                self.data.append(str2int(l))
            else:
                pos = l.find(' ')
                if (pos == -1): pos = len(l)
                tag = l[0:pos].strip()
                val = l[pos:len(l)].strip()
                if tag == 'VERSION:':
                    pass
                elif tag == "DATE:":
                    for i in range(len(self.elapsed['start time'])):
                        self.elapsed['start_time'] = val
                elif tag == "ELEMENTS:":
                    self.ndetectors = int(val)
                elif tag == 'CHANNELS:':
                    self.maxpts = int(val)
                elif tag == 'ROIS:':
                    self.nrois = max(str2int(val))
                elif tag == 'REAL_TIME:':
                    self.elapsed['real time']  = str2float(val)
                elif tag == 'LIVE_TIME:':
                    self.elapsed['live time']  = str2float(val)
                elif tag == 'CAL_OFFSET:':
                    self.calibration['offset'] = str2float(val)
                elif tag == 'CAL_SLOPE:':
                    self.calibration['slope']  = str2float(val)
                elif tag == 'CAL_QUAD:':
                    self.calibration['quad']   = str2float(val)
                elif tag == 'TWO_THETA:':
                    self.calibration['twotheta'] = str2float(val)
                elif tag == 'DATA:':
                    data_mode = 1
                elif tag == 'ENVIRONMENT:':
                    addr, val = val.split('="')
                    val, desc  = val.split('"')
                    val.strip()
                    desc.strip()
                    if desc.startswith('(') and desc.endswith(')'):
                        desc = desc[1:-1]
                    self.environ.append({'name': addr, 'value': val,
                                         'desc': desc})

                elif tag[0:4] == 'ROI_':
                    iroi = int(tag[4:5])
                    item = tag[6:]
                    if iroi >= len(self.rois):
                        for ir in range(1  + iroi - len(self.rois)):
                            self.rois.append({'label':[], 'right':[], 'left':[]})
                    if item == "LABEL:":
                        self.rois[iroi]['label'] = str2str(val, delim='\&')
                    elif item == "LEFT:":
                        self.rois[iroi]['left']  = str2int(val)
                    elif item == "RIGHT:":
                        self.rois[iroi]['right'] = str2int(val)
                else:
                    pass # print " Warning: " , tag, " is not supported here!"

        #  find first valid detector, identify bad detectors
        self.data = numpy.transpose(numpy.array(self.data))

        m = self.maxpts - 1
        self._det0 = -1
        for i in range(self.ndetectors):
            is_good = i not in bad
            if is_good:
                o, s, q = self.get_calibration(detector=i)
                emin   = q
                emax   = o + m * (s + m  * q)
                d      = self.get_data(detector=i, align=0)
                if (self._det0 == -1 and
                    emin > MIN_EN  and emax < MAX_EN):
                    self._det0 = i
                if emax > MAX_EN or d.max() < 2:
                    is_good = False
            if is_good:
                self.detectors.append(i)
        if self.ndetectors == 1:
            self.data = self.data[0]

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
            if  d[i] > 0:   xlog = numpy.log10(d[i])
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
    group.chan2energy  = xfile.chan2energy
    group.get_data  = xfile.get_data
    for key, val in xfile.__dict__.items():
        if not key.startswith('_'):
            setattr(group, key, val)
    return group

def registerLarchPlugin():
    return ('_io', {'_gsemca_old': gsemca_group})

