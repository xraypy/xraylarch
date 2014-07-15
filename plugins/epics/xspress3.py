#!/usr/bin/python
import sys
import os
import time
from  epics import Device, caget, caput
from epics.devices.mca import MCA, ROI, OrderedDict
import numpy

from ConfigParser import ConfigParser

MAX_ROIS = 32

class Xspress3(Device):
    """very simple XSPRESS3 interface"""
    attrs = ('NumImages','Acquire', 'Acquire_RBV', 
             'ERASE', 'TriggerMode', 'StatusMessage_RBV',
             'DetectorState_RBV', 'NumImages_RBV')

    _nonpvs  = ('_prefix', '_pvs', '_delim', 'filesaver', 'fileroot',
                'pathattrs', '_nonpvs', 'nmca', 'dxps', 'mcas')

    pathattrs = ('FilePath', 'FileTemplate',
                 'FileName', 'FileNumber',
                 'Capture',  'NumCapture')

    def __init__(self, prefix, nmca=4, filesaver='HDF5:',
                 fileroot='/home/xspress3/cars5/Data'):
        self.nmca = nmca
        attrs = list(self.attrs)
        attrs.extend(['%s%s' % (filesaver,p) for p in self.pathattrs])

        self.filesaver = filesaver
        self.fileroot = fileroot
        self._prefix = prefix

        self.mcas = [MCA(prefix, mca=i+1) for i in range(nmca)]

        Device.__init__(self, prefix, attrs=attrs, delim='')

        time.sleep(0.1)

    def get_rois(self):
        return [m.get_rois() for m in self.mcas]

    def copy_rois_to_savearrays(self, roilist):
        """copy rois from MCA record to arrays to be saved
        by XSPress3"""
        roilist = list(roilist)
        if len(roilist) < 4: roilist.append((10, 4090))
        pref = self._prefix
        for iroi, roiname in enumerate(roilist):
            if isinstance(roiname, tuple):
                lo, hi = roiname
            else:
                roiname = roiname.lower().strip()
                lo, hi = 1, 4000
                for ix in range(nroi):
                    nm = caget('%smca1.R%iNM' % (pref, ix))
                    if nm.lower().strip() == roiname:
                        lo = caget('%smca1.R%iLO' % (pref, ix))
                        hi = caget('%smca1.R%iHI' % (pref, ix))
                        break
            for imca in range(1, nmca+1):
                pv_lo = "%sC%i_MCA_ROI%i_LLM" % (pref, imca, iroi+1)
                pv_hi = "%sC%i_MCA_ROI%i_HLM" % (pref, imca, iroi+1)
                caput(pv_hi, hi)
                caput(pv_lo, lo)

    def roi_calib_info(self):
        buff = ['[rois]']
        add = buff.append
        roidat = self.get_rois()
        for i, k in enumerate(roidat[0].keys()):
            s = [list(roidat[m][k]) for m in range(self.nmca)]
            rd = repr(s).replace('],', '').replace('[', '').replace(']','').replace(',','')
            add("ROI%2.2i = %s | %s" % (i,k,rd))

        add('[calibration]')
        add("OFFSET = %s " % (' '.join(["0.00 "] * self.nmca)))
        add("SLOPE  = %s " % (' '.join(["0.10 "] * self.nmca)))
        add("QUAD   = %s " % (' '.join(["0.00 "] * self.nmca)))
        add('[dxp]')
        return buff

    def restore_rois(self, roifile):
        """restore ROI setting from ROI.dat file"""
        cp =  ConfigParser()
        cp.read(roifile)
        rois = []
        self.mcas[0].clear_rois()
        prefix = self.mcas[0]._prefix
        if prefix.endswith('.'):
            prefix = prefix[:-1]
        iroi = 0
        for a in cp.options('rois'):
            if a.lower().startswith('roi'):
                name, dat = cp.get('rois', a).split('|')
                lims = [int(i) for i in dat.split()]
                lo, hi = lims[0], lims[1]
                roi = ROI(prefix=prefix, roi=iroi)
                roi.left = lo
                roi.right = hi
                roi.name = name.strip()
                rois.append(roi)
                iroi += 1

        epics.poll(0.050, 1.0)
        self.mcas[0].set_rois(rois)
        cal0 = self.mcas[0].get_calib()
        for mca in self.mcas[1:]:
            mca.set_rois(rois, calib=cal0)

    def useExternalTrigger(self):
        self.TriggerMode = 3

    def setTriggerMode(self, mode):
        self.TriggerMode = mode

    def start(self, capture=True):
        self.ERASE = 1
        time.sleep(.05)
        if capture:
            self.FileCaptureOn()
        self.Acquire = 1

    def stop(self):
        self.Acquire = 0
        self.FileCaptureOff()

    def filePut(self, attr, value, **kw):
        return self.put("%s%s" % (self.filesaver, attr), value, **kw)

    def setFilePath(self, pathname):
        fullpath = os.path.join(self.fileroot, pathname)
        return self.filePut('FilePath', fullpath)

    def setFileTemplate(self,fmt):
        return self.filePut('FileTemplate', fmt)

    def setFileWriteMode(self,mode):
        return self.filePut('FileWriteMode', mode)

    def setFileName(self,fname):
        return self.filePut('FileName', fname)

    def nextFileNumber(self):
        self.setFileNumber(1+self.fileGet('FileNumber'))

    def setFileNumber(self, fnum=None):
        if fnum is None:
            self.filePut('AutoIncrement', 1)
        else:
            self.filePut('AutoIncrement', 0)
            return self.filePut('FileNumber',fnum)

    def getLastFileName(self):
        return self.fileGet('FullFileName_RBV',as_string=True)

    def FileCaptureOn(self):
        return self.filePut('Capture', 1)

    def FileCaptureOff(self):
        return self.filePut('Capture', 0)

    def setFileNumCapture(self,n):
        return self.filePut('NumCapture', n)

    def FileWriteComplete(self):
        return (0==self.fileGet('WriteFile_RBV') )

    def getFileTemplate(self):
        return self.fileGet('FileTemplate_RBV',as_string=True)

    def getFileName(self):
        return self.fileGet('FileName_RBV',as_string=True)

    def getFileNumber(self):
        return self.fileGet('FileNumber_RBV')

    def getFilePath(self):
        return self.fileGet('FilePath_RBV',as_string=True)

    def getFileNameByIndex(self,index):
        return self.getFileTemplate() % (self.getFilePath(), self.getFileName(), index)
