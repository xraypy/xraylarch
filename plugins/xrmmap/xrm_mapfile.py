from __future__ import print_function
import re
import os
import sys
import socket
import time
import datetime
import h5py
import numpy as np
import six
import scipy.stats as stats
import json
import multiprocessing as mp
from functools import partial
import larch
from larch.utils.debugtime import debugtime
from larch.utils.strutils import fix_filename, bytes2str, version_ge
from larch_plugins.io import nativepath, new_filename
from larch_plugins.xrf import MCA, ROI
from larch_plugins.xrmmap import (FastMapConfig, read_xrf_netcdf, read_xsp3_hdf5,
                                  readASCII, readMasterFile, readROIFile,
                                  readEnvironFile, parseEnviron, read_xrd_netcdf,
                                  read_xrd_hdf5)
from larch_plugins.xrd import (XRD,E_from_lambda,integrate_xrd_row,q_from_twth,
                               q_from_d,lambda_from_E,read_xrd_data)
from larch_plugins.tomo import tomo_reconstruction,reshape_sinogram,trim_sinogram


NINIT = 32
COMPRESSION_OPTS = 2
COMPRESSION = 'gzip'
#COMPRESSION = 'lzf'
DEFAULT_ROOTNAME = 'xrmmap'
NOT_OWNER = "Not Owner of HDF5 file %s"
STEPS = 5001

def h5str(obj):
    '''strings stored in an HDF5 from Python2 may look like
     "b'xxx'", that is containg "b".  strip these out here
    '''
    out = str(obj)
    if out.startswith("b'") and out.endswith("'"):
        out = out[2:-1]
    return out

def isotime(xtime):
    if type(xtime) is not float:
        xtime = time.mktime(time.strptime(xtime))
    return time.strftime("%Y-%m-%d %H:%M:%S" , time.localtime(xtime))

class GSEXRM_FileStatus:
    no_xrfmap    = 'hdf5 does not have top-level XRF map'
    no_xrdmap    = 'hdf5 does not have top-level XRD map'
    created      = 'hdf5 has empty schema'  # xrm map exists, no data
    hasdata      = 'hdf5 has map data'      # array sizes known
    wrongfolder  = 'hdf5 exists, but does not match folder name'
    err_notfound = 'file not found'
    empty        = 'file is empty (read from folder)'
    err_nothdf5  = 'file is not hdf5 (or cannot be read)'

def getFileStatus(filename, root=None, folder=None):
    '''return status, top-level group, and version'''
    # set defaults for file does not exist
    # print(" Get Status ", filename, folder)
    if folder is not None:
        folder = os.path.abspath(folder)
        parent, folder = os.path.split(folder)
    status, top, vers = GSEXRM_FileStatus.err_notfound, '', ''
    if root not in ('', None):
        top = root
    # see if file exists:
    if (not os.path.exists(filename) or
        not os.path.isfile(filename) ):
        return status, top, vers

    # see if file is empty/too small(signifies "read from folder")
    if os.stat(filename).st_size < 1024:
        return GSEXRM_FileStatus.empty, top, vers

    # see if file is an H5 file
    try:
        fh = h5py.File(filename)
    except IOError:
        return GSEXRM_FileStatus.err_nothdf5, top, vers

    status =  GSEXRM_FileStatus.no_xrfmap
    ##
    def test_h5group(group, folder=None):
        valid = ('config' in group and 'roimap' in group)
        for attr in  ('Version', 'Map_Folder',
                      'Dimension', 'Start_Time'):
            valid = valid and attr in group.attrs
        if not valid:
            return None, None
        status = GSEXRM_FileStatus.hasdata
        vers = group.attrs.get('Version','')
        fullpath = group.attrs.get('Map_Folder','')
        _parent, _folder = os.path.split(fullpath)

        if folder is not None and folder != _folder:
            status = GSEXRM_FileStatus.wrongfolder
        return status, vers

    if root is not None and root in fh:
        s, v = test_h5group(fh[root], folder=folder)
        if s is not None:
            status, top, vers = s, root, v
    else:
        # print( 'Root was None ', fh.items())
        for name, group in fh.items():
            s, v = test_h5group(group, folder=folder)
            if s is not None:
                status, top, vers = s, name, v
                break
    fh.close()
    return status, top, vers

def isGSEXRM_MapFolder(fname):
    "return whether folder a valid Scan Folder (raw data)"
    if (fname is None or not os.path.exists(fname) or
        not os.path.isdir(fname)):
        return False
    flist = os.listdir(fname)
    for f in ('Master.dat', 'Environ.dat', 'Scan.ini'):
        if f not in flist:
            return False

    has_xrmdata = False

    header, rows = readMasterFile(os.path.join(fname, 'Master.dat'))
    try:
        for f in rows[0]:
            if f in flist:
                has_xrmdata = True
    except:
        pass
    return has_xrmdata

H5ATTRS = {'Type': 'XRM 2D Map',
           'Version': '2.0.1',
           'Title': 'Epics Scan Data',
           'Beamline': 'GSECARS, 13-IDE / APS',
           'Start_Time': '',
           'Stop_Time': '',
           'Map_Folder': '',
           'Dimension': 2,
           'Process_Machine': '',
           'Process_ID': 0,
           'Compression': ''}

def create_xrmmap(h5root, root=None, dimension=2, folder='', start_time=None):
    '''creates a skeleton '/xrmmap' group in an open HDF5 file

    This is left as a function, not method of GSEXRM_MapFile below
    because it may be called by the mapping collection program
    (ie, from collector.py) when a map is started

    This leaves a structure to be filled in by
    GSEXRM_MapFile.init_xrmmap(),
    '''
    attrs = {}
    attrs.update(H5ATTRS)
    if start_time is None:
        start_time = time.ctime()

    attrs.update({'Dimension':dimension, 'Start_Time':start_time,
                  'Map_Folder': folder, 'Last_Row': -1})
    if root in ('', None):
        root = DEFAULT_ROOTNAME
    xrmmap = h5root.create_group(root)

    for key, val in attrs.items():
        xrmmap.attrs[key] = str(val)

    g = xrmmap.create_group('roimap')
    g.attrs['type'] = 'roi maps'
    g.attrs['desc'] = 'ROI data, including summed and deadtime corrected maps'

    g = xrmmap.create_group('config')
    g.attrs['type'] = 'scan config'
    g.attrs['desc'] = '''scan configuration, including scan definitions,
    ROI definitions, MCA calibration, Environment Data, etc'''

    xrmmap.create_group('scalars')

    xrmmap.create_group('areas')
    xrmmap.create_group('work')
    xrmmap.create_group('positions')

    conf = xrmmap['config']
    for name in ('scan', 'general', 'environ', 'positioners', 'notes',
                 'motor_controller', 'rois', 'mca_settings', 'mca_calib'):
        conf.create_group(name)

    h5root.flush()

def ensure_subgroup(subgroup,group):
    
    if subgroup not in group.keys():
        return group.create_group(subgroup)
    else:
        return group[subgroup]

# def ensure_subgroup(subgroup,group,overwrite=False):
#     
#     if subgroup not in group.keys():
#         grp = group.create_group(subgroup)
#     elif overwrite:
#         del group[subgroup]
#         grp = group.create_group(subgroup)
#     else:
#         grp = group[subgroup]
#         
#     return grp    




def build_datapath_list(xrmmap):

    det_list = build_detector_list(xrmmap)
    data_list = []

    def find_detector(group):

        sub_list = []
        if 'counts' in group.keys():
            sub_list += [group['counts'].name]
        elif 'scal' in group.name:
            for key,val in dict(group).iteritems():
                sub_list += [group[key].name]
        return sub_list

    for det in det_list:
        for idet in find_detector(xrmmap[det]):
            data_list += [idet]

    return data_list


def build_detector_list(group):

    det_list = []
    for key in group.keys():
        try:
            is_det = bytes2str(group[key].attrs.get('type', '')).find('det') > -1
            if not is_det:
               is_det = bytes2str(group[key].attrs.get('type', '')).find('mca') > -1
        except:
            is_det = False
        if is_det and key not in det_list:
            det_list += [key]
    det_list = sorted(det_list)
            
    for i,det in enumerate(det_list):
        if 'sum' in det.lower():
            det_list = [det_list[i]] + det_list[:i] + det_list[i+1:]

    return det_list

class GSEXRM_Exception(Exception):
    '''GSEXRM Exception: General Errors'''
    pass

class GSEXRM_MapRow:
    '''
    read one row worth of data:
    '''
    def __init__(self, yvalue, xrffile, xrdfile, xpsfile, sisfile, folder,
                 reverse=None, ixaddr=0, dimension=2, ioffset=0,
                 npts=None,  irow=None, dtime=None, nrows_expected=None,
                 masterfile=None, xrftype=None, xrdtype=None,
                 xrdcal=None, xrd2dmask=None, xrd2dbkgd=None,
                 wdg=0, steps=STEPS, flip=True,
                 FLAGxrf=True, FLAGxrd2D=False, FLAGxrd1D=False):

        self.read_ok = False
        self.nrows_expected = nrows_expected

        ioff = ioffset
        offslice = slice(None, None, None)
        if ioff > 0:
            offslice = slice(ioff, None, None)
        elif ioff < 0:
            offslice = slice(None, ioff, None)

        self.npts = npts
        self.irow = irow
        self.yvalue  = yvalue
        self.xrffile = xrffile
        self.xpsfile = xpsfile
        self.sisfile = sisfile
        self.xrdfile = xrdfile

        self.xrd2d     = None
        self.xrdq      = None
        self.xrd1d     = None
        self.xrdq_wdg  = None
        self.xrd1d_wdg = None
        
        if masterfile is not None:
            header, rows = readMasterFile(masterfile)
            for row in header:
                if row.startswith('#XRF.filetype'): xrftype = row.split()[-1]
                if row.startswith('#XRD.filetype'): xrdtype = row.split()[-1]

        if FLAGxrf:
            if xrftype is None:
                xrftype = 'netcdf'
                if xrffile.startswith('xsp3'):
                    xrftype = 'hdf5'
            if xrftype == 'netcdf':
                xrf_reader = read_xrf_netcdf
            else:
                xrf_reader = read_xsp3_hdf5

        if FLAGxrd2D or FLAGxrd1D:
            if xrdtype == 'hdf5':
                xrd_reader = read_xrd_hdf5
            elif xrdtype == 'netcdf' or xrdfile.endswith('nc'):
                xrd_reader = read_xrd_netcdf
            else:
                xrd_reader = read_xrd_netcdf


        # reading can fail with IOError, generally meaning the file isn't
        # ready for read.  Try again for up to 5 seconds
        t0 = time.time()
        sis_ok, xps_ok = False, False

        gdata, sdata = [], []
        while not (sis_ok and xps_ok):
            try:
                ghead, gdata = readASCII(os.path.join(folder, xpsfile))
                xps_ok = len(gdata) > 1
            except IOError:
                if (time.time() - t0) > 5.0:
                    break
                time.sleep(0.25)
            try:
                shead, sdata = readASCII(os.path.join(folder, sisfile))
                sdata = sdata[offslice]
                sis_ok = len(sdata) > 1
            except IOError:
                if (time.time() - t0) > 5.0:
                    break
                time.sleep(0.25)

        if not(sis_ok and xps_ok):
            print('Failed to read ASCII data for SIS: %s (%i), XPS: %s (%i)' %
                     (sisfile, len(sdata), xpsfile, len(gdata)) )
            return

        self.sishead = shead
        if dtime is not None:  dtime.add('maprow: read ascii files')
        t0 = time.time()

        atime = -1

        xrf_dat,xrf_file = None,os.path.join(folder, xrffile)
        xrd_dat,xrd_file = None,os.path.join(folder, xrdfile)

        while atime < 0 and time.time()-t0 < 10:
            try:
                atime = os.stat(os.path.join(folder, sisfile)).st_ctime
                if FLAGxrf:
                    xrf_dat = xrf_reader(xrf_file, npixels=self.nrows_expected, verbose=False)
                    if xrf_dat is None:
                        print( 'Failed to read XRF data from %s' % self.xrffile)
                if FLAGxrd2D or FLAGxrd1D:
                    xrd_dat = xrd_reader(xrd_file, verbose=False)
                    if xrd_dat is None:
                        print( 'Failed to read XRD data from %s' % self.xrdfile)

            except (IOError, IndexError):
                time.sleep(0.010)

        if atime < 0:
            print( 'Failed to read data.')
            return
        if dtime is not None:
            dtime.add('maprow: read XRM files')

        ## SPECIFIC TO XRF data
        if FLAGxrf:
            self.counts    = xrf_dat.counts[offslice]
            self.inpcounts = xrf_dat.inputCounts[offslice]
            self.outcounts = xrf_dat.outputCounts[offslice]

            # times are extracted from the netcdf file as floats of ms
            # here we truncate to nearest ms (clock tick is 0.32 ms)
            self.livetime  = (xrf_dat.liveTime[offslice]).astype('int')
            self.realtime  = (xrf_dat.realTime[offslice]).astype('int')

            dt_denom = xrf_dat.outputCounts[offslice]*xrf_dat.liveTime[offslice]
            dt_denom[np.where(dt_denom < 1)] = 1.0
            self.dtfactor  = xrf_dat.inputCounts[offslice]*xrf_dat.realTime[offslice]/dt_denom

        ## SPECIFIC TO XRD data
        if FLAGxrd2D or FLAGxrd1D:
            if self.npts == xrd_dat.shape[0]:
                self.xrd2d = xrd_dat
            elif self.npts > xrd_dat.shape[0]:
                self.xrd2d = np.zeros((self.npts,xrd_dat.shape[1],xrd_dat.shape[2]))
                self.xrd2d[0:xrd_dat.shape[0]] = xrd_dat
            else:
                self.xrd2d = xrd_dat[0:self.npts]

            ############################################################################
            ## subtracts background and applies mask, row by row
            ## mkak 2018.02.01 
            ## major speed up if no background or mask specified
            ## updated mkak 2018.03.30
            
            if xrd2dmask is not None:
                dir = -1 if flip else 1
                mask2d = np.ones(self.xrd2d[0].shape)
                mask2d = mask2d - xrd2dmask[::dir]
                if xrd2dbkgd is not None:
                    self.xrd2d = mask2d*(self.xrd2d-xrd2dbkgd)
                else:
                    self.xrd2d = mask2d*(self.xrd2d)
            elif xrd2dbkgd is not None:
                self.xrd2d = self.xrd2d-xrd2dbkgd
            
            ## limits all values to positive
            self.xrd2d[self.xrd2d < 0] = 0
            ############################################################################

            if xrdcal is not None and FLAGxrd1D:
                attrs = {'steps':steps,'flip':flip}

                self.xrdq,self.xrd1d = integrate_xrd_row(self.xrd2d,xrdcal,**attrs)

                if wdg > 1:
                    self.xrdq_wdg,self.xrd1d_wdg = [],[]
                    wdg_sz = 360./int(wdg)
                    for iwdg in range(wdg):
                        wdg_lmts = np.array([iwdg*wdg_sz, (iwdg+1)*wdg_sz]) - 180

                        attrs.update({'wedge_limits':wdg_lmts})
                        q,counts = integrate_xrd_row(self.xrd2d,xrdcal,**attrs)
                        self.xrdq_wdg  += [q]
                        self.xrd1d_wdg += [counts]

                    self.xrdq_wdg  = np.einsum('kij->ijk', self.xrdq_wdg)
                    self.xrd1d_wdg = np.einsum('kij->ijk', self.xrd1d_wdg)

        gnpts, ngather  = gdata.shape
        snpts, nscalers = sdata.shape

        xnpts,nmca = gnpts,1
        if FLAGxrf:
            xnpts, nmca, nchan = self.counts.shape

        if self.npts is None:
            self.npts = min(gnpts, xnpts)

        # print("Row ", sisfile, snpts, self.npts)

        if snpts < self.npts:  # extend struck data if needed
            print('     extending SIS data from %i to %i !' % (snpts, self.npts))
            sdata = list(sdata)
            for i in range(self.npts+1-snpts):
                sdata.append(sdata[snpts-1])
            sdata = np.array(sdata)
            snpts = self.npts
        self.sisdata = sdata[:self.npts]

        if xnpts > self.npts:
            if FLAGxrf:
                self.counts    = self.counts[:self.npts]
                self.realtime  = self.realtime[:self.npts]
                self.livetime  = self.livetime[:self.npts]
                self.dtfactor  = self.dtfactor[:self.npts]
                self.inpcounts = self.inpcounts[:self.npts]
                self.outcounts = self.outcounts[:self.npts]
            if FLAGxrd2D:
                self.xrd2d = self.xrd2d[:self.npts]
            if FLAGxrd1D:
                self.xrdq,self.xrd1d = self.xrdq[:self.npts],self.xrd1d[:self.npts]
                if self.xrdq_wdg is not None:
                    self.xrdq_wdg    = self.xrdq_wdg[:self.npts]
                    self.xrd1d_wdg   = self.xrd1d_wdg[:self.npts]

        points = list(range(1, self.npts+1))
        # auto-reverse: counter-intuitively (because stage is upside-down and so
        # backwards wrt optical view), left-to-right scans from high to low value
        # so reverse those that go from low to high value
        if reverse is None:
            reverse = gdata[0, 0] < gdata[-1, 0]

        if reverse:
            points.reverse()
            self.sisdata  = self.sisdata[::-1]
            if FLAGxrf:
                self.counts  = self.counts[::-1]
                self.realtime = self.realtime[::-1]
                self.livetime = self.livetime[::-1]
                self.dtfactor = self.dtfactor[::-1]
                self.inpcounts= self.inpcounts[::-1]
                self.outcounts= self.outcounts[::-1]
            if FLAGxrd2D:
                self.xrd2d = self.xrd2d[::-1]
            if FLAGxrd1D:
                self.xrdq,self.xrd1d = self.xrdq[::-1],self.xrd1d[::-1]
                if self.xrdq_wdg is not None:
                    self.xrdq_wdg        = self.xrdq_wdg[::-1]
                    self.xrd1d_wdg       = self.xrd1d_wdg[::-1]

        if FLAGxrf:
            xvals = [(gdata[i, ixaddr] + gdata[i-1, ixaddr])/2.0 for i in points]
            self.posvals = [np.array(xvals)]
            if dimension == 2:
                self.posvals.append(np.array([float(yvalue) for i in points]))
            self.posvals.append(self.realtime.sum(axis=1).astype('float32') / nmca)
            self.posvals.append(self.livetime.sum(axis=1).astype('float32') / nmca)
            total = None
            for imca in range(nmca):
                dtcorr = self.dtfactor[:, imca].astype('float32')
                cor   = dtcorr.reshape((dtcorr.shape[0], 1))
                if total is None:
                    total = self.counts[:, imca, :] * cor
                else:
                    total = total + self.counts[:, imca, :] * cor

            self.total = total.astype('int16')
            self.dtfactor = self.dtfactor.astype('float32')
            self.dtfactor = self.dtfactor.transpose()
            self.inpcounts= self.inpcounts.transpose()
            self.outcounts= self.outcounts.transpose()
            self.livetime = self.livetime.transpose()
            self.realtime = self.realtime.transpose()
            self.counts   = self.counts.swapaxes(0, 1)

        self.read_ok = True

class GSEMCA_Detector(object):
    '''Detector class, representing 1 detector element (real or virtual)
    has the following properties (many of these as runtime-calculated properties)

    rois           list of ROI objects
    rois[i].name        names
    rois[i].address     address
    rois[i].left        index of lower limit
    rois[i].right       index of upper limit
    energy         array of energy values
    counts         array of count values
    dtfactor       array of deadtime factor
    realtime       array of real time
    livetime       array of live time
    inputcounts    array of input counts
    outputcount    array of output count

    '''
    def __init__(self, xrmmap, index=None):
        self.xrmmap = xrmmap
        self.__ndet =  xrmmap.attrs.get('N_Detectors',0)
        self.det = None
        self.rois = []
        detname = 'det1'
        if index is not None:
            self.det = self.xrmmap['det%i' % index]
            detname = 'det%i' % index

        self.shape =  self.xrmmap['%s/livetime' % detname].shape

        # energy
        self.energy = self.xrmmap['%s/energy' % detname].value

        # set up rois
        rnames = self.xrmmap['%s/roi_names' % detname].value
        raddrs = self.xrmmap['%s/roi_addrs' % detname].value
        rlims  = self.xrmmap['%s/roi_limits' % detname].value
        for name, addr, lims in zip(rnames, raddrs, rlims):
            self.rois.append(ROI(name=name, address=addr,
                                 left=lims[0], right=lims[1]))

    def __getval(self, param):
        if self.det is None:
            out = self.xrmmap['det1/%s' % (param)].value
            for i in range(2, self.__ndet):
                out += self.xrmmap['det%i/%s' % (i, param)].value
            return out
        return self.det[param].value

    @property
    def counts(self):
        "detector counts array"
        return self.__getval('counts')

    @property
    def dtfactor(self):
        '''deadtime factor'''
        return self.__getval('dtfactor')

    @property
    def realtime(self):
        '''real time'''
        return self.__getval('realtime')

    @property
    def livetime(self):
        '''live time'''
        return self.__getval('livetime')

    @property
    def inputcounts(self):
        '''inputcounts'''
        return self.__getval('inputcounts')

    @property
    def outputcount(self):
        '''output counts'''
        return self.__getval('outputcounts')


class GSEXRM_Area(object):
    '''Map Area class, representing a map area for a detector
    '''
    def __init__(self, xrmmap, index, det=None):
        self.xrmmap = xrmmap
        self.det = GSEMCA_Detector(xrmmap, index=det)
        if isinstance(index, int):
            index = 'area_%3.3i' % index
        self._area = self.xrmmap['areas/%s' % index]
        self.npts = self._area.value.sum()

        sy, sx = [slice(min(_a), max(_a)+1) for _a in np.where(self._area)]
        self.yslice, self.xslice = sy, sx

    def roicounts(self, roiname):
        iroi = -1
        for ir, roi in enumerate(self.det.rois):
            if roiname.lower() == roi.name.lower():
                iroi = ir
                break
        if iroi < 0:
            raise ValueError('ROI name %s not found' % roiname)
        elo, ehi = self.det.rois[iroi].left, self.det.rois[iroi].right
        counts = self.det.counts[self.yslice, self.xslice, elo:ehi]


class GSEXRM_MapFile(object):
    '''
    Access to GSECARS X-ray Microprobe Map File:

    The GSEXRM Map file is an HDF5 file built from a folder containing
    'raw' data from a set of sources
         xmap:   XRF spectra saved to NetCDF by the Epics MCA detector
         struck: a multichannel scaler, saved as ASCII column data
         xps:    stage positions, saved as ASCII file from the Newport XPS

    The object here is intended to expose an HDF5 file that:
         a) watches the corresponding folder and auto-updates when new
            data is available, as for on-line collection
         b) stores locking information (Machine Name/Process ID) in the top-level

    For extracting data from a GSEXRM Map File, use:

    >>> from epicscollect.io import GSEXRM_MapFile
    >>> map = GSEXRM_MapFile('MyMap.001')
    >>> fe  = map.get_roimap('Fe', det='mca2')
    >>> as  = map.get_roimap('As Ka', det='mca1', dtcorrect=True)
    >>> rgb = map.get_rgbmap('Fe', 'Ca', 'Zn', dtcorrect=True, scale_each=False)
    >>> en  = map.get_energy(det=1)

    All these take the following options:

       det:         which detector element to use (1, 2, 3, 4, None), [None]
                    None means to use the sum of all detectors
       dtcorrect:   whether to return dead-time corrected spectra     [True]

    '''

    ScanFile   = 'Scan.ini'
    EnvFile    = 'Environ.dat'
    ROIFile    = 'ROI.dat'
    MasterFile = 'Master.dat'

    def __init__(self, filename=None, folder=None, root=None, chunksize=None,
                 xrdcal=None, xrd2dmask=None, xrd2dbkgd=None, xrd1dbkgd=None,
                 azwdgs=0, qstps=STEPS, flip=True, bkgdscale=1.,
                 FLAGxrf=True, FLAGxrd1D=False, FLAGxrd2D=False,
                 compression=COMPRESSION, compression_opts=COMPRESSION_OPTS,
                 facility='APS', beamline='13-ID-E',run='',proposal='',user=''):

        self.filename         = filename
        self.folder           = folder
        self.root             = root
        self.chunksize        = chunksize
        self.status           = GSEXRM_FileStatus.err_notfound
        self.dimension        = None
        self.ndet             = None
        self.start_time       = None
        self.xrmmap           = None
        self.h5root           = None
        self.last_row         = -1
        self.rowdata          = []
        self.npts             = None
        self.roi_slices       = None
        self._pixeltime       = None
        self.masterfile       = None
        self.masterfile_mtime = -1
        self.compress_args = {'compression': compression}
        if compression != 'lzf':
            self.compress_args['compression_opts'] = compression_opts

        self.mono_energy  = None
        self.flag_xrf     = FLAGxrf
        self.flag_xrd1d   = FLAGxrd1D
        self.flag_xrd2d   = FLAGxrd2D

        ## used for XRD
        self.bkgd_xrd2d     = None
        self.bkgd_xrd1d     = None
        self.mask_xrd2d     = None
        self.xrdcalfile     = None
        self.xrd2dmaskfile  = None
        self.xrd2dbkgdfile  = None
        self.xrd1dbkgdfile  = None

        self.bkgdscale = bkgdscale if bkgdscale > 0 else 1.
        
        self.azwdgs      = 0 if azwdgs > 36 or azwdgs < 2 else int(azwdgs)
        self.qstps       = int(qstps)
        self.flip        = flip

        ## used for tomography orientation
        self.x           = None
        self.ome         = None
        self.reshape     = None

        self.notes = {'facility'   : facility,
                      'beamline'   : beamline,
                      'run'        : run,
                      'proposal'   : proposal,
                      'user'       : user}

        # initialize from filename or folder
        if self.filename is not None:

            self.status,self.root,self.version = getFileStatus(self.filename, root=root)
            # see if file contains name of folder
            # (signifies "read from folder")
            if self.status == GSEXRM_FileStatus.empty:
                ftmp = open(self.filename, 'r')
                self.folder = ftmp.readlines()[0][:-1].strip()
                if '/' in self.folder:
                    self.folder = self.folder.split('/')[-1]
                ftmp.close()
                os.unlink(self.filename)

        if isGSEXRM_MapFolder(self.folder):
            self.read_master()
            if self.filename is None:
                raise GSEXRM_Exception(
                    "'%s' is not a valid GSEXRM Map folder" % self.folder)
            self.status, self.root, self.version = \
                getFileStatus(self.filename, root=root,
                              folder=self.folder)

        # for existing file, read initial settings
        if self.status in (GSEXRM_FileStatus.hasdata,
                           GSEXRM_FileStatus.created):
            self.open(self.filename, root=self.root, check_status=False)
            self.reset_flags()
            return

        # file exists but is not hdf5
        if self.status ==  GSEXRM_FileStatus.err_nothdf5:
            raise GSEXRM_Exception(
                "'%s' is not a readable HDF5 file" % self.filename)

        # create empty HDF5 if needed
        if self.status == GSEXRM_FileStatus.empty and os.path.exists(self.filename):
            try:
                flines = open(self.filename, 'r').readlines()
                if len(flines) < 3:
                    os.unlink(self.filename)
                self.status =  GSEXRM_FileStatus.err_notfound
            except (IOError, ValueError):
                pass
        if (self.status in (GSEXRM_FileStatus.err_notfound,
                            GSEXRM_FileStatus.wrongfolder) and
            self.folder is not None and isGSEXRM_MapFolder(self.folder)):

            self.read_master()
            if self.status == GSEXRM_FileStatus.wrongfolder:
                self.filename = new_filename(self.filename)
                cfile = FastMapConfig()
                cfile.Read(os.path.join(self.folder, self.ScanFile))
                cfile.config['scan']['filename'] = self.filename
                # cfile.Save(os.path.join(self.folder, self.ScanFile))
            self.h5root = h5py.File(self.filename)

            if self.dimension is None and isGSEXRM_MapFolder(self.folder):
                self.read_master()
            create_xrmmap(self.h5root, root=self.root, dimension=self.dimension,
                          folder=self.folder, start_time=self.start_time)

            self.notes['h5_create_time'] = isotime(time.time())

            self.status = GSEXRM_FileStatus.created
            self.open(self.filename, root=self.root, check_status=False)

            for xkey,xval in zip(self.xrmmap.attrs.keys(),self.xrmmap.attrs.values()):
                if xkey == 'Version': self.version = xval

            self.add_XRDfiles(xrdcalfile=xrdcal,
                              xrd2dmaskfile=xrd2dmask,
                              xrd2dbkgdfile=xrd2dbkgd,
                              xrd1dbkgdfile=xrd1dbkgd)
        else:
            raise GSEXRM_Exception('GSEXMAP Error: could not locate map file or folder')

    def __repr__(self):
        fname = ''
        if self.filename is not None:
            fpath, fname = os.path.split(self.filename)
        return "GSEXRM_MapFile('%s')" % fname

    def get_det(self, index):
        return GSEMCA_Detector(self.xrmmap, index=index)

    def area_obj(self, index, det=None):
        return GSEXRM_Area(self.xrmmap, index, det=det)

    def get_scanconfig(self):
        '''return scan configuration from file'''
        conftext = self.xrmmap['config/scan/text'].value
        return FastMapConfig(conftext=conftext)

    def get_coarse_stages(self):
        '''return coarse stage positions for map'''
        stages = []
        env_addrs = [h5str(s) for s in self.xrmmap['config/environ/address']]
        env_vals  = [h5str(s) for s in self.xrmmap['config/environ/value']]
        for addr, pname in self.xrmmap['config/positioners'].items():
            name = h5str(pname.value)
            addr = h5str(addr)
            val = ''
            if not addr.endswith('.VAL'):
                addr = '%s.VAL' % addr
            if addr in env_addrs:
                val = env_vals[env_addrs.index(addr)]

            stages.append((addr, val, name))

        return stages

    def open(self, filename, root=None, check_status=True):
        '''open GSEXRM HDF5 File :
        with check_status=False, this **must** be called
        for an existing, valid GSEXRM HDF5 File!!
        '''
        if root in ('', None):
            root = DEFAULT_ROOTNAME
        if check_status:
            self.status, self.root, self.version = \
                         getFileStatus(filename, root=root)
            if self.status not in (GSEXRM_FileStatus.hasdata,
                                   GSEXRM_FileStatus.created):
                raise GSEXRM_Exception(
                    "'%s' is not a valid GSEXRM HDF5 file" % self.filename)
        self.filename = filename
        if self.h5root is None:
            self.h5root = h5py.File(self.filename)
        self.xrmmap = self.h5root[root]
        if self.folder is None:
            self.folder = bytes2str(self.xrmmap.attrs.get('Map_Folder',''))
        self.last_row = int(self.xrmmap.attrs.get('Last_Row',0))

        try:
            self.dimension = self.xrmmap['config/scan/dimension'].value
        except:
            pass

        if (len(self.rowdata) < 1 or
            (self.dimension is None and isGSEXRM_MapFolder(self.folder))):
            self.read_master()
            
        if self.ndet is None:
            self.ndet = self.xrmmap.attrs.get('N_Detectors', None)

    def close(self):
        if self.check_hostid():
            self.xrmmap.attrs['Process_Machine'] = ''
            self.xrmmap.attrs['Process_ID'] = 0
            self.xrmmap.attrs['Last_Row'] = self.last_row
        self.h5root.close()
        self.h5root = None

    def add_XRDfiles(self, flip=None, xrdcalfile=None, xrd2dmaskfile=None,
                     xrd2dbkgdfile=None, xrd1dbkgdfile=None):
        '''
        adds mask file to exisiting '/xrmmap' group in an open HDF5 file
        mkak 2018.02.01
        '''

        xrd1Dgrp = ensure_subgroup('xrd1D',self.xrmmap)

        if xrdcalfile is not None:
            self.xrdcalfile = xrdcalfile
        if os.path.exists(str(self.xrdcalfile)):
            print('Calibration file loaded: %s' % self.xrdcalfile)
            xrd1Dgrp.attrs['calfile'] = str(self.xrdcalfile)
            

        self.flip = flip if flip is not None else self.flip

        if xrd1dbkgdfile is not None:
            self.xrd1dbkgdfile= xrd1dbkgdfile
        if os.path.exists(str(self.xrd1dbkgdfile)):
            print('1DXRD background file loaded: %s' % self.xrd1dbkgdfile)
            xrd1Dgrp.attrs['1Dbkgdfile'] = '%s' % (self.xrd1dbkgdfile)
            self.bkgd_xrd1d = read_xrd_data(self.xrd1dbkgdfile)*self.bkgdscale

        if xrd2dbkgdfile is not None:
            self.xrd2dbkgdfile= xrd2dbkgdfile
        if os.path.exists(str(self.xrd2dbkgdfile)):
            print('2DXRD background file loaded: %s' % self.xrd2dbkgdfile)
            xrd1Dgrp.attrs['2Dbkgdfile'] = '%s' % (self.xrd2dbkgdfile)
            self.bkgd_xrd2d = read_xrd_data(self.xrd2dbkgdfile)*self.bkgdscale

        if xrd2dmaskfile is not None:
            self.xrd2dmaskfile= xrd2dmaskfile
        if os.path.exists(str(self.xrd2dmaskfile)):
            print('Mask file loaded: %s' % self.xrd2dmaskfile)
            xrd1Dgrp.attrs['maskfile'] = '%s' % (self.xrd2dmaskfile)
            self.mask_xrd2d = read_xrd_data(self.xrd2dmaskfile)

        self.h5root.flush()

    def add_data(self, group, name, data, attrs=None, **kws):
        ''' creata an hdf5 dataset'''
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        kws.update(self.compress_args)
        d = group.create_dataset(name, data=data, **kws)
        if isinstance(attrs, dict):
            for key, val in attrs.items():
                d.attrs[key] = val
        return d

    def add_map_config(self, config):
        '''add configuration from Map Folder to HDF5 file
        ROI, DXP Settings, and Config data
        '''
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        group = self.xrmmap['config']
        scantext = open(os.path.join(self.folder, self.ScanFile), 'r').read()
        for name, sect in (('scan', 'scan'),
                           ('general', 'general'),
                           ('positioners', 'slow_positioners'),
                           ('motor_controller', 'xps')):
            for key, val in config[sect].items():
                group[name].create_dataset(key, data=val)

        group['scan'].create_dataset('text', data=scantext)

        roifile = os.path.join(self.folder, self.ROIFile)
        self.ndet = 0
        if os.path.exists(roifile):
            roidat, calib, extra = readROIFile(roifile)
            self.ndet = len(calib['slope'])
            self.xrmmap.attrs['N_Detectors'] = self.ndet
            roi_desc, roi_addr, roi_lim = [], [], []
            roi_slices = []

            for iroi, label, lims in roidat:
                roi_desc.append(label)
                roi_addr.append("%smca%%i.R%i" % (config['xrf']['prefix'], iroi))
                roi_lim.append([lims[i] for i in range(self.ndet)])
                roi_slices.append([slice(lims[i][0], lims[i][1]) for i in range(self.ndet)])
            roi_lim = np.array(roi_lim)

            self.add_data(group['rois'], 'name',     [six.b(a) for a in roi_desc])
            self.add_data(group['rois'], 'address',  [six.b(a) for a in roi_addr])
            self.add_data(group['rois'], 'limits',   roi_lim)

            for key, val in calib.items():
                self.add_data(group['mca_calib'], key, val)

            for key, val in extra.items():
                self.add_data(group['mca_settings'], key, val)

            self.roi_desc = roi_desc
            self.roi_addr = roi_addr
            self.roi_slices = roi_slices
            self.calib = calib
        # add env data
        envdat = readEnvironFile(os.path.join(self.folder, self.EnvFile))
        env_desc, env_addr, env_val = parseEnviron(envdat)

        self.add_data(group['environ'], 'name',     [six.b(a) for a in env_desc])
        self.add_data(group['environ'], 'address',  [six.b(a) for a in env_addr])
        self.add_data(group['environ'], 'value',    [six.b(a) for a  in env_val])

        cmprstr = '%s' % self.compress_args['compression']
        if self.compress_args['compression'] != 'lzf':
            cmprstr = '%s-%s' % (cmprstr,self.compress_args['compression_opts'])
        self.xrmmap.attrs['Compression'] = cmprstr

        self.h5root.flush()

    def initialize_xrmmap(self, callback=None):
        ''' initialize '/xrmmap' group in HDF5 file, generally
        possible once at least 1 row of raw data is available
        in the scan folder.
        '''
        self.starttime = time.time()
        if self.status == GSEXRM_FileStatus.hasdata:
            return
        if self.status != GSEXRM_FileStatus.created:
            print( 'Warning, cannot initialize xrmmap yet.')
            return

        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        if (len(self.rowdata) < 1 or
            (self.dimension is None and isGSEXRM_MapFolder(self.folder))):
            self.read_master()
        if len(self.rowdata) < 1:
            return

        self.last_row = -1
        self.add_map_config(self.mapconf)

        self.process_row(0, flush=True, callback=callback)

        self.status = GSEXRM_FileStatus.hasdata

    def process_row(self, irow, flush=False, callback=None):

        row = self.read_rowdata(irow)

        if irow == 0:
            self.build_schema(row,verbose=True)

        if row.read_ok:
            self.add_rowdata(row, callback=callback)

        if flush:
            self.resize_arrays(self.last_row+1)
            self.h5root.flush()
            if self._pixeltime is None:
                self.calc_pixeltime()

            if hasattr(callback, '__call__'):
                callback(filename=self.filename, status='complete')
        
    def process(self, maxrow=None, force=False, callback=None):
        "look for more data from raw folder, process if needed"

        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        self.reset_flags()
        if self.status == GSEXRM_FileStatus.created:
            self.initialize_xrmmap(callback=callback)
        if (force or len(self.rowdata) < 1 or
            (self.dimension is None and isGSEXRM_MapFolder(self.folder))):
            self.read_master()

        nrows = len(self.rowdata)
        if maxrow is not None:
            nrows = min(nrows, maxrow)

        if force or self.folder_has_newdata():
            irow = self.last_row + 1
            while irow < nrows:
                self.process_row(irow, flush=(nrows-irow<=1), callback=callback)
                irow  = irow + 1

        print(datetime.datetime.fromtimestamp(time.time()).strftime('End: %Y-%m-%d %H:%M:%S'))

    def calc_pixeltime(self):
        scanconf = self.xrmmap['config/scan']
        rowtime = float(scanconf['time1'].value)
        start = float(scanconf['start1'].value)
        stop = float(scanconf['stop1'].value)
        step = float(scanconf['step1'].value)
        npts = int((abs(stop - start) + 1.1*step)/step)
        self._pixeltime = rowtime/(npts-1)
        return self._pixeltime

    @property
    def pixeltime(self):
        """Return the pixel time"""
        if self._pixeltime is None:
            self.calc_pixeltime()
        return self._pixeltime

    def read_rowdata(self, irow, offset=None):
        '''read a row worth of raw data from the Map Folder
        returns arrays of data
        '''

        if self.xrdcalfile is None:
            self.xrdcalfile = bytes2str(self.xrmmap['xrd1D'].attrs.get('calfile',''))

        if self.dimension is None or irow > len(self.rowdata):
            self.read_master()

        if self.folder is None or irow >= len(self.rowdata):
            return

        scan_version = getattr(self, 'scan_version', 1.00)

        # if not self.flag_xrf and not self.flag_xrd2d and not self.flag_xrd1d:
        #    raise IOError('No XRF or XRD flags provided.')
        #    return

        if scan_version > 1.35 or self.flag_xrd2d or self.flag_xrd1d:
            yval, xrff, sisf, xpsf, xrdf, etime = self.rowdata[irow]


            if xrff.startswith('None'):
                xrff = xrff.replace('None', 'xsp3')
            if sisf.startswith('None'):
                sisf = sisf.replace('None', 'struck')
            if xpsf.startswith('None'):
                xpsf = xpsf.replace('None', 'xps')
            if xrdf.startswith('None'):
                xrdf = xrdf.replace('None', 'pexrd')
        else:
            yval, xrff, sisf, xpsf, etime = self.rowdata[irow]
            xrdf = '_unused_'

        if '_unused_' in xrdf:
            self.flag_xrd1d = False
            self.flag_xrd2d = False

        if '_unused_' in xrff:
            self.flag_xrf = False

        reverse = None # (irow % 2 != 0)

        ioffset = 0
        if scan_version > 1.35:
            ioffset = 1
        if offset is not None:
            ioffset = offset
        self.flag_xrf = self.flag_xrf and xrff != '_unused_'
        return GSEXRM_MapRow(yval, xrff, xrdf, xpsf, sisf, self.folder,
                             irow=irow, nrows_expected=self.nrows_expected,
                             ixaddr=self.ixaddr, dimension=self.dimension,
                             npts=self.npts, reverse=reverse, ioffset=ioffset,
                             masterfile=self.masterfile, flip=self.flip,
                             xrdcal=self.xrdcalfile, xrd2dmask=self.mask_xrd2d,
                             xrd2dbkgd = self.bkgd_xrd2d,
                             wdg=self.azwdgs, steps=self.qstps,
                             FLAGxrf=self.flag_xrf, FLAGxrd2D=self.flag_xrd2d,
                             FLAGxrd1D=self.flag_xrd1d)


    def add_rowdata(self, row, callback=None):
        '''adds a row worth of real data'''

        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        thisrow = self.last_row + 1

        if hasattr(callback, '__call__'):
            callback(row=(thisrow+1), maxrow=len(self.rowdata), filename=self.filename)

        pform = 'Add row %4i, yval=%s' % (thisrow+1, row.yvalue)
        if self.flag_xrf:
            pform = '%s, xrffile=%s' % (pform,row.xrffile)
        if self.flag_xrd2d or self.flag_xrd1d:
            pform = '%s, xrdfile=%s' % (pform,row.xrdfile)
        print(pform)

        if version_ge(self.version, '2.0.0'):

            mcasum_raw,mcasum_cor = [],[]
            nrows = 0
            map_items = sorted(self.xrmmap.keys())
            for gname in map_items:
                g = self.xrmmap[gname]
                if bytes2str(g.attrs.get('type', None)) == 'scalar detectors':
                    first_det = list(g.keys())[0]
                    nrows, npts =  g[first_det].shape

            if thisrow >= nrows:
                self.resize_arrays(NINIT*(1+nrows/NINIT))

            sclrgrp = self.xrmmap['scalars']
            for ai,aname in enumerate(re.findall(r"[\w']+", row.sishead[-1])):
                sclrgrp[aname][thisrow,  :npts] = row.sisdata[:npts].transpose()[ai]

            if self.flag_xrf:

                npts = min([len(p) for p in row.posvals])
                pos    = self.xrmmap['positions/pos']
                rowpos = np.array([p[:npts] for p in row.posvals])

                tpos = rowpos.transpose()
                pos[thisrow, :npts, :] = tpos[:npts, :]
                nmca, xnpts, nchan = row.counts.shape
                mca_dets = []

                for gname in map_items:
                    g = self.xrmmap[gname]
                    if bytes2str(g.attrs.get('type', None)) == 'mca detector':
                        mca_dets.append(gname)
                        nrows, npts, nchan =  g['counts'].shape

                _nr, npts, nchan = self.xrmmap[mca_dets[0]]['counts'].shape
                npts = min(npts, xnpts, self.npts)
                for idet, gname in enumerate(mca_dets):
                    grp = self.xrmmap[gname]
                    grp['counts'][thisrow, :npts, :] = row.counts[idet, :npts, :]
                    grp['dtfactor'][thisrow,  :npts] = row.dtfactor[idet, :npts]
                    grp['realtime'][thisrow,  :npts] = row.realtime[idet, :npts]
                    grp['livetime'][thisrow,  :npts] = row.livetime[idet, :npts]
                    grp['inpcounts'][thisrow, :npts] = row.inpcounts[idet, :npts]
                    grp['outcounts'][thisrow, :npts] = row.outcounts[idet, :npts]
                self.xrmmap['mcasum']['counts'][thisrow, :npts, :nchan] = row.total[:npts, :nchan]
                roigrp = self.xrmmap['roimap']

                en  = self.xrmmap['mcasum']['energy'][:]
                for roiname in roigrp['mcasum'].keys():
                    en_lim = roigrp['mcasum'][roiname]['limits'][:]
                    roi_slice = slice(np.abs(en-en_lim[0]).argmin(),
                                      np.abs(en-en_lim[1]).argmin())
                    sumraw = roigrp['mcasum'][roiname]['raw'][thisrow,]
                    sumcor = roigrp['mcasum'][roiname]['cor'][thisrow,]
                    for detname in mca_dets:
                        mcaraw = self.xrmmap[detname]['counts'][thisrow,][:,roi_slice].sum(axis=1)
                        mcacor = mcaraw*self.xrmmap[detname]['dtfactor'][thisrow,]
                        roigrp[detname][roiname]['raw'][thisrow,] = mcaraw
                        roigrp[detname][roiname]['cor'][thisrow,] = mcacor
                        sumraw += mcaraw
                        sumcor += mcacor
                    roigrp['mcasum'][roiname]['raw'][thisrow,] = sumraw
                    roigrp['mcasum'][roiname]['cor'][thisrow,] = sumcor


        else:
            if self.flag_xrf:
                nmca, xnpts, nchan = row.counts.shape
                xrm_dets = []

                nrows = 0
                map_items = sorted(self.xrmmap.keys())
                for gname in map_items:
                    g = self.xrmmap[gname]
                    if bytes2str(g.attrs.get('type', None)) == 'mca detector':
                        xrm_dets.append(g)
                        nrows, npts, nchan =  g['counts'].shape

                if thisrow >= nrows:
                    self.resize_arrays(NINIT*(1+nrows/NINIT))

                _nr, npts, nchan = xrm_dets[0]['counts'].shape
                npts = min(npts, xnpts, self.npts)
                for idet, grp in enumerate(xrm_dets):
                    grp['dtfactor'][thisrow,  :npts] = row.dtfactor[idet, :npts]
                    grp['realtime'][thisrow,  :npts] = row.realtime[idet, :npts]
                    grp['livetime'][thisrow,  :npts] = row.livetime[idet, :npts]
                    grp['inpcounts'][thisrow, :npts] = row.inpcounts[idet, :npts]
                    grp['outcounts'][thisrow, :npts] = row.outcounts[idet, :npts]
                    grp['counts'][thisrow, :npts, :] = row.counts[idet, :npts, :]

                # here, we add the total dead-time-corrected data to detsum.
                self.xrmmap['detsum']['counts'][thisrow, :npts, :nchan] = row.total[:npts, :nchan]

                pos    = self.xrmmap['positions/pos']
                rowpos = np.array([p[:npts] for p in row.posvals])

                tpos = rowpos.transpose()

                pos[thisrow, :npts, :] = tpos[:npts, :]

                # now add roi map data
                roimap = self.xrmmap['roimap']
                det_raw = roimap['det_raw']
                det_cor = roimap['det_cor']
                sum_raw = roimap['sum_raw']
                sum_cor = roimap['sum_cor']

                detraw = list(row.sisdata[:npts].transpose())

                detcor = detraw[:]
                sumraw = detraw[:]
                sumcor = detraw[:]

                if self.roi_slices is None:
                    lims = self.xrmmap['config/rois/limits'].value
                    nrois, nmca, nx = lims.shape

                    self.roi_slices = []
                    for iroi in range(nrois):
                        x = [slice(lims[iroi, i, 0],
                                   lims[iroi, i, 1]) for i in range(nmca)]
                        self.roi_slices.append(x)

                for slices in self.roi_slices:
                    iraw = [row.counts[i, :npts, slices[i]].sum(axis=1)
                            for i in range(nmca)]
                    icor = [row.counts[i, :npts, slices[i]].sum(axis=1)*row.dtfactor[i, :npts]
                            for i in range(nmca)]
                    detraw.extend(iraw)
                    detcor.extend(icor)
                    sumraw.append(np.array(iraw).sum(axis=0))
                    sumcor.append(np.array(icor).sum(axis=0))

                det_raw[thisrow, :npts, :] = np.array(detraw).transpose()
                det_cor[thisrow, :npts, :] = np.array(detcor).transpose()
                sum_raw[thisrow, :npts, :] = np.array(sumraw).transpose()
                sum_cor[thisrow, :npts, :] = np.array(sumcor).transpose()

        if self.flag_xrd1d:
            if thisrow == 0:
                self.xrmmap['xrd1D/q'][:] = row.xrdq[0]
            if self.bkgd_xrd1d is not None:
                self.xrmmap['xrd1D/counts'][thisrow,] = row.xrd1d - self.bkgd_xrd1d
            else:
                self.xrmmap['xrd1D/counts'][thisrow,] = row.xrd1d
            if self.azwdgs > 1 and row.xrd1d_wdg is not None:
                for iwdg,wdggrp in enumerate(self.xrmmap['work/xrdwedge'].values()):
                    try:
                        wdggrp['q'] = row.xrdq_wdg[0,:,iwdg]
                    except:
                        pass

                    ## does not yet subtract a background here BECAUSE q-range different
                    ##    for each wedge - won't be same size or shape array
                    ## mkak 2018.02.26
                    wdggrp['counts'][thisrow,] = row.xrd1d_wdg[:,:,iwdg]

        
        if self.flag_xrd2d and row.xrd2d is not None:
            self.xrmmap['xrd2D/counts'][thisrow,] = row.xrd2d

        self.last_row = thisrow
        self.xrmmap.attrs['Last_Row'] = thisrow
        self.h5root.flush()

    def build_schema(self, row, verbose=False):
        '''build schema for detector and scan data'''

        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        print('XRM Map Folder: %s' % self.folder)
        xrmmap = self.xrmmap

        conf = xrmmap['config']
        for key in self.notes:
            conf['notes'].attrs[key] = self.notes[key]

        if self.npts is None:
            self.npts = row.npts
        npts = self.npts

        if self.flag_xrf:
            nmca, xnpts, nchan = row.counts.shape
        else:
            nmca, xnpts, nchan = 1, self.npts, 1

        if self.chunksize is None:
            if xnpts < 10: xnpts=10
            nxx = min(xnpts-1, 2**int(np.log2(xnpts)))
            nxm = 1024
            if nxx > 256:
                nxm = min(1024, int(65536*1.0/ nxx))
            self.chunksize = (1, nxx, nxm)

        if version_ge(self.version, '2.0.0'):
            sismap = xrmmap['scalars']
            sismap.attrs['type'] = 'scalar detectors'
            for aname in re.findall(r"[\w']+", row.sishead[-1]):
                sismap.create_dataset(aname, (NINIT, npts), np.float32,
                                      chunks=self.chunksize[:-1],
                                      maxshape=(None, npts), **self.compress_args)

            # positions
            pos = xrmmap['positions']
            for pname in ('mca realtime', 'mca livetime'):
                self.pos_desc.append(pname)
                self.pos_addr.append(pname)
            npos = len(self.pos_desc)
            self.add_data(pos, 'name',     [six.b(a) for a in self.pos_desc])
            self.add_data(pos, 'address',  [six.b(a) for a in self.pos_addr])
            pos.create_dataset('pos', (NINIT, npts, npos), np.float32,
                               maxshape=(None, npts, npos), **self.compress_args)

            if self.flag_xrf:
                roi_names = [h5str(s) for s in conf['rois/name']]
                roi_limits = np.einsum('jik->ijk', conf['rois/limits'].value)

                offset = conf['mca_calib/offset'].value
                slope  = conf['mca_calib/slope'].value
                quad   = conf['mca_calib/quad'].value

                en_index = np.arange(nchan)

                if verbose:
                    prtxt = '--- Build XRF Schema: %i, %i ---- MCA: (%i, %i)'
                    print(prtxt % (self.nrows_expected, row.npts, nmca, nchan))

                ## mca1 to mca 4
                for i,imca in enumerate(('mca1', 'mca2', 'mca3', 'mca4')):
                    for grp in (xrmmap, xrmmap['roimap']):
                        dgrp = grp.create_group(imca)
                        dgrp.attrs['type'] = 'mca detector'
                        dgrp.attrs['desc'] = imca

                    dgrp = xrmmap[imca]
                    en  = 1.0*offset[i] + slope[i]*1.0*en_index
                    self.add_data(dgrp, 'energy', en, attrs={'cal_offset':offset[i],
                                                             'cal_slope': slope[i]})
                    dgrp.create_dataset('counts', (NINIT, npts, nchan), np.int16,
                                        chunks=self.chunksize,
                                        maxshape=(None, npts, nchan), **self.compress_args)

                    for name, dtype in (('realtime',  np.int    ),
                                        ('livetime',  np.int    ),
                                        ('dtfactor',  np.float32),
                                        ('inpcounts', np.float32),
                                        ('outcounts', np.float32)):
                        dgrp.create_dataset(name, (NINIT, npts), dtype,
                                            maxshape=(None, npts), **self.compress_args)

                    dgrp = xrmmap['roimap'][imca]
                    for rname,rlimit in zip(roi_names,roi_limits[i]):
                        rgrp = dgrp.create_group(rname)
                        for aname,dtype in (('raw',  np.int16  ),
                                            ('cor',  np.float32)):
                            rgrp.create_dataset(aname, (NINIT, npts), dtype,
                                                chunks=self.chunksize[:-1],
                                                maxshape=(None, npts), **self.compress_args)
                        lmtgrp = rgrp.create_dataset('limits', data=en[rlimit])
                        lmtgrp.attrs['type'] = 'energy'
                        lmtgrp.attrs['units'] = 'keV'

                ## mcasum
                for grp in (xrmmap, xrmmap['roimap']):
                    dgrp = grp.create_group('mcasum')
                    dgrp.attrs['type'] = 'virtual mca detector'
                    dgrp.attrs['desc'] = 'sum of detectors'

                dgrp = xrmmap['mcasum']
                en  = 1.0*offset[0] + slope[0]*1.0*en_index
                self.add_data(dgrp, 'energy', en, attrs={'cal_offset':offset[0],
                                                         'cal_slope': slope[0]})
                dgrp.create_dataset('counts', (NINIT, npts, nchan), np.int16,
                                    chunks=self.chunksize,
                                    maxshape=(None, npts, nchan), **self.compress_args)

                dgrp = xrmmap['roimap']['mcasum']
                for rname,rlimit in zip(roi_names,roi_limits[0]):
                    rgrp = dgrp.create_group(rname)
                    for aname,dtype in (('raw',  np.int16  ),('cor',  np.float32)):
                        rgrp.create_dataset(aname, (NINIT, npts), dtype,
                                            chunks=self.chunksize[:-1],
                                            maxshape=(None, npts), **self.compress_args)
                    lmtgrp = rgrp.create_dataset('limits', data=en[rlimit], **self.compress_args)
                    lmtgrp.attrs['type'] = 'energy'
                    lmtgrp.attrs['units'] = 'keV'
        else:
            if self.flag_xrf:
                if verbose:
                    prtxt = '--- Build XRF Schema: %i, %i ---- MCA: (%i, %i)'
                    print(prtxt % (npts, row.npts, nmca, nchan))

                en_index = np.arange(nchan)

                offset = conf['mca_calib/offset'].value
                slope  = conf['mca_calib/slope'].value
                quad   = conf['mca_calib/quad'].value

                roi_names = [h5str(s) for s in conf['rois/name']]
                roi_addrs = [h5str(s) for s in conf['rois/address']]
                roi_limits = conf['rois/limits'].value
                for imca in range(nmca):
                    dname = 'det%i' % (imca+1)
                    dgrp = xrmmap.create_group(dname)
                    dgrp.attrs['type'] = 'mca detector'
                    dgrp.attrs['desc'] = 'mca%i' % (imca+1)
                    en  = 1.0*offset[imca] + slope[imca]*1.0*en_index
                    self.add_data(dgrp, 'energy', en, attrs={'cal_offset':offset[imca],
                                                             'cal_slope': slope[imca]})
                    self.add_data(dgrp, 'roi_name',    [six.b(a) for a in roi_names])
                    self.add_data(dgrp, 'roi_address', [six.b(s % (imca+1)) for s in roi_addrs])
                    self.add_data(dgrp, 'roi_limits',  roi_limits[:,imca,:])

                    dgrp.create_dataset('counts', (NINIT, npts, nchan), np.int16,
                                        chunks=self.chunksize,
                                        maxshape=(None, npts, nchan), **self.compress_args)
                    for name, dtype in (('realtime', np.int),  ('livetime', np.int),
                                        ('dtfactor', np.float32),
                                        ('inpcounts', np.float32),
                                        ('outcounts', np.float32)):
                        dgrp.create_dataset(name, (NINIT, npts), dtype,
                                            maxshape=(None, npts), **self.compress_args)

                # add 'virtual detector' for corrected sum:
                dgrp = xrmmap.create_group('detsum')
                dgrp.attrs['type'] = 'virtual mca'
                dgrp.attrs['desc'] = 'deadtime corrected sum of detectors'
                en = 1.0*offset[0] + slope[0]*1.0*en_index
                self.add_data(dgrp, 'energy', en, attrs={'cal_offset':offset[0],
                                                         'cal_slope': slope[0]})
                self.add_data(dgrp, 'roi_name',    [six.b(a) for a in roi_names])
                self.add_data(dgrp, 'roi_address', [six.b(s % 1) for s in roi_addrs])
                self.add_data(dgrp, 'roi_limits',  roi_limits[: ,0, :])
                dgrp.create_dataset('counts', (NINIT, npts, nchan), np.int16,
                                    chunks=self.chunksize,
                                    maxshape=(None, npts, nchan), **self.compress_args)
                # roi map data
                scan = xrmmap['roimap']
                det_addr = [i.strip() for i in row.sishead[-2][1:].split('|')]
                det_desc = [i.strip() for i in row.sishead[-1][1:].split('|')]
                for addr in roi_addrs:
                    det_addr.extend([addr % (i+1) for i in range(nmca)])

                for desc in roi_names:
                    det_desc.extend(["%s (mca%i)" % (desc, i+1)
                                     for i in range(nmca)])

                sums_map = {}
                sums_desc = []
                nsum = 0
                for idet, addr in enumerate(det_desc):
                    if '(mca' in addr:
                        addr = addr.split('(mca')[0].strip()

                    if addr not in sums_map:
                        sums_map[addr] = []
                        sums_desc.append(addr)
                    sums_map[addr].append(idet)
                nsum = max([len(s) for s in sums_map.values()])
                sums_list = []
                for sname in sums_desc:
                    slist = sums_map[sname]
                    if len(slist) < nsum:
                        slist.extend([-1]*(nsum-len(slist)))
                    sums_list.append(slist)

                nsum = len(sums_list)
                nsca = len(det_desc)

                sums_list = np.array(sums_list)

                self.add_data(scan, 'det_name',    [six.b(a) for a in det_desc])
                self.add_data(scan, 'det_address', [six.b(a) for a in det_addr])
                self.add_data(scan, 'sum_name',    [six.b(a) for a in sums_desc])
                self.add_data(scan, 'sum_list',    sums_list)

                nxx = min(nsca, 8)
                for name, nx, dtype in (('det_raw', nsca, np.int32),
                                        ('det_cor', nsca, np.float32),
                                        ('sum_raw', nsum, np.int32),
                                        ('sum_cor', nsum, np.float32)):
                    scan.create_dataset(name, (NINIT, npts, nx), dtype,
                                        chunks=(2, npts, nx),
                                        maxshape=(None, npts, nx), **self.compress_args)

                # positions
                pos = xrmmap['positions']
                for pname in ('mca realtime', 'mca livetime'):
                    self.pos_desc.append(pname)
                    self.pos_addr.append(pname)
                npos = len(self.pos_desc)
                self.add_data(pos, 'name',     [six.b(a) for a in self.pos_desc])
                self.add_data(pos, 'address',  [six.b(a) for a in self.pos_addr])
                pos.create_dataset('pos', (NINIT, npts, npos), dtype,
                                   maxshape=(None, npts, npos), **self.compress_args)

        if self.flag_xrd2d or self.flag_xrd1d:
            xrdpts, xpixx, xpixy = row.xrd2d.shape
            if verbose:
                prtxt = '--- Build XRD Schema: %i, %i ---- 2D XRD:  (%i, %i)'
                print(prtxt % (self.nrows_expected, row.npts, xpixx, xpixy))

            if self.flag_xrd2d:
                
                xrdgrp = ensure_subgroup('xrd2D',xrmmap)

                xrdgrp.attrs['type'] = 'xrd2D detector'
                xrdgrp.attrs['desc'] = '' #'add detector name eventually'

                xrdgrp.create_dataset('mask', (xpixx, xpixy), np.uint16, **self.compress_args)
                xrdgrp.create_dataset('background', (xpixx, xpixy), np.uint16, **self.compress_args)

                chunksize_2DXRD = (1, npts, xpixx, xpixy)
                xrdgrp.create_dataset('counts', (NINIT, npts, xpixx, xpixy), np.uint16,
                                      chunks = chunksize_2DXRD,
                                      maxshape=(None, npts, xpixx, xpixy), **self.compress_args)

            if self.flag_xrd1d:

                xrdgrp = ensure_subgroup('xrd1D',xrmmap)

                xrdgrp.attrs['type'] = 'xrd1D detector'
                xrdgrp.attrs['desc'] = 'pyFAI calculation from xrd2D data'

                xrdgrp.create_dataset('q',          (self.qstps,), np.float32, **self.compress_args)
                xrdgrp.create_dataset('background', (self.qstps,), np.float32, **self.compress_args)

                chunksize_1DXRD  = (1, npts, self.qstps)
                xrdgrp.create_dataset('counts',
                                      (NINIT, npts, self.qstps),
                                      np.float32,
                                      chunks = chunksize_1DXRD,
                                      maxshape=(None, npts, self.qstps), **self.compress_args)

                if self.azwdgs > 1:
                    xrmmap['work'].create_group('xrdwedge')
                    for azi in range(self.azwdgs):
                        wdggrp = xrmmap['work/xrdwedge'].create_group('wedge_%02d' % azi)

                        wdggrp.create_dataset('q', (self.qstps,), np.float32, **self.compress_args)

                        wdggrp.create_dataset('counts',
                                              (NINIT, npts, self.qstps),
                                              np.float32,
                                              chunks = chunksize_1DXRD,
                                              maxshape=(None, npts, self.qstps), **self.compress_args)

                        #wdggrp.create_dataset('limits', (2,), np.float32)
                        wdg_sz = 360./self.azwdgs
                        wdg_lmts = np.array([azi*wdg_sz, (azi+1)*wdg_sz]) - 180
                        wdggrp.create_dataset('limits', data=wdg_lmts)

        try:
            timestr = '\nStart: %Y-%m-%d %H:%M:%S'
            print(datetime.datetime.fromtimestamp(self.starttime).strftime(timestr))
        except:
            pass

        self.h5root.flush()

    def add_1DXRD(self, qstps=None):
        
        xrd1Dgrp = ensure_subgroup('xrd1D',self.xrmmap)
        xrdcalfile = bytes2str(xrd1Dgrp.attrs.get('calfile',''))
        if os.path.exists(xrdcalfile):
            print('Using calibration file : %s' % xrdcalfile)
            try:
                nrows, npts , xpixx, xpixy = self.xrmmap['xrd2D/counts'].shape
            except:
                #if version_ge(self.version, '2.0.0'):
                #    print('Only compatible with newest hdf5 mapfile version.')
                return

            if qstps is not None: self.qstps = qstps

            pform ='\n--- Build 1D XRD Schema (%i, %i, %i) from 2D XRD (%i, %i, %i, %i) ---'
            print(pform % (nrows, npts, self.qstps, nrows, npts, xpixx, xpixy))

            try:
                xrd1Dgrp.attrs['type'] = 'xrd1D detector'
                xrd1Dgrp.attrs['desc'] = 'pyFAI calculation from xrd2D data'

                xrd1Dgrp.create_dataset('q',          (self.qstps,), np.float32)
                xrd1Dgrp.create_dataset('background', (self.qstps,), np.float32)

                chunksize_1DXRD  = (1, npts, self.qstps)
                xrd1Dgrp.create_dataset('counts',
                                       (nrows, npts, self.qstps),
                                       np.float32,
                                       chunks = chunksize_1DXRD)

                attrs = {'steps':self.qstps,'mask':self.xrd2dmaskfile,'flip':self.flip}

                print(datetime.datetime.fromtimestamp(time.time()).strftime('\nStart: %Y-%m-%d %H:%M:%S'))
                for i in np.arange(nrows):
                    print(' Add row %4i' % (i+1))
                    rowq,row1D = integrate_xrd_row(self.xrmmap['xrd2D/counts'][i],xrdcalfile,**attrs)
                    if i == 0: self.xrmmap['xrd1D/q'][:] = rowq[0]
                    self.xrmmap['xrd1D/counts'][i,] = row1D

                self.flag_xrd1d = True
                print(datetime.datetime.fromtimestamp(time.time()).strftime('End: %Y-%m-%d %H:%M:%S'))
            except:
                print('1DXRD data already in file.')
                return

    def get_slice_y(self):

        for name, val in zip(list(self.xrmmap['config/environ/name']),
                             list(self.xrmmap['config/environ/value'])):
            name = str(name).lower()
            if name.startswith('sample'):
                name = name.replace('samplestage.', '')
                if name.lower() == 'fine y' or name.lower() == 'finey':
                    return float(val)

    def get_datapath_list(self,remove='raw'):
    
        det_list = build_datapath_list(self.xrmmap)
        
        ## remove instances of detector with 'raw' in title
        if isinstance(remove,str):
            return [det for det in det_list if remove not in det]
        else:
            return det_list


    def get_roi_list(self,detname):
        """get a list of rois from detector
        """ 

        detname = self._det_name(detname)
        roigrp = ensure_subgroup('roimap',self.xrmmap)
        
        def sort_roi_limits(roidetgrp):
            roi_name, roi_limits = [],[]            
            for name in roidetgrp.keys():
                roi_name   += [name]
                roi_limits += [list(roidetgrp[name]['limits'][:])]
            return [x for (y,x) in sorted(zip(roi_limits,roi_name))]
        
        rois = ['1']

        if version_ge(self.version, '2.0.0'):
            if detname in roigrp.keys():
                rois = sort_roi_limits(roigrp[detname])

            elif detname.lower().startswith('scal'):
                rois = rois+list(self.xrmmap[detname].keys())
                
        else:
            if detname in self.xrmmap.keys():
                rois = list(roigrp['sum_name']) + rois
            try:
                rois = sort_roi_limits(roigrp[detname]) + rois
            except:
                pass
                
        return rois
        

    def get_detector_list(self):
        """get a list of detector groups,
        ['mcasum', 'mca1', ..., 'scalars']
        """
        xrmmap = self.xrmmap
        det_list = []
        if version_ge(self.version, '2.0.0'):
            det_list = build_detector_list(xrmmap['roimap'])
            if 'scalars' in xrmmap:
                det_list += ['scalars']
        else:
            det_list = build_detector_list(xrmmap)
            for det in ('scalars','xrd1D','xrd2D'):
                 try:
                     det_list.pop(det_list.index(det))
                 except:
                     pass
            for det in build_detector_list(xrmmap['roimap']):
                if det not in det_list:
                    det_list += [grp]

        if len(det_list) < 1:
            det_list = ['']

        return det_list

    def reset_flags(self):
        '''
        Reads hdf5 file for data and sets the flags.
        mkak 2016.08.30 // rewritten mkak 2017.08.03 // rewritten mkak 2017.12.05
        '''

        detlist = build_detector_list(self.xrmmap)
        for det in detlist:
            detgrp = self.xrmmap[det]
                        
            dettype = bytes2str(detgrp.attrs.get('type', '')).lower()
            if 'mca' in dettype:
                self.flag_xrf   = self.check_flag(detgrp)
            elif 'xrd2d' in dettype:
                self.flag_xrd2d = self.check_flag(detgrp)
            elif 'xrd1d' in dettype:
                self.flag_xrd1d = self.check_flag(detgrp)
            elif det == 'xrd': ## compatible with old version
                try:
                    detgrp['data1D']
                    self.flag_xrd1d = True
                except:
                    pass
                try:
                    detgrp['data2D']
                    self.flag_xrd2d = True
                except:
                    pass

    def check_flag(self,detgrp):

        try:
            detgrp['counts']
            return True
        except:
            return False

    def print_flags(self):

       print('')
       print('   XRF data: %s' % self.flag_xrf)
       print('2D-XRD data: %s' % self.flag_xrd2d)
       print('1D-XRD data: %s' % self.flag_xrd1d)

    def resize_arrays(self, nrow):
        "resize all arrays for new nrow size"

        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        if version_ge(self.version, '2.0.0'):

            g = self.xrmmap['positions/pos']
            old, npts, nx = g.shape
            g.resize((nrow, npts, nx))

            for g in self.xrmmap.values():
                type_attr = bytes2str(g.attrs.get('type', ''))
                if type_attr.find('det') > -1:
                    if type_attr.startswith('scalar'):
                        for aname in g.keys():
                            oldnrow, npts = g[aname].shape
                            g[aname].resize((nrow, npts))
                    elif type_attr.startswith('mca'):
                        oldnrow, npts, nchan = g['counts'].shape
                        g['counts'].resize((nrow, npts, nchan))
                        for aname in ('livetime', 'realtime',
                                      'inpcounts', 'outcounts', 'dtfactor'):
                            g[aname].resize((nrow, npts))
                    elif type_attr.startswith('virtual mca'):
                        oldnrow, npts, nchan = g['counts'].shape
                        g['counts'].resize((nrow, npts, nchan))
                    elif type_attr.startswith('xrd2D'):
                        oldnrow, npts, xpixx, xpixy = g['counts'].shape
                        g['counts'].resize((nrow, npts, xpixx, xpixy))
                    elif type_attr.startswith('xrd1D'):
                        oldnrow, npts, qstps = g['counts'].shape
                        g['counts'].resize((nrow, npts, qstps))

            if self.azwdgs > 1:
                for g in self.xrmmap['work/xrdwedge'].values():
                    g['counts'].resize((nrow, npts, qstps))

            for g in self.xrmmap['roimap'].values(): # loop through detectors in roimap
                for h in g.values():  # loop through rois in roimap
                    for aname in ('raw','cor'):
                        oldnrow, npts = h[aname].shape
                        h[aname].resize((nrow, npts))

        else: ## old file format method

            realmca_groups = []
            virtmca_groups = []
            for g in self.xrmmap.values():
                # include both real and virtual mca detectors!
                type_attr = bytes2str(g.attrs.get('type', ''))
                if type_attr.find('det') > -1 or type_attr.find('mca') > -1:
                    if type_attr.startswith('mca'):
                        realmca_groups.append(g)
                    elif type_attr.startswith('virtual mca'):
                        virtmca_groups.append(g)
                    elif type_attr.startswith('xrd2D'):
                        oldnrow, npts, xpixx, xpixy = g['counts'].shape
                        g['counts'].resize((nrow, npts, xpixx, xpixy))
                    elif type_attr.startswith('xrd1D'):
                        oldnrow, npts, qstps = g['counts'].shape
                        g['counts'].resize((nrow, npts, qstps))

            if self.azwdgs > 1:
                for g in self.xrmmap['work/xrdwedge'].values():
                    g['counts'].resize((nrow, npts, qstps))

            oldnrow, npts, nchan = realmca_groups[0]['counts'].shape
            for g in realmca_groups:
                g['counts'].resize((nrow, npts, nchan))
                for aname in ('livetime', 'realtime',
                              'inpcounts', 'outcounts', 'dtfactor'):
                    g[aname].resize((nrow, npts))

            for g in virtmca_groups:
                g['counts'].resize((nrow, npts, nchan))

            g = self.xrmmap['positions/pos']
            old, npts, nx = g.shape
            g.resize((nrow, npts, nx))

            for bname in ('det_raw', 'det_cor', 'sum_raw', 'sum_cor'):
                g = self.xrmmap['roimap'][bname]
                old, npts, nx = g.shape
                g.resize((nrow, npts, nx))

        self.h5root.flush()

    def add_work_array(self, data, name, **kws):
        '''
        add an array to the work group of processed arrays
        '''
        workgroup = ensure_subgroup('work',self.xrmmap)
        if name is None:
            name = 'array_%3.3i' % (1+len(workgroup))
        if name in workgroup:
            raise ValueError("array name '%s' exists in work arrays" % name)
        ds = workgroup.create_dataset(name, data=data)
        for key, val in kws.items():
            ds.attrs[key] = val
        self.h5root.flush()

    def del_work_array(self, name):
        '''
        delete an array to the work group of processed arrays
        '''
        workgroup = ensure_subgroup('work',self.xrmmap)
        name = h5str(name)
        if name in workgroup:
            del workgroup[name]
            self.h5root.flush()

    def get_work_array(self, name):
        '''
        get an array from the work group of processed arrays by index or name
        '''
        workgroup = ensure_subgroup('work',self.xrmmap)
        dat = None
        name = h5str(name)
        if name in workgroup:
            dat = workgroup[name]
        return dat

    def work_array_names(self):
        '''
        return list of work array descriptions
        '''
        workgroup = ensure_subgroup('work',self.xrmmap)
        return [h5str(g) for g in workgroup.keys()]

    def add_area(self, amask, name=None, desc=None, tomo=False):
        '''add a selected area, with optional name
        the area is encoded as a boolean array the same size as the map

        '''
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        base_grp = self.xrmmap
        area_grp = ensure_subgroup('areas',base_grp)
        if name is None:
            name = 'area_001'
        if len(area_grp) > 0:
            count = len(area_grp)
            while name in area_grp and count < 9999:
                name = 'area_%3.3i' % (count)
                count += 1
        ds = area_grp.create_dataset(name, data=amask)
        if desc is None:
            desc = name
        ds.attrs['description'] = desc
        ds.attrs['tomograph']   = tomo
        self.h5root.flush()
        return name

    def export_areas(self, filename=None, tomo=False):
        '''export areas to datafile '''
        if filename is None:
            file_str = '%s_TomoAreas.npz' if tomo else '%s_Areas.npz'
            filename = file_str % self.filename
        
        base_grp = self.xrmmap
        area_grp = ensure_subgroup('areas',base_grp)

        kwargs = {}
        for aname in area_grp:
            kwargs[aname] = area_grp[aname][:]
        np.savez(filename, **kwargs)
        return filename

    def import_areas(self, filename, overwrite=False, tomo=False):
        '''import areas from datafile exported by export_areas()'''
        npzdat = np.load(filename)

        othername = os.path.split(filename)[1]
        for npz_str in ('.h5_Areas.npz','.h5_TomoAreas.npz'):
            if othername.endswith(npz_str):
                othername = othername.replace(npz_str, '')

        for aname in npzdat.files:
            amask = npzdat[aname]
            outname = '%s_%s' % (aname, othername)
            self.add_area(amask, name=outname, desc=outname, tomo=tomo)

    def get_area(self, name=None, desc=None):
        '''
        get area group by name or description
        '''

        area_grp = ensure_subgroup('areas',self.xrmmap)

        if name is not None and name in area_grp:
            return area_grp[name]
        if desc is not None:
            for name in area_grp:
                if desc == bytes2str(area_grp[name].attrs.get('description','')):
                    return area_grp[name]
        return None

    def get_area_stats(self, name=None, desc=None):
        '''return statistics for all raw detector counts/sec values

        for each raw detector returns
           name, length, mean, standard_deviation,
           median, mode, minimum, maximum,
           gmean, hmean, skew, kurtosis

        '''
        area = self.get_area(name=name, desc=desc)
        if area is None:
            return None

        if 'roistats' in area.attrs:
            return json.loads(area.attrs.get('roistats',''))

        amask = area.value

        roidata = []
        d_addrs = [d.lower() for d in self.xrmmap['roimap/det_address']]
        d_names = [d for d in self.xrmmap['roimap/det_name']]
        # count times
        ctime = [1.e-6*self.xrmmap['roimap/det_raw'][:,:,0][amask]]
        for i in range(self.xrmmap.attrs.get('N_Detectors',0)):
            tname = 'det%i/realtime' % (i+1)
            ctime.append(1.e-6*self.xrmmap[tname].value[amask])

        for idet, dname in enumerate(d_names):
            daddr = d_addrs[idet]
            det = 0
            if 'mca' in daddr:
                det = 1
                words = daddr.split('mca')
                if len(words) > 1:
                    det = int(words[1].split('.')[0])
            if idet == 0:
                d = ctime[0]
            else:
                d = self.xrmmap['roimap/det_raw'][:,:,idet][amask]/ctime[det]

            try:
                hmean, gmean = stats.gmean(d), stats.hmean(d)
                skew, kurtosis = stats.skew(d), stats.kurtosis(d)
            except ValueError:
                hmean, gmean, skew, kurtosis = 0, 0, 0, 0
            mode = stats.mode(d)
            roidata.append((dname, len(d), d.mean(), d.std(), np.median(d),
                            stats.mode(d), d.min(), d.max(),
                            gmean, hmean, skew, kurtosis))

            if 'roistats' not in area.attrs:
                area.attrs['roistats'] = json.dumps(roidata)
                self.h5root.flush()

        return roidata

    def get_translation_axis(self,hotcols=False):
        posnames = [n.lower() for n in self.xrmmap['positions/name']]
        # print(" Get Translation axes ", posnames, 'x' in posnames)
        if 'x' in posnames:
            x = self.get_pos('x', mean=True)
        elif 'fine x' in posnames:
            x = self.get_pos('fine x', mean=True)
        else:
            x = self.get_pos(0, mean=True)

        if hotcols and x is not None:
           if len(x) == self.xrmmap[self._det_name()]['counts'].shape[1]:
               x = x[1:-1]

        return x

    def get_rotation_axis(self,axis=None,hotcols=False):

        posnames = [n.lower() for n in self.xrmmap['positions/name']]
        if axis is not None:
            if axis in posnames or type(axis) == int:
                omega = self.get_pos(axis, mean=True)
        elif 'theta' in posnames:
            omega = self.get_pos('theta', mean=True)
        elif 'omega' in posnames:
            omega = self.get_pos('omega', mean=True)
        else:
            omega = None

        if hotcols and omega is not None:
           if len(omega) == self.xrmmap[self._det_name()]['counts'].shape[1]:
               omega = omega[1:-1]        
        return omega

    def get_tomography_center(self):

        tomogrp = ensure_subgroup('tomo',self.xrmmap)
        try:
            return tomogrp['center'].value
        except:
            self.set_tomography_center()

        return tomogrp['center'].value

    def set_tomography_center(self,center=None):
        if center is None:
            center = len(self.get_translation_axis())/2.

        tomogrp = ensure_subgroup('tomo',self.xrmmap)
        try:
            del tomogrp['center']
        except:
            pass
        tomogrp.create_dataset('center', data=center)

        self.h5root.flush()

    def get_sinogram(self, roi_name, det=None, trim_sino=False, hotcols=False, **kws):
        '''extract roi map for a pre-defined roi by name

        Parameters
        ---------
        roiname    :  str                       ROI name
        det        :  str                       detector name
        dtcorrect  :  optional, bool [True]     dead-time correct data
        hotcols    :  optional, bool [False]    suppress hot columns

        Returns
        -------
        sinogram for ROI data
        sinogram_order (needed for knowing shape of sinogram)
        '''

        sino  = self.get_roimap(roi_name, det=det, hotcols=hotcols, **kws)
        x     = self.get_translation_axis(hotcols=hotcols)
        omega = self.get_rotation_axis(hotcols=hotcols)

        if omega is None:
            print('\n** Cannot compute tomography: no rotation axis specified in map. **')
            return

        if trim_sino: sino,x,omega = trim_sinogram(sino,x,omega)

        return reshape_sinogram(sino,x,omega)

    def get_tomograph(self, sino, omega=None, center=None, hotcols=False, **kws):
        '''
        returns tomo_center, tomo
        '''

        if center is None:
            center = self.get_tomography_center()

        if omega  is None:
            omega = self.get_rotation_axis(hotcols=hotcols)
        if omega is None:
            print('\n** Cannot compute tomography: no rotation axis specified in map. **')
            return

        center,tomo = tomo_reconstruction(sino, omega=omega, center=center, **kws)
        self.set_tomography_center(center=center)
        
        return tomo

    def save_tomograph(self, datapath, tomo_alg=[], dtcorrect=False, hotcols=False, **kws):
        '''
        saves group for tomograph for selected detector
        '''
       
        ## check to make sure the selected detector exists for reconstructions
        detlist = self.get_datapath_list(remove=None)
        if datapath not in detlist:
            print("Detector '%s' not found in data." % datapath)
            print('Known detectors: %s' % detlist)
            return
        datagroup = self.xrmmap[datapath]

        ## check to make sure there is data to perform tomographic reconstruction
        center = self.get_tomography_center()
        
        x     = self.get_translation_axis(hotcols=hotcols)
        omega = self.get_rotation_axis(hotcols=hotcols)
        
        if omega is None:
            print('\n** Cannot compute tomography: no rotation axis specified in map. **')
            return
        
        ## define detector path
        detgroup  = datagroup
        while isinstance(detgroup,h5py.Dataset):
            detgroup = detgroup.parent
            detpath = detgroup.name

        ## create path for saving data
        tpath = datapath.replace('/xrmmap','/tomo')
        tpath = tpath.replace('/scalars','')
        if tpath.endswith('raw'):
            tpath = tpath.replace('_raw','')
            dtcorrect = False
        elif tpath.endswith('counts'):
            tpath = os.path.split(tpath)[0]
 
        ## build path for saving data in tomo-group
        grp = self.xrmmap
        for kpath in tpath.split('/'):
            if len(kpath) > 0:
                grp = ensure_subgroup(kpath,grp)
        tomogrp = grp
        
        ## define sino group from datapath
        if 'scalars' in datapath or 'xrd' in datapath:
            sino = datagroup.value
        elif dtcorrect:
            if 'sum' in datapath:
                sino = np.zeros(np.shape(np.einsum('jki->ijk', datagroup.value)))
                for i in range(4):
                ##for i in range(self.ndet):
                    idatapath = datapath.replace('sum',str(i+1))
                    idatagroup = self.xrmmap[idatapath]
                    idetpath  = detpath.replace('sum',str(i+1))
                    idetgroup = self.xrmmap[idetpath]
                    sino += np.einsum('jki->ijk', idatagroup.value) * idetgroup['dtfactor'].value
                
            else:
                sino = np.einsum('jki->ijk', datagroup.value) * detgroup['dtfactor'].value
        else:
            sino = datagroup.value

        sino,order = reshape_sinogram(sino,x,omega)

        center,tomo = tomo_reconstruction(sino, omega=omega, center=center,
                                          sinogram_order=order, tomo_alg=tomo_alg)

        tomogrp.attrs['tomo_alg'] = '-'.join([str(t) for t in tomo_alg])
        tomogrp.attrs['center'] = '%0.2f pixels' % (center)
        
        try:
            tomogrp.create_dataset('counts', data=np.swapaxes(tomo,0,2), **self.compress_args)
        except:
            del tomogrp['counts']
            tomogrp.create_dataset('counts', data=np.swapaxes(tomo,0,2), **self.compress_args)
        
        for data_tag in ('energy','q'):
            if data_tag in detgroup.keys():
                try:
                    tomogrp.create_dataset(data_tag, data=detgroup[data_tag])
                    del tomogrp[data_tag]
                except:
                    del tomogrp[data_tag]
                    tomogrp.create_dataset(data_tag, data=detgroup[data_tag])

        for key,val in dict(detgroup.attrs).iteritems():
            tomogrp.attrs[key] = val

        self.h5root.flush()

    def claim_hostid(self):
        "claim ownership of file"
        self.take_ownership()

    def take_ownership(self):
        "claim ownership of file"
        if self.xrmmap is None:
            return
        self.xrmmap.attrs['Process_Machine'] = socket.gethostname()
        self.xrmmap.attrs['Process_ID'] = os.getpid()
        self.h5root.flush()

    def release_ownership(self):
        self.xrmmap.attrs['Process_Machine'] = ''
        self.xrmmap.attrs['Process_ID'] = 0
        self.xrmmap.attrs['Last_Row'] = self.last_row

    def check_ownership(self):
        return self.check_hostid()

    def check_hostid(self):
        '''checks host and id of file:
        returns True if this process the owner of the file
        '''
        if self.xrmmap is None:
            return
        attrs = self.xrmmap.attrs
        self.folder = attrs['Map_Folder']

        file_mach = attrs['Process_Machine']
        file_pid  = attrs['Process_ID']
        if len(file_mach) < 1 or file_pid < 1:
            self.take_ownership()
            return True
        return (file_mach == socket.gethostname() and
                file_pid == os.getpid())

    def folder_has_newdata(self):
        if self.folder is not None and isGSEXRM_MapFolder(self.folder):
            self.read_master()
            return (self.last_row < len(self.rowdata)-1)
        return False

    def read_master(self):
        "reads master file for toplevel scan info"
        if self.folder is None or not isGSEXRM_MapFolder(self.folder):
            return
        self.masterfile = os.path.join(nativepath(self.folder),self.MasterFile)
        mtime = int(os.stat(self.masterfile).st_mtime)
        self.masterfile_mtime = mtime

        try:
            header, rows = readMasterFile(self.masterfile)
        except IOError:
            raise GSEXRM_Exception(
                "cannot read Master file from '%s'" % self.masterfile)

        self.notes['end_time'] = isotime(os.stat(self.masterfile).st_ctime)
        self.master_header = header
        # carefully read rows to avoid repeated rows due to bad collection
        self.rowdata = []
        _yl, _xl, _s1 = None, None, None
        for row in rows:
            yval, xrff, sisf = row[0], row[1], row[2]
            il = len(self.rowdata)-1
            if il > -1:
                _yl, _xl, _s1 = (self.rowdata[il][0],
                                 self.rowdata[il][1],
                                 self.rowdata[il][2])
            # skip repeated rows in master file
            if yval != _yl and (xrff != _xl or sisf != _s1):
                self.rowdata.append(row)
            #else:
            #    print(" skip row ", yval, xrff, sisf)
        self.scan_version = 1.00
        self.nrows_expected = None
        self.start_time = time.ctime()
        for line in header:
            words = line.split('=')
            if 'scan.starttime' in words[0].lower():
                self.start_time = words[1].strip()
                self.notes['scan_start_time'] = isotime(self.start_time)
            elif 'scan.version' in words[0].lower():
                self.scan_version = words[1].strip()
            elif 'scan.nrows_expected' in words[0].lower():
                self.nrows_expected = int(words[1].strip())
        self.scan_version = float(self.scan_version)


        self.folder_modtime = os.stat(self.masterfile).st_mtime
        self.stop_time = time.ctime(self.folder_modtime)
        try:
            last_file = os.path.join(self.folder,rows[-1][2])
            self.stop_time = time.ctime(os.stat(last_file).st_ctime)
        except:
            pass

        self.notes['scan_end_time'] = isotime(self.stop_time)
        self.notes['scan_version'] = self.scan_version

        if self.scan_version < 1.35 and (self.flag_xrd2d or self.flag_xrd1d):
            xrd_files = [fn for fn in os.listdir(self.folder) if fn.endswith('nc')]
            for i,addxrd in enumerate(xrd_files):
                self.rowdata[i].insert(4,addxrd)

        cfile = FastMapConfig()
        cfile.Read(os.path.join(self.folder, self.ScanFile))
        self.mapconf = cfile.config

        if self.filename is None:
            self.filename = self.mapconf['scan']['filename']
        if not self.filename.endswith('.h5'):
            self.filename = "%s.h5" % self.filename

        mapconf = self.mapconf
        slow_pos = mapconf['slow_positioners']
        fast_pos = mapconf['fast_positioners']

        scanconf = mapconf['scan']
        self.dimension = scanconf['dimension']
        start = mapconf['scan']['start1']
        stop  = mapconf['scan']['stop1']
        step  = mapconf['scan']['step1']
        span = abs(stop-start)
        self.npts = int(abs(abs(step)*1.01 + span)/abs(step))
        # print("ReadMaster set npts ", self.npts)

        pos1 = scanconf['pos1']
        self.pos_addr = [pos1]
        self.pos_desc = [slow_pos[pos1]]
        # note: XPS gathering file now saving ONLY data for the fast axis
        self.ixaddr = 0

        if self.dimension > 1:
            yaddr = scanconf['pos2']
            self.pos_addr.append(yaddr)
            self.pos_desc.append(slow_pos[yaddr])
            
        

    def _det_name(self, det=None):
        "return  XRMMAP group for a detector"

        mcastr = 'mca' if version_ge(self.version, '2.0.0') else 'det'
        dgroup = '%ssum' % mcastr

        try: ## python 2
            is_str = (isinstance(det,str) or isinstance(det, unicode))   
        except: ## python 3
            is_str = isinstance(det,str)
        if is_str:
            for d in build_detector_list(self.xrmmap):
                if det.lower() == d.lower():
                    dgroup = d
        elif isinstance(det,int):
            if det in range(1, self.ndet+1):
                dgroup = '%s%i' % (mcastr,det)

        return dgroup

    def _det_group(self, det=None):
        "return  XRMMAP group for a detector"

        dgroup = self._det_name(det)
        return self.xrmmap[dgroup]

    def get_energy(self, det=None):
        '''return energy array for a detector'''
        try:
            group = self.xrmmap[det]
        except:
            group = self._det_group(det)
        return group['energy'].value

    def get_shape(self):
        '''returns NY, NX shape of array data'''
        ny, nx, npos = self.xrmmap['positions/pos'].shape
        return ny, nx

    def get_mca_area(self, areaname, det=None, dtcorrect=True, callback=None, tomo=False):
        '''return XRF spectra as MCA() instance for
        spectra summed over a pre-defined area

        Parameters
        ---------
        areaname :   str       name of area
        dtcorrect :  optional, bool [True]         dead-time correct data

        Returns
        -------
        MCA object for XRF counts in area

        '''

        try:
            area = self.get_area(areaname).value
        except:
            raise GSEXRM_Exception("Could not find area '%s'" % areaname)

        if tomo:
            tomogrp = ensure_subgroup('tomo',self.xrmmap)
            detlist = build_detector_list(tomogrp)
            if len(detlist) < 1:
                return

            if det in detlist:
                detname = det
            elif det is None:
                detname = detlist[0]
            elif (type(det) is str and det.isdigit()) or type(det) is int:
                det = int(det)
                detname = 'det%i' % det
                if version_ge(self.version, '2.0.0'):
                    detname = detname.replace('det','mca')
            else:
                return
                
            dgroup = 'tomo/%s' % detname

            try:
                mapdat = self.xrmmap[dgroup]
                dtcorrect = False
            except:
                return

        else:
            dgroup = self._det_name(det)
            mapdat = self._det_group(det)

        ix, iy, nmca = mapdat['counts'].shape

        npix = len(np.where(area)[0])
        if npix < 1:
            return None
        sy, sx = [slice(min(_a), max(_a)+1) for _a in np.where(area)]
        xmin, xmax, ymin, ymax = sx.start, sx.stop, sy.start, sy.stop
        nx, ny = (xmax-xmin), (ymax-ymin)
        NCHUNKSIZE = 16384 # 8192
        use_chunks = nx*ny > NCHUNKSIZE
        step = int((nx*ny)/NCHUNKSIZE)

        if not use_chunks:
            try:
                if hasattr(callback , '__call__'):
                    callback(1, 1, nx*ny)
                counts = self.get_counts_rect(ymin, ymax, xmin, xmax,
                                           mapdat=mapdat, area=area,
                                           dtcorrect=dtcorrect)
            except MemoryError:
                use_chunks = True
        if use_chunks:
            counts = np.zeros(nmca)
            if nx > ny:
                for i in range(step+1):
                    x1 = xmin + int(i*nx/step)
                    x2 = min(xmax, xmin + int((i+1)*nx/step))
                    if x1 >= x2: break
                    if hasattr(callback , '__call__'):
                        callback(i, step, (x2-x1)*ny)
                    counts += self.get_counts_rect(ymin, ymax, x1, x2, mapdat=mapdat,
                                                det=det, area=area,
                                                dtcorrect=dtcorrect)
            else:
                for i in range(step+1):
                    y1 = ymin + int(i*ny/step)
                    y2 = min(ymax, ymin + int((i+1)*ny/step))
                    if y1 >= y2: break
                    if hasattr(callback , '__call__'):
                        callback(i, step, nx*(y2-y1))
                    counts += self.get_counts_rect(y1, y2, xmin, xmax, mapdat=mapdat,
                                                det=det, area=area,
                                                dtcorrect=dtcorrect)

        ltime, rtime = self.get_livereal_rect(ymin, ymax, xmin, xmax, det=det,
                                              dtcorrect=dtcorrect, area=area)
        return self._getmca(dgroup, counts, areaname, npixels=npix,
                            real_time=rtime, live_time=ltime)

    def get_mca_rect(self, ymin, ymax, xmin, xmax, det=None, dtcorrect=True):
        '''return mca counts for a map rectangle, optionally

        Parameters
        ---------
        ymin :       int       low y index
        ymax :       int       high y index
        xmin :       int       low x index
        xmax :       int       high x index
        det :        optional, None or int         index of detector
        dtcorrect :  optional, bool [True]         dead-time correct data

        Returns
        -------
        MCA object for XRF counts in rectangle

        '''

        dgroup = self._det_name(det)
        mapdat = self._det_group(det)
        counts = self.get_counts_rect(ymin, ymax, xmin, xmax, mapdat=mapdat,
                                      det=det, dtcorrect=dtcorrect)
        name = 'rect(y=[%i:%i], x==[%i:%i])' % (ymin, ymax, xmin, xmax)
        npix = (ymax-ymin+1)*(xmax-xmin+1)
        ltime, rtime = self.get_livereal_rect(ymin, ymax, xmin, xmax, det=det,
                                              dtcorrect=dtcorrect, area=None)

        return self._getmca(dgroup, counts, name, npixels=npix,
                            real_time=rtime, live_time=ltime)

    def get_counts_rect(self, ymin, ymax, xmin, xmax, mapdat=None, det=None,
                        area=None, dtcorrect=True, tomo=False):
        '''return counts for a map rectangle, optionally
        applying area mask and deadtime correction

        Parameters
        ---------
        ymin :       int       low y index
        ymax :       int       high y index
        xmin :       int       low x index
        xmax :       int       high x index
        mapdat :     optional, None or map data
        det :        optional, None or int         index of detector
        dtcorrect :  optional, bool [True]         dead-time correct data
        area :       optional, None or area object  area for mask

        Returns
        -------
        ndarray for XRF counts in rectangle

        Does *not* check for errors!

        Note:  if mapdat is None, the map data is taken from the 'det' parameter
        '''
        
        if mapdat is None:
            mapdat = self._det_group(det)
        det = os.path.split(mapdat.name)[-1]

        if bytes2str(mapdat.attrs.get('type', '')).startswith('xrd'):
            dtcorrect = False
        elif tomo:
            dtcorrect = False

        nx, ny = (xmax-xmin, ymax-ymin)
        sx = slice(xmin, xmax)
        sy = slice(ymin, ymax)

        nchan = None
        try:
            ix, iy, nchan = mapdat['counts'].shape
        except:
            ix, iy, pixx, pixy = mapdat['counts'].shape
        cell   = mapdat['counts'].regionref[sy, sx, :]
        counts = mapdat['counts'][cell]
        
        if nchan is None:
            counts = counts.reshape(ny, nx, pixx, pixy)
        else:
            counts = counts.reshape(ny, nx, nchan)

        if mapdat is None or 'sum' in det:
            counts = np.zeros(counts.shape)
            if dtcorrect:
                for _idet in range(1, self.ndet):
                    _md    = self._det_group(_idet)
                    cell   = _md['counts'].regionref[sy, sx, :]
                    _cts   = _md['counts'][cell].reshape(ny, nx, nchan)
                    cell   = _md['dtfactor'].regionref[sy, sx]
                    dtfact = _md['dtfactor'][cell].reshape(ny, nx)
                    dtfact = dtfact.reshape(dtfact.shape[0], dtfact.shape[1], 1)
                    counts += _cts * dtfact
            else:
                for _idet in range(1, self.ndet):
                    _md    = self._det_group(_idet)
                    cell   = _md['counts'].regionref[sy, sx, :]
                    _cts   = _md['counts'][cell].reshape(ny, nx, nchan)
                    counts += _cts
        elif mapdat is not None:
            if dtcorrect:
                cell   = mapdat['dtfactor'].regionref[sy, sx]
                dtfact = mapdat['dtfactor'][cell].reshape(ny, nx)
                dtfact = dtfact.reshape(dtfact.shape[0], dtfact.shape[1], 1)
                counts = counts * dtfact
            #else:
            #    cell   = mapdat['counts'].regionref[sy, sx, :]
            #    counts = mapdat['counts'][cell].reshape(ny, nx)

        if area is not None:
            counts = counts[area[sy, sx]]
        else:
            counts = counts.sum(axis=0)
        return counts.sum(axis=0)

    def get_livereal_rect(self, ymin, ymax, xmin, xmax, det=None,
                          area=None, dtcorrect=True):
        '''return livetime, realtime for a map rectangle, optionally
        applying area mask and deadtime correction

        Parameters
        ---------
        ymin :       int       low y index
        ymax :       int       high y index
        xmin :       int       low x index
        xmax :       int       high x index
        det :        optional, None or int         index of detector
        dtcorrect :  optional, bool [True]         dead-time correct data
        area :       optional, None or area object  area for mask

        Returns
        -------
        realtime, livetime in seconds

        Does *not* check for errors!

        '''
        # need real size, not just slice values, for np.zeros()
        shape = self._det_group(1)['livetime'].shape
        if ymax < 0: ymax += shape[0]
        if xmax < 0: xmax += shape[1]
        nx, ny = (xmax-xmin, ymax-ymin)
        sx = slice(xmin, xmax)
        sy = slice(ymin, ymax)
        if det is None or 'sum' in str(det):
            livetime = np.zeros((ny, nx))
            realtime = np.zeros((ny, nx))
            for d in range(1, self.ndet+1):
                dmap = self._det_group(d)
                livetime += dmap['livetime'][sy, sx]
                realtime += dmap['realtime'][sy, sx]
            livetime /= (1.0*self.ndet)
            realtime /= (1.0*self.ndet)
        else:
            dmap = self._det_group(det)
            livetime = dmap['livetime'][sy, sx]
            realtime = dmap['realtime'][sy, sx]
        if area is not None:
            livetime = livetime[area[sy, sx]]
            realtime = realtime[area[sy, sx]]

        livetime = 1.e-6*livetime.sum()
        realtime = 1.e-6*realtime.sum()
        return livetime, realtime

    def _getmca(self, dgroup, counts, name, npixels=None, tomo=False, **kws):
        '''return an MCA object for a detector group
        (map is one of the  'det1', ... 'detsum')
        with specified counts array and a name


        Parameters
        ---------
        det :        detector object (one of det1, det2, ..., detsum)
        counts :     ndarray array of counts
        name  :      name for MCA

        Returns
        -------
        MCA object

        '''
        if dgroup.startswith('tomo/'):
            tomo = True
            dgroup = dgroup[5:]

        map  = self.xrmmap[dgroup]
        cal  = map['energy'].attrs
        _mca = MCA(counts=counts, offset=cal['cal_offset'],
                   slope=cal['cal_slope'], **kws)

        _mca.energy =  map['energy'].value
        env_names = list(self.xrmmap['config/environ/name'])
        env_addrs = list(self.xrmmap['config/environ/address'])
        env_vals  = list(self.xrmmap['config/environ/value'])
        for desc, val, addr in zip(env_names, env_vals, env_addrs):
            _mca.add_environ(desc=desc, val=val, addr=addr)

        if npixels is not None:
            _mca.npixels=npixels


        if version_ge(self.version, '2.0.0'):

            for roi in self.xrmmap['roimap'][dgroup]:
                emin,emax = self.xrmmap['roimap'][dgroup][roi]['limits'][:]
                Eaxis = map['energy'][:]

                imin = (np.abs(Eaxis-emin)).argmin()
                imax = (np.abs(Eaxis-emax)).argmin()
                _mca.add_roi(roi, left=imin, right=imax)
        else:

            # a workaround for poor practice -- some '1.3.0' files
            # were built with 'roi_names', some with 'roi_name'
            roiname = 'roi_name'
            if roiname not in map: roiname = 'roi_names'

            roinames = list(map[roiname])
            roilims  = list(map['roi_limits'])
            for roi, lims in zip(roinames, roilims):
                _mca.add_roi(roi, left=lims[0], right=lims[1])

        _mca.areaname = _mca.title = name
        path, fname = os.path.split(self.filename)
        _mca.filename = fix_filename(fname)
        fmt = "Data from File '%s', detector '%s', area '%s'"
        _mca.info  =  fmt % (self.filename, dgroup, name)

        return _mca

    def get_xrd_area(self, areaname, xrd='2D', callback=None, **kws):
        '''return 1D or 2D XRD pattern for a pre-defined area

        Parameters
        ---------
        areaname :   str       name of area

        Returns
        -------
        diffraction pattern for given area

        '''

        try:
            area = self.get_area(areaname).value
        except:
            raise GSEXRM_Exception("Could not find area '%s'" % areaname)
            return
        npix = len(np.where(area)[0])
        if npix < 1:
            return None

        stps, xpix, ypix, qdat = 0,0,0,None
            
        xrddir   = 'xrd1D' if '1' in xrd else 'xrd2D'
        mapdat   = self.xrmmap[xrddir]
        xrdshape = mapdat['counts'].shape
        mapname  = mapdat.name 

        try:
            qdat = mapdat['q']
        except:
            pass

        sy, sx = [slice(min(_a), max(_a)+1) for _a in np.where(area)]
        xmin, xmax, ymin, ymax = sx.start, sx.stop, sy.start, sy.stop
        nx, ny = (xmax-xmin), (ymax-ymin)
        NCHUNKSIZE = 16384 # 8192
        use_chunks = nx*ny > NCHUNKSIZE
        step = int((nx*ny)/NCHUNKSIZE)
        
        if not use_chunks:
            try:
                if hasattr(callback , '__call__'):
                    callback(1, 1, nx*ny)
                counts = self.get_counts_rect(ymin, ymax, xmin, xmax, area=area,
                                                mapdat=mapdat, dtcorrect=False)
            except MemoryError:
                use_chunks = True
        if use_chunks:
            counts = np.zeros(xrdshape[2:])
            if nx > ny:
                for i in range(step+1):
                    x1 = xmin + int(i*nx/step)
                    x2 = min(xmax, xmin + int((i+1)*nx/step))
                    if x1 >= x2: break
                    if hasattr(callback , '__call__'):
                        callback(i, step, (x2-x1)*ny)
                    counts += self.get_counts_rect(ymin, ymax, x1, x2, area=area,
                                                     mapdat=mapdat, dtcorrect=False)
            else:
                for i in range(step+1):
                    y1 = ymin + int(i*ny/step)
                    y2 = min(ymax, ymin + int((i+1)*ny/step))
                    if y1 >= y2: break
                    if hasattr(callback , '__call__'):
                        callback(i, step, nx*(y2-y1))
                    counts += self.get_counts_rect(y1, y2, xmin, xmax, area=area,
                                                     mapdat=mapdat, dtcorrect=False)
        if qdat is not None:
            counts = np.array([qdat,counts])

        return self._getXRD(mapname, counts, areaname, xrddir, **kws)

    def _getXRD(self, mapname, data, areaname, xrddir, **kws):

        name = '%s : %s' % (xrddir,areaname)
        
        if xrddir == 'xrd1D':
            _xrd = XRD(data1D=data, steps=data.shape[-1], name=name, **kws)
        else: #elif  xrddir == 'xrd2D':
            xpix,ypix = data.shape
            _xrd = XRD(data2D=data, xpixels=xpix, ypixels=ypix, name=name, **kws)

        _xrd.areaname = _xrd.title = name
        path, fname = os.path.split(self.filename)
        _xrd.filename = fname
        fmt = "Data from File '%s', detector '%s', area '%s'"
        _xrd.info  =  fmt % (self.filename, mapname, name)

        return _xrd

    def get_pos(self, name, mean=True):
        '''return  position by name (matching 'roimap/pos_name' if
        name is a string, or using name as an index if it is an integer

        Parameters
        ---------
        name :       str    ROI name
        mean :       optional, bool [True]        return mean x-value

        with mean=True, and a positioner in the first two position,
        returns a 1-d array of mean x-values

        with mean=False, and a positioner in the first two position,
        returns a 2-d array of x values for each pixel
        '''
        index = -1
        if isinstance(name, int):
            index = name
        else:
            for ix, nam in enumerate(self.xrmmap['positions/name']):
                if nam.lower() == name.lower():
                    index = ix
                    break
        if index == -1:
            raise GSEXRM_Exception("Could not find position '%s'" % repr(name))
        pos = self.xrmmap['positions/pos'][:, :, index]
        if index in (0, 1) and mean:
            pos = pos.sum(axis=index)/pos.shape[index]
        return pos


    def build_xrd_roimap(self,xrd='1D'):

        detname = None
        xrdtype = 'xrd%s detector' % xrd

        roigroup = ensure_subgroup('roimap',self.xrmmap)
        for det,grp in zip(self.xrmmap.keys(),self.xrmmap.values()):
            if bytes2str(grp.attrs.get('type', '')).startswith(xrdtype):
                detname = det
                ds = ensure_subgroup(det,roigroup)
                ds.attrs['type'] = xrdtype
        return roigroup,detname

    def add_xrd2Droi(self, xyrange, roiname, unit='pixels'):

        if version_ge(self.version, '2.0.0'):
            if not self.flag_xrd2d:
                return

            roigroup,detname = self.build_xrd_roimap(xrd='2D')
            xrmdet = self.xrmmap[detname]

            if roiname in roigroup[detname]:
                raise ValueError("Name '%s' exists in 'roimap/%s' arrays." % (roiname,detname))

            xyrange = [int(x) for x in xyrange]
            xmin,xmax,ymin,ymax = xyrange

            xrd2d_counts = xrmdet['counts'][:,:,slice(xmin,xmax),slice(ymin,ymax)]
            xrd2d_counts = xrd2d_counts.sum(axis=2).sum(axis=2)
            if abs(xmax-xmin) > 0 and abs(ymax-ymin) > 0:
                xrd2d_cor = xrd2d_counts/(abs(xmax-xmin)*abs(ymax-ymin))
            else:
                xrd2d_cor = xrd2d_counts

            self.save_roi(roiname,detname,xrd2d_counts,xrd2d_cor,xyrange,'area','pixels')
        else:
            print('Only compatible with newest hdf5 mapfile version.')


    def read_xrd1D_ROIFile(self,filename,verbose=False):

        roidat = readROIFile(filename,xrd=True)
        print('\nReading 1D-XRD ROI file: %s' % filename)
        for iroi, label, xunit, xrange in roidat:
            print(' Adding ROI: %s' % label)
            self.add_xrd1Droi(xrange,label,unit=xunit)
        print('Finished.\n')

    def add_xrd1Droi(self, xrange, roiname, unit='q'):

        if version_ge(self.version, '2.0.0'):
            if not self.flag_xrd1d:
                print('No 1D-XRD data in file')
                return

            if self.mono_energy is None:
                env_names = list(self.xrmmap['config/environ/name'])
                env_vals  = list(self.xrmmap['config/environ/value'])
                for name, val in zip(env_names, env_vals):
                    name = str(name).lower()
                if ('mono.energy' in name or 'mono energy' in name):
                    self.mono_energy = float(val)/1000.

            if unit.startswith('2th'): ## 2th to 1/A
                qrange = q_from_twth(xrange,lambda_from_E(self.mono_energy))
            elif unit == 'd':           ## A to 1/A
                qrange = q_from_d(xrange)
            else:
                qrange = xrange

            roigroup,detname  = self.build_xrd_roimap(xrd='1D')
            xrmdet = self.xrmmap[detname]

            if roiname in roigroup[detname]:
                raise ValueError("Name '%s' exists in 'roimap/%s' arrays." % (roiname,detname))

            qaxis = xrmdet['q'][:]
            imin = (np.abs(qaxis-qrange[0])).argmin()
            imax = (np.abs(qaxis-qrange[1])).argmin()+1
            xrd1d_counts = xrmdet['counts'][:,:,slice(imin,imax)].sum(axis=2)
            if abs(imax-imin) > 0:

                A = (xrmdet['counts'][:,:,imin]+xrmdet['counts'][:,:,imax])/2
                B = abs(imax-imin)

                ## cor = ( raw - AB ) / B = ( raw/B ) - A

                xrd1d_counts = xrd1d_counts / B ## divides by number of channels
                xrd1d_cor    = xrd1d_counts - A ## subtracts 'average' background
            else:
                xrd1d_cor = xrd1d_counts

            self.save_roi(roiname,detname,xrd1d_counts,xrd1d_cor,qrange,'q','1/A')
        else:
            print('Only compatible with newest hdf5 mapfile version.')

    def del_all_xrd1Droi(self):

        ''' delete all 1D-XRD ROI'''

        roigrp_xrd1d = ensure_subgroup('xrd1D',self.xrmmap['roimap'])

        for roiname in roigrp_xrd1d.keys():
            self.del_xrd1Droi(roiname)

    def del_xrd1Droi(self, roiname):

        ''' delete a 1D-XRD ROI'''

        roigrp_xrd1d = ensure_subgroup('xrd1D',self.xrmmap['roimap'])

        if roiname not in roigrp_xrd1d.keys():
            print("No ROI named '%s' found to delete" % roiname)
            return

        roiname = h5str(roiname)
        if roiname in roigrp_xrd1d:
            del roigrp_xrd1d[roiname]
            self.h5root.flush()


    def save_roi(self,roiname,det,raw,cor,range,type,units):

        ds = ensure_subgroup(roiname,self.xrmmap['roimap'][det])
        ds.create_dataset('raw',    data=raw   )
        ds.create_dataset('cor',    data=cor   )
        ds.create_dataset('limits', data=range )
        ds['limits'].attrs['type']  = type
        ds['limits'].attrs['units'] = units

        self.h5root.flush()

    def build_mca_roimap(self):

        det_list = []
        sumdet = None

        roigroup = ensure_subgroup('roimap',self.xrmmap)
        for det,grp in zip(self.xrmmap.keys(),self.xrmmap.values()):
            if bytes2str(grp.attrs.get('type', '')).startswith('mca det'):
                det_list   += [det]
                ds = ensure_subgroup(det,roigroup)
                ds.attrs['type'] = 'mca detector'
            if bytes2str(grp.attrs.get('type', '')).startswith('virtual mca'):
                sumdet = det
                ds = ensure_subgroup(det,roigroup)
                ds.attrs['type'] = 'virtual mca detector'

        return roigroup,det_list,sumdet

    def add_xrfroi(self, Erange, roiname, unit='keV'):

        if not self.flag_xrf:
            return

        if unit == 'eV': Erange[:] = [x/1000. for x in Erange] ## eV to keV

        roigroup,det_list,sumdet  = self.build_mca_roimap()

        if 'sum_name' in roigroup and roiname in roigroup['sum_name']:
            raise ValueError("Name '%s' exists in 'roimap/sum_name' arrays." % roiname)
        for det in det_list+[sumdet]:
            if roiname in roigroup[det]:
                raise ValueError("Name '%s' exists in 'roimap/%s' arrays." % (roiname,det))

        roi_limits,dtfctrs,icounts = [],[],[]
        for det in det_list:
            xrmdet = self.xrmmap[det]
            if unit.startswith('chan'):
                imin,imax = Erange
            else:
                Eaxis = xrmdet['energy'][:]

                imin = (np.abs(Eaxis-Erange[0])).argmin()
                imax = (np.abs(Eaxis-Erange[1])).argmin()+1


            roi_limits += [[int(imin), int(imax)]]
            dtfctrs += [xrmdet['dtfactor']]
            icounts += [np.array(xrmdet['counts'][:])]

        detraw = [icnt[:,:,slice(*islc)].sum(axis=2)        for icnt,islc        in zip(icounts,roi_limits)]
        detcor = [icnt[:,:,slice(*islc)].sum(axis=2)*dtfctr for icnt,islc,dtfctr in zip(icounts,roi_limits,dtfctrs)]
        detraw = np.einsum('kij->ijk', detraw)
        detcor = np.einsum('kij->ijk', detcor)

        sumraw = detraw.sum(axis=2)
        sumcor = detcor.sum(axis=2)

        for i,det in enumerate(det_list):
            self.save_roi(roiname,det,detraw[:,:,i],detcor[:,:,i],Erange,'energy',unit)
        if sumdet is not None:
            self.save_roi(roiname,sumdet,sumraw,sumcor,Erange,'energy',unit)

    def check_roi(self, roiname, det=None):

        if (type(det) is str and det.isdigit()) or type(det) is int:
            det = int(det)
            detname = 'mca%i' % det
        else:
            detname = det

        if roiname is not None: roiname = roiname.lower()

        if version_ge(self.version, '2.0.0'):
            if detname is not None:
                detname = detname.replace('det','mca')

            for sclr in self.xrmmap['scalars']:
                if roiname == sclr.lower():
                    return sclr.strip('_raw'),'scalars'

            if detname is None:
                detname = 'roimap/mcasum'
            elif not detname.startswith('roimap'):
                detname = 'roimap/%s' % detname

            try:
                roi_list = [r for r in self.xrmmap[detname]]
                if roiname is None:
                    return roi_list,detname
                if roiname not in roi_list:
                    for roi in roi_list:
                        if roi.lower().startswith(roiname):
                            roiname = roi
            except:
                ## provide summed output counts if fail
                detname = 'roimap/mcasum'
                roiname = 'outputcounts'

        else:
            if detname is not None:
                detname = detname.replace('mca','det')

            sum_roi = [h5str(r).lower() for r in self.xrmmap['roimap/sum_name']]
            det_roi = [h5str(r).lower() for r in self.xrmmap['roimap/det_name']]

            if roiname not in sum_roi:
                if roiname is None:
                    return np.arange(len(sum_roi)),'roimap/sum_'
                else:
                    for roi in sum_roi:
                        if roi.startswith(roiname):
                            roiname = roi

            if detname in ['det1','det2','det3','det4']:
                idet = int(''.join([i for i in detname if i.isdigit()]))
                detname = 'roimap/det_'

                if roiname not in det_roi:
                    roiname = '%s (mca%i)' % (roiname,idet)
                roiname = det_roi.index(roiname)

            else:
                detname = 'roimap/sum_'
                try:
                    roiname = sum_roi.index(roiname)
                except:
                    roiname = sum_roi.index('outputcounts')

        return roiname, detname


    def get_roimap(self, roiname, det=None, hotcols=False, dtcorrect=True):
        '''extract roi map for a pre-defined roi by name

        Parameters
        ---------
        roiname    :  str                       ROI name
        det        :  str                       detector name
        dtcorrect  :  optional, bool [True]     dead-time correct data
        hotcols    :  optional, bool [False]    suppress hot columns

        Returns
        -------
        ndarray for ROI data
        '''

        #scan_version = getattr(self, 'scan_version', 1.00)
        #hotcols = hotcols or scan_version < 1.36

        if roiname == '1' or roiname == 1:
            map = np.ones(self.xrmmap['positions']['pos'][:].shape[:-1])
            if hotcols:
                return map[:, 1:-1]
            else:
                return map

        roi,det = self.check_roi(roiname,det)

        if type(roiname) is str:
            if roiname.endswith('raw'): dtcorrect = False
        ext = 'cor' if dtcorrect else 'raw'

        if version_ge(self.version, '2.0.0'):
            if det.startswith('roimap'):
                roi_ext = '%s/' + ext
            else:
                roi_ext = '%s_' + ext if ext is 'raw' else '%s'

            if type(roi) is list:
                all_roi = []
                for iroi in roi:
                    iroi = '%s/%s'
                    if hotcols:
                        all_roi += [self.xrmmap[det][roi_ext % iroi][:, 1:-1]]
                    else:
                        all_roi += [self.xrmmap[det][roi_ext % iroi][:, :]]
                return np.array(all_roi)

            try:
                if hotcols:
                    return self.xrmmap[det][roi_ext % roi][:, 1:-1]
                else:
                    return self.xrmmap[det][roi_ext % roi][:, :]
            except:
                print('specified ROI not found. returning array of ones.')
                return np.ones(self.xrmmap['positions']['pos'][:].shape[:-1])

        else:
            detname = '%s%s' % (det,ext)

            if hotcols:
                return self.xrmmap[detname][:, 1:-1, roi]
            else:
                return self.xrmmap[detname][:, :, roi]


    def get_mca_erange(self, det=None, dtcorrect=True,
                       emin=None, emax=None, by_energy=True):
        '''extract map for an ROI set here, by energy range:

        not implemented
        '''
        pass

    def get_rgbmap(self, rroi, groi, broi, det=None, rdet=None, gdet=None, bdet=None,
                   hotcols=True, dtcorrect=True, scale_each=True, scales=None):
        '''return a (NxMx3) array for Red, Green, Blue from named
        ROIs (using get_roimap).

        Parameters
        ----------
        rroi :       str    name of ROI for red channel
        groi :       str    name of ROI for green channel
        broi :       str    name of ROI for blue channel
        det  :       optional, None or int [None]  index for detector
        dtcorrect :  optional, bool [True]         dead-time correct data
        hotcols   :  optional, bool [True]         suppress hot columns
        scale_each : optional, bool [True]
                     scale each map separately to span the full color range.
        scales :     optional, None or 3 element tuple [None]
                     multiplicative scale for each map.

        By default (scales_each=True, scales=None), each map is scaled by
        1.0/map.max() -- that is 1 of the max value for that map.

        If scales_each=False, each map is scaled by the same value
        (1/max intensity of all maps)

        '''
        if det is not None: rdet = gdet = bdet = det

        rmap = self.get_roimap(rroi, det=rdet, hotcols=hotcols, dtcorrect=dtcorrect)
        gmap = self.get_roimap(groi, det=gdet, hotcols=hotcols, dtcorrect=dtcorrect)
        bmap = self.get_roimap(broi, det=bdet, hotcols=hotcols, dtcorrect=dtcorrect)

        if scales is None or len(scales) != 3:
            scales = (1./rmap.max(), 1./gmap.max(), 1./bmap.max())
        if scale_each:
            rmap *= scales[0]
            gmap *= scales[1]
            bmap *= scales[2]
        else:
            scale = min(scales[0], scales[1], scales[2])
            rmap *= scale
            bmap *= scale
            gmap *= scale

        return np.array([rmap, gmap, bmap]).swapaxes(0, 2).swapaxes(0, 1)

    def add_roi(self, name, high, low,  address='', det=1,
                overwrite=False, **kws):
        '''add named ROI to an XRMMap file.
        These settings will be propogated through the
        ROI maps and all detectors.

        '''
        # data structures affected:
        #   config/rois/address
        #   config/rois/name
        #   config/rois/limits
        #   roimap/det_address
        #   roimap/det_name
        #   roimap/det_raw
        #   roimap/det_cor
        #   roimap/sum_list
        #   roimap/sum_name
        #   roimap/sum_raw
        #   roimap/sum_cor
        #   det{I}/roi_address      for I = 1, N_detectors (xrmmap attribute)
        #   det{I}/roi_name         for I = 1, N_detectors (xrmmap attribute)
        #   det{I}/roi_limits       for I = 1, N_detectors (xrmmap attribute)
        #   detsum/roi_address      for I = 1, N_detectors (xrmmap attribute)
        #   detsum/roi_name         for I = 1, N_detectors (xrmmap attribute)
        #   detsum/roi_limits       for I = 1, N_detectors (xrmmap attribute)

        roi_names = [i.lower().strip() for i in self.xrmmap['config/rois/name']]
        if name.lower().strip() in roi_name:
            if overwrite:
                self.del_roi(name)
            else:
                print("An ROI named '%s' exists, use overwrite=True to overwrite" % name)
                return
        #

    def del_roi(self, name):
        ''' delete an ROI'''
        roi_names = [i.lower().strip() for i in self.xrmmap['config/rois/name']]
        if name.lower().strip() not in roi_name:
            print("No ROI named '%s' found to delete" % name)
            return
        iroi = roi_name.index(name.lower().strip())
        roi_names = [i in self.xrmmap['config/rois/name']]
        roi_names.pop(iroi)

# 
# def update_xrmmap_file(xrmmap):
#     '''update dataset names, version, etc. in xrmmap file'''
# 
#     version = bytes2str(xrmmap.attrs.get('Version','0.0.0'))
# 
#     if version_ge('2.0.0', version):
# 
#         xrmmap['mca1'] = xrmmap['det1']
#         del xrmmap['det1']
#         xrmmap['mca2'] = xrmmap['det2']
#         del xrmmap['det2']
#         xrmmap['mca3'] = xrmmap['det3']
#         del xrmmap['det3']
#         xrmmap['mca4'] = xrmmap['det4']
#         del xrmmap['det4']
# 
#         xrmmap['mcasum'] = xrmmap['detsum']
#         del xrmmap['detsum']
# 
#         xrmmap.attrs['Version'] = '2.0.0'
#     else:
#         xrmmap.attrs['Version'] = '1.0.0'    


def read_xrfmap(filename, root=None):
    '''read GSE XRF FastMap data from HDF5 file or raw map folder'''
    key = 'filename'
    if os.path.isdir(filename):
        key = 'folder'
    kws = {key: filename, 'root': root}
    return GSEXRM_MapFile(**kws)

read_xrmmap = read_xrfmap

def read_fake1(filename, root=None):
    raise GSEXRM_Exception("GSEXMAP Error: %s" % filename)

def read_fake2(filename, root=None):
    raise ValueError("cannot open %s" % filename)

def process_mapfolder(path, take_ownership=False, **kws):
    """process a single map folder
    with optional keywords passed to GSEXRM_MapFile
    """
    try:
        kws['xrdcal'] = kws.pop('poni')
    except:
        pass
    if os.path.isdir(path) and isGSEXRM_MapFolder(path):
        print( '\n build map for: %s' % path)
        try:
            g = GSEXRM_MapFile(folder=path, **kws)
        except:
            print( 'Could not create MapFile')
            print( sys.exc_info() )
            return
        try:
            if take_ownership:
                g.take_ownership()
            if g.check_ownership():
                g.process()
            else:
                print( 'Skipping file %s: not owner' % path)
        except KeyboardInterrupt:
            sys.exit()
        except:
            print( 'Could not convert %s' % path)
            print( sys.exc_info() )
            return
        finally:
            g.close()

def process_mapfolders(folders, ncpus=None, take_ownership=False, **kws):
    """process a list of map folders
    with optional keywords passed to GSEXRM_MapFile
    """
    try:
        kws['xrdcal'] = kws.pop('poni')
    except:
        pass
    if ncpus is None:
        ncpus = max(1, mp.cpu_count()-1)
    if ncpus == 0:
        for path in folders:
            process_mapfolder(path, **kws)
    else:
        pool = mp.Pool(ncpus)
        kws['take_ownership'] = take_ownership
        myfunc = partial(process_mapfolder, **kws)
        pool.map(myfunc, folders)


def registerLarchPlugin():
    return ('_io', {'read_xrfmap': read_xrfmap,
                    'read_xrmmap': read_xrmmap,
                    'read_fake1': read_fake1,
                    'read_fake2': read_fake2,
                    'process_mapfolder': process_mapfolder,
                    'process_mapfolders': process_mapfolders})

