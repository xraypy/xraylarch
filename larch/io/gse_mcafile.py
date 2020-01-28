#!/usr/bin/python

import os
import copy
import numpy as np
from scipy.interpolate import UnivariateSpline

from larch import Group
from larch.xrf import MCA, ROI

def str2floats(s, delim='&'):
    s = s.replace('&', ' ')
    return [float(i) for i in s.split()]

def str2ints(s, delim='&'):
    return [int(i) for i in str2floats(s, delim=delim)]

def str2str(s, delim='&'):
    s = s.strip()
    return [i.strip() for i in s.split(delim) if len(i) > 0]

class GSEMCA_Header(object):
    version  = 'unknown'
    date = ''
    elements = 1
    channels = 2048
    rois = []
    live_time = []
    real_time = []
    cal_slope = []
    cal_offset = []
    cal_quad = []

class GSEMCA_File(Group):
    """
    Read GSECARS style MCA / Multi-element MCA files
    """
    def __init__(self, filename=None, text=None, bad=None, **kws):
        kwargs = {'name': 'GSE MCA File: %s' % filename}
        kwargs.update(kws)
        Group.__init__(self,  **kwargs)
        self.mcas   = []
        self.__mca0 = None
        self.bad    = bad
        if bad is None:
            self.bad = []

        self.filename = filename
        if filename:
            self.read(filename=filename)
        elif text is not None:
            self.readtext(text)

    def __get_mca0(self, chan_min=2, min_counts=2):
        """ find first good detector for alignment
        'good' is defined as at least min_counts counts
        above channel chan_min
        """
        if self.__mca0 is None:
            for imca, mca in enumerate(self.mcas):
                if mca.counts[chan_min:].sum() > min_counts:
                    self.__mca0 = mca
                    self.offset = mca.offset
                    self.slope  = mca.slope
                    self.quad   = mca.quad
                    break
                elif imca not in self.bad:
                    self.bad.append(imca)
            if self.__mca0 is None:
                self.__mca0 = mca = self.mcas[0]
                self.offset = mca.offset
                self.slope  = mca.slope
                self.quad   = mca.quad
        return self.__mca0

    def get_energy(self, imca=None):
        "get energy, optionally selecting which mca to use"
        if imca is not None:
            mca = self.mcas[imca]
        else:
            mca = self.__get_mca0()
        return mca.get_energy()

    def get_counts(self, dt_correct=True, align=True):
        """ get summed MCA spectra,

        Options:
        --------
          align   align spectra in energy before summing (True).
        """
        mca0 = self.__get_mca0()
        en  = mca0.get_energy()
        dat = 0
        for mca in self.mcas:
            mdat = mca.counts
            if align and mca != mca0:
                _en  = mca.get_energy()
                mdat = UnivariateSpline(_en, mdat, s=0)(en)
            if dt_correct:
                mdat = mdat * mca.dt_factor
            dat = dat + mdat
        return dat.astype(np.int)

    def predict_pileup(self, scale=None):
        """predict pileup for an MCA spectra from its auto-correlation.

        Options:
        --------
          scale   factor to apply to convolution [found from data]

        the output `pileup` will be the average of the `pileup` for each MCA

        """
        pileup = self.mcas[0].counts * 0.0
        for m in self.mcas:
            m.predict_pileup(scale=scale)
            pileup += m.pileup
        self.pileup = pileup / len(self.mcas)

    def predict_escape(self, det='Si', scale=1):
        """predict detector escape, save to `escape` attribute

        Options:
        --------
          det       detector material ['Si']
          scale     scale factor [1]

        Outputs 'escape' attribute will contain the average `escape` for each MCA
        """
        escape = self.mcas[0].counts * 0.0
        for m in self.mcas:
            m.predict_escape(det=det, scale=scale)
            escape += m.escape
        self.escape = escape  / len(self.mcas)

    def read(self, filename=None, bad=None):
        """read GSE MCA file"""
        self.filename = filename
        with open(filename, 'r') as fh:
            return self.readtext(fh.read(), bad=bad)

    def readtext(self, text, bad=None):
        """read text of GSE MCA file"""
        lines = text.split('\n')
        if bad is None:
            bad = self.bad
        nrow       = 0
        data_mode  = 'HEADER'
        counts     = []
        rois       = []
        environ    = []
        self.incident_energy = None
        head = self.header = GSEMCA_Header()
        for l in lines:
            l  = l.strip()
            if len(l) < 1: continue
            if data_mode == 'DATA':
                counts.append(str2ints(l))
            else:
                pos = l.find(' ')
                if (pos == -1): pos = len(l)
                tag = l[0:pos].strip().lower()
                if tag.endswith(':'):
                    tag = tag[:-1]
                val = l[pos:len(l)].strip()
                if tag in ('version', 'date'):
                    setattr(head, tag, val)
                elif tag in ('elements', 'channels'):
                    setattr(head, tag, int(val))
                elif tag in ('real_time', 'live_time', 'cal_offset',
                             'cal_slope', 'cal_quad'):
                    setattr(head, tag, str2floats(val))
                elif tag == 'rois':
                    head.rois = str2ints(val)
                    self.nrois = max(head.rois)
                elif tag == 'data':
                    data_mode = 'DATA'
                elif tag == 'environment':
                    addr, val = val.split('="')
                    val, desc = val.split('"')
                    val = val.strip()
                    desc = desc.strip()
                    if desc.startswith('(') and desc.endswith(')'):
                        desc = desc[1:-1]
                    environ.append((desc, val, addr))
                    if 'mono' in desc.lower() and 'energy' in desc.lower():
                        try:
                            val = float(val)
                        except ValueError:
                            pass
                        self.incident_energy = val
                elif tag[0:4] == 'roi_':
                    iroi, item = tag[4:].split('_')
                    iroi = int(iroi)
                    if iroi >= len(rois):
                        for ir in range(1  + iroi - len(rois)):
                            rois.append({'label':[], 'right':[], 'left':[]})
                    if item == "label":
                        rois[iroi]['label'] = str2str(val, delim='&')
                    elif item == "left":
                        rois[iroi]['left']  = str2ints(val)
                    elif item == "right":
                        rois[iroi]['right'] = str2ints(val)
                else:
                    pass # print(" Warning: " , tag, " is not supported here!")

        #
        counts =  np.array(counts)
        ## Data has been read, now store in MCA objects
        sum_mca = None

        for tag in ('real_time', 'live_time', 'cal_offset',
                    'cal_slope', 'cal_quad'):
            val = getattr(head, tag)
            # print( ' Attr ', tag, val)
            if len(val) == 1 and head.elements > 1:
                val = [val[0]]*head.elements
                setattr(head, tag, val)
        for imca in range(head.elements):
            thismca = MCA(name='mca%i' % (imca+1),
                          nchans=head.channels,
                          counts=counts[:,imca],
                          start_time=head.date,
                          offset=head.cal_offset[imca],
                          slope=head.cal_slope[imca],
                          quad=head.cal_quad[imca],
                          real_time=head.real_time[imca],
                          live_time=head.live_time[imca])

            for desc, val, addr in environ:
                thismca.add_environ(desc=desc, val=val, addr=addr)

            for roi in rois:
                left = roi['left'][imca]
                right = roi['right'][imca]
                label = roi['label'][imca]
                if right > 1 and len(label) > 1:
                    thismca.add_roi(name=label, left=left, right=right,
                                    sort=False, counts=counts[:,imca])
            thismca.rois.sort()
            self.mcas.append(thismca)

        mca0 = self.__get_mca0()
        self.counts = self.get_counts()
        self.raw    = self.get_counts(dt_correct=False)
        self.name   = 'mcasum'
        self.energy = mca0.energy[:]
        self.environ = mca0.environ
        self.real_time = mca0.real_time
        self.live_time = mca0.live_time
        self.offset = mca0.offset
        self.slope  = mca0.slope
        self.quad   = mca0.quad
        self.rois = []
        for roi in mca0.rois:
            self.add_roi(name=roi.name, left=roi.left,
                         right=roi.right, sort=False,
                         counts=counts, to_mcas=False)
        self.rois.sort()
        return

    def add_roi(self, name='', left=0, right=0, bgr_width=3,
                counts=None, sort=True, to_mcas=True):
        """add an ROI to the sum spectra"""
        name = name.strip()
        # print('GSEMCA: Add ROI ', name, left, right)
        roi = ROI(name=name, left=left, right=right,
                  bgr_width=bgr_width, counts=counts)
        rnames = [r.name.lower() for r in self.rois]
        if name.lower() in rnames:
            iroi = rnames.index(name.lower())
            self.rois[iroi] = roi
        else:
            self.rois.append(roi)
        if sort:
            self.rois.sort()
        if to_mcas:
            mca0 = self.__get_mca0()
            slo0 = mca0.slope
            off0 = mca0.offset
            mca0.add_roi(name=name, left=left, right=right,
                         bgr_width=bgr_width)
            for mca in self.mcas:
                if mca != mca0:
                    xleft  = int(0.5 + ((off0 + left*slo0) - mca.offset)/mca.slope)
                    xright = int(0.5 + ((off0 + right*slo0) - mca.offset)/mca.slope)
                    mca.add_roi(name=name, left=xleft, right=xright,
                                 bgr_width=bgr_width)

    def save_mcafile(self, filename):
        """
        write multi-element MCA file
        Parameters:
        -----------
        * filename: output file name
        """
        with open(filename, 'w') as fh:
            fh.write(self.dump_mcafile())

    def dump_mcafile(self):
        """return text of MCA file, not writing to disk, as for dumping"""
        nchans = len(self.counts)
        ndet   = len(self.mcas)

        # formatted count times and calibration
        rtimes  = ["%f" % m.real_time for m in self.mcas]
        ltimes  = ["%f" % m.live_time for m in self.mcas]
        offsets = ["%e" % m.offset    for m in self.mcas]
        slopes  = ["%e" % m.slope     for m in self.mcas]
        quads   = ["%e" % m.quad      for m in self.mcas]

        b = ['VERSION:    3.1']
        b.append('ELEMENTS:   %i' % ndet)
        b.append('DATE:       %s' % self.mcas[0].start_time)
        b.append('CHANNELS:   %i' % nchans)
        b.append('REAL_TIME:  %s' % ' '.join(rtimes))
        b.append('LIVE_TIME:  %s' % ' '.join(ltimes))
        b.append('CAL_OFFSET: %s' % ' '.join(offsets))
        b.append('CAL_SLOPE:  %s' % ' '.join(slopes))
        b.append('CAL_QUAD:   %s' % ' '.join(quads))

        # Write ROIS  in channel units
        nrois = ["%i" % len(m.rois) for m in self.mcas]
        rois = [m.rois for m in self.mcas]
        b.append('ROIS:      %s' % ' '.join(nrois))

        # don't assume number of ROIS is same for all elements
        nrois = max([len(r) for r in rois])
        # print('NROIS ' , nrois, [len(r) for r in rois])
        for ir, r in enumerate(rois):
            if len(r) < nrois:
                for i in range(nrois - len(r)):
                    r.append(ROI(name='', left=0, right=0))
        # print( 'NROIS ' , nrois, [len(r) for r in rois])
        for i in range(len(rois[0])):
            names = ' &  '.join([r[i].name  for r in rois])
            left  = ' '.join(['%i' % r[i].left  for r in rois])
            right = ' '.join(['%i' % r[i].right for r in rois])
            b.append('ROI_%i_LEFT:  %s' % (i, left))
            b.append('ROI_%i_RIGHT:  %s' % (i, right))
            b.append('ROI_%i_LABEL: %s &' % (i, names))

        # environment
        for e in self.environ:
            b.append('ENVIRONMENT: %s="%s" (%s)' % (e.addr, e.val, e.desc))
        # data
        b.append('DATA: ')
        for i in range(nchans):
            d = ' '.join(["%i" % m.counts[i] for m in self.mcas])
            b.append(" %s" % d)
        b.append('')
        return '\n'.join(b)

    def save_ascii(self, filename):
        """
        write multi-element MCA file to XDI-style ASCII file
        Parameters:
        -----------
        * filename: output file name
        """
        nchans = len(self.counts)
        ndet   = len(self.mcas)


        mca0 = self.mcas[0]
        buff = ['# XDI/1.0  GSE/1.0',
                '# Collection.date: %s' % mca0.start_time,
                '# Collection.n_detectors: %i' % ndet,
                '# Collection.n_channels: %i' % nchans,
                '# Collection.real_time: %i' % mca0.real_time,
                '# Collection.live_time: %s' % mca0.live_time,
                '# Calibration.offset: %s' % mca0.offset,
                '# Calibration.slope: %s' % mca0.slope,
                '# Calibration.quad: %s' % mca0.quad,
                '# Column.1: energy keV']

        label = '#   energy  '
        for i in range(ndet):
            buff.append('# Column.%i: MCA%i counts' % (i+2, i+1))
            label = '%s    MCA%i '  % (label, i+1)

        froi = '# ROI.%i: %s [%i:%i]'
        fenv = '# ENV.%s:  %s [%s]'
        for i, roi in enumerate(mca0.rois):
            buff.append(froi % (i, roi.name, roi.left, roi.right))


        for e in self.environ:
            desc = e.desc.replace(' ', '_')
            buff.append(fenv % (desc, e.val, e.addr))
        buff.append('#--------------------')
        buff.append(label)

        # data
        for i in range(nchans):
            d = ['%9.3f' % self.energy[i]]
            d.extend(['%11i' % m.counts[i] for m in self.mcas])
            buff.append(' %s' % ' '.join(d))
        buff.append('')

        fp = open(filename, 'w')
        fp.write('\n'.join(buff))
        fp.close()


def gsemca_group(filename=None, text=None, _larch=None, **kws):
    """read GSECARS MCA file to larch group"""
    return GSEMCA_File(filename=filename, text=text)
