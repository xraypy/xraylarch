import sys
import os
import socket
import time
import datetime
import h5py
import numpy as np
from scipy import constants
import scipy.stats as stats
import json
import larch
from larch.utils.debugtime import debugtime

from larch_plugins.io import nativepath, new_filename
from larch_plugins.xrf import MCA, ROI

from larch_plugins.xrmmap import (FastMapConfig, read_xrf_netcdf,
                                  read_xsp3_hdf5, readASCII,
                                  readMasterFile, readROIFile,
                                  readEnvironFile, parseEnviron,
                                  read_xrd_netcdf) #, read_xrd_hdf5)

from larch_plugins.diFFit.xrd import XRD

HAS_pyFAI = False
try:
    import pyFAI
    HAS_pyFAI = True
except ImportError:
    pass

NINIT = 32
#COMPRESSION_LEVEL = 4
COMPRESSION_LEVEL = 'lzf' ## faster but larger files;mkak 2016.08.19
DEFAULT_ROOTNAME = 'xrmmap'

def h5str(obj):
    """strings stored in an HDF5 from Python2 may look like
     "b'xxx'", that is containg "b".  strip these out here
    """
    out = str(obj)
    if out.startswith("b'") and out.endswith("'"):
        out = out[2:-1]
    return out

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
    """return status, top-level group, and version"""
    # set defaults for file does not exist
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
        vers = group.attrs['Version']
        if folder is not None and folder != group.attrs['Map_Folder']:
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
    has_xrfdata = False
    for f in ('xmap.0001', 'xsp3.0001'):
        if f in flist: has_xrfdata = True
    return has_xrfdata

def isGSEXRM_XRDMapFolder(fname):
    "return whether folder a valid Scan Folder (raw data)"
    if (fname is None or not os.path.exists(fname) or
        not os.path.isdir(fname)):
        return False
    flist = os.listdir(fname)
    has_xrddata = False
    for f in ('xrd_001.nc','xrd_001.h5'):
        if f in flist: has_xrddata = True
    return has_xrddata

H5ATTRS = {'Type': 'XRM 2D Map',
           'Version': '1.4.0',
           'Title': 'Epics Scan Data',
           'Beamline': 'GSECARS, 13-IDE / APS',
           'Start_Time':'',
           'Stop_Time':'',
           'Map_Folder': '',
           'Dimension': 2,
           'Process_Machine':'',
           'Process_ID': 0}

def create_xrmmap(h5root, root=None, dimension=2, folder='', start_time=None):
    """creates a skeleton '/xrmmap' group in an open HDF5 file

    This is left as a function, not method of GSEXRM_MapFile below
    because it may be called by the mapping collection program
    (ie, from collector.py) when a map is started

    This leaves a structure to be filled in by
    GSEXRM_MapFile.init_xrmmap(),
    """
    attrs = {}
    attrs.update(H5ATTRS)
    if start_time is None:
        start_time = time.ctime()
    attrs.update({'Dimension':dimension, 'Start_Time':start_time,
                  'Map_Folder': folder, 'Last_Row': -1})
    if root in ('', None):
        root = DEFAULT_ROOTNAME
    xrmmap = h5root.create_group(root)

    xrmmap.create_group('flags')

    for key, val in attrs.items():
        xrmmap.attrs[key] = str(val)

    g = xrmmap.create_group('roimap')
    g.attrs['type'] = 'roi maps'
    g.attrs['desc'] = 'ROI data, including summed and deadtime corrected maps'

    g = xrmmap.create_group('config')
    g.attrs['type'] = 'scan config'
    g.attrs['desc'] = '''scan configuration, including scan definitions,
    ROI definitions, MCA calibration, Environment Data, etc'''

    xrmmap.create_group('areas')
    xrmmap.create_group('work')
    xrmmap.create_group('positions')

    conf = xrmmap['config']
    for name in ('scan', 'general', 'environ', 'positioners',
                 'motor_controller', 'rois', 'mca_settings', 'mca_calib'):
        conf.create_group(name)

    xrmmap.create_group('xrd')
    xrmmap['xrd'].attrs['desc'] = 'xrd detector calibration and data'
    xrmmap['xrd'].attrs['type'] = 'xrd detector'

    h5root.flush()

def checkFORattrs(attrib,group):
    try:
        group.attrs[attrib]
    except:
        group.attrs[attrib] = ''

def checkFORsubgroup(subgroup,group):
    try:
        group[subgroup]
    except:
         group.create_group(subgroup)


class GSEXRM_Exception(Exception):
    """GSEXRM Exception: General Errors"""
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
    def __str__(self):
        return self.msg

class GSEXRM_NotOwner(Exception):
    """GSEXRM Not Owner Host/Process ID"""
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = 'Not Owner of HDF5 file %s' % msg
    def __str__(self):
        return self.msg

class GSEXRM_MapRow:
    """
    read one row worth of data:
    """
    def __init__(self, yvalue, xrffile, xrdfile, xpsfile, sisfile, folder,
                 reverse=False, ixaddr=0, dimension=2,
                 npts=None,  irow=None, dtime=None, nrows_expected=None,
                 FLAGxrf = True, FLAGxrd = False):

        if not FLAGxrf and not FLAGxrd:
            return

        self.read_ok = False
        self.nrows_expected = nrows_expected

        npts_offset = 0

        self.npts = npts
        self.irow = irow
        self.yvalue = yvalue
        self.xrffile = xrffile
        self.xpsfile = xpsfile
        self.sisfile = sisfile
        self.xrdfile = xrdfile

        if FLAGxrf:
            xrf_reader = read_xsp3_hdf5
            if not xrffile.startswith('xsp'):
                xrf_reader = read_xrf_netcdf

        if FLAGxrd:
            xrd_reader = read_xrd_netcdf
            ## not yet implemented for hdf5 files
            ## mkak 2016.07.27
            #if not xrdfile.endswith('nc'):
            #    xrd_reader = read_xrd_hdf5

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

        xrfdat = None
        xmfile = os.path.join(folder, xrffile)
        xrddat = None
        xdfile = os.path.join(folder, xrdfile)

        while atime < 0 and time.time()-t0 < 10:
            try:
                atime = os.stat(xmfile).st_ctime

                if FLAGxrf:
                    xrfdat = xrf_reader(xmfile, npixels=self.nrows_expected, verbose=False)
                    if xrfdat is None:
                        print( 'Failed to read XRF data from %s' % self.xrffile)

                if FLAGxrd:
                    xrddat = xrd_reader(xdfile, verbose=False)
                    if xrddat is None:
                        print( 'Failed to read XRD data from %s' % self.xrdfile)

            except (IOError, IndexError):
                time.sleep(0.010)

        if atime < 0:
            print( 'Failed to read data.')
            return
        if dtime is not None:  dtime.add('maprow: read XRM files')

        ## SPECIFIC TO XRF data
        if FLAGxrf:
            self.counts    = xrfdat.counts # [:]
            self.inpcounts = xrfdat.inputCounts[:]
            self.outcounts = xrfdat.outputCounts[:]

            # times are extracted from the netcdf file as floats of ms
            # here we truncate to nearest ms (clock tick is 0.32 ms)
            self.livetime  = (xrfdat.liveTime[:]).astype('int')
            self.realtime  = (xrfdat.realTime[:]).astype('int')

            dt_denom = xrfdat.outputCounts*xrfdat.liveTime
            dt_denom[np.where(dt_denom < 1)] = 1.0
            self.dtfactor  = xrfdat.inputCounts*xrfdat.realTime/dt_denom

        ## SPECIFIC TO XRD data
        if FLAGxrd:
            if self.npts - xrddat.shape[0] == 0:
                self.xrd2d     = xrddat
            else:
                # print 'XRD row has %i points, but it requires %i points.' % (xrddat.shape[0],self.npts)
                self.xrd2d = np.zeros((self.npts,xrddat.shape[1],xrddat.shape[2]))
                self.xrd2d[0:xrddat.shape[0]] = xrddat

        gnpts, ngather  = gdata.shape
        snpts, nscalers = sdata.shape
        xnpts, nmca, nchan = self.counts.shape
        if self.npts is None:
            self.npts = min(gnpts, xnpts)

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
            if FLAGxrd:
                self.xrd2d = self.xrd2d[:self.npts]

        points = range(1, self.npts+1)
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
            if FLAGxrd:
                self.xrd2d = self.xrd2d[::-1]


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
    """Detector class, representing 1 detector element (real or virtual)
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

    """
    def __init__(self, xrmmap, index=None):
        self.xrmmap = xrmmap
        self.__ndet =  xrmmap.attrs['N_Detectors']
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
        """deadtime factor"""
        return self.__getval('dtfactor')

    @property
    def realtime(self):
        """real time"""
        return self.__getval('realtime')

    @property
    def livetime(self):
        """live time"""
        return self.__getval('livetime')

    @property
    def inputcounts(self):
        """inputcounts"""
        return self.__getval('inputcounts')

    @property
    def outputcount(self):
        """output counts"""
        return self.__getval('outputcounts')


class GSEXRM_Area(object):
    """Map Area class, representing a map area for a detector
    """
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
    """
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
    >>> fe  = map.get_roimap('Fe')
    >>> as  = map.get_roimap('As Ka', det=1, dtcorrect=True)
    >>> rgb = map.get_rgbmap('Fe', 'Ca', 'Zn', det=None, dtcorrect=True, scale_each=False)
    >>> en  = map.get_energy(det=1)

    All these take the following options:

       det:         which detector element to use (1, 2, 3, 4, None), [None]
                    None means to use the sum of all detectors
       dtcorrect:   whether to return dead-time corrected spectra     [True]

    """

    ScanFile   = 'Scan.ini'
    EnvFile    = 'Environ.dat'
    ROIFile    = 'ROI.dat'
    MasterFile = 'Master.dat'

    def __init__(self, filename=None, folder=None, root=None, chunksize=None,
                 FLAGxrf=True, FLAGxrd=False):

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
        self.pixeltime        = None
        self.dt               = debugtime()
        self.masterfile       = None
        self.masterfile_mtime = -1

        self.calibration = None
        self.xrdmask = None
        self.xrdbkgd = None
        self.flag_xrf = FLAGxrf
        self.flag_xrd = FLAGxrd

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
                cfile.Save(os.path.join(self.folder, self.ScanFile))
            self.h5root = h5py.File(self.filename)

            if self.dimension is None and isGSEXRM_MapFolder(self.folder):
                self.read_master()

            print('')

            create_xrmmap(self.h5root, root=self.root, dimension=self.dimension,
                          folder=self.folder, start_time=self.start_time)

            self.status = GSEXRM_FileStatus.created
            self.open(self.filename, root=self.root, check_status=False)
        else:
            raise GSEXRM_Exception('GSEXMAP Error: could not locate map file or folder')

    def get_det(self, index):
        return GSEMCA_Detector(self.xrmmap, index=index)

    def area_obj(self, index, det=None):
        return GSEXRM_Area(self.xrmmap, index, det=det)

    def get_scanconfig(self):
        """return scan configuration from file"""
        conftext = self.xrmmap['config/scan/text'].value
        return FastMapConfig(conftext=conftext)

    def get_coarse_stages(self):
        """return coarse stage positions for map"""
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
        """open GSEXRM HDF5 File :
        with check_status=False, this **must** be called
        for an existing, valid GSEXRM HDF5 File!!
        """
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
            self.folder = self.xrmmap.attrs['Map_Folder']
        self.last_row = int(self.xrmmap.attrs['Last_Row'])

        try:
            self.dimension = self.xrmmap['config/scan/dimension'].value
        except:
            pass

        if (len(self.rowdata) < 1 or
            (self.dimension is None and isGSEXRM_MapFolder(self.folder))):
            self.read_master()

    def close(self):
        if self.check_hostid():
            self.xrmmap.attrs['Process_Machine'] = ''
            self.xrmmap.attrs['Process_ID'] = 0
            self.xrmmap.attrs['Last_Row'] = self.last_row
        self.h5root.close()
        self.h5root = None

    def readEDFfile(self,name='mask',keyword='maskfile'):

        edffile = self.xrmmap['xrd'].attrs[keyword]
        print('Reading %s file: %s' % (name,edffile))

        try:
            import fabio
            rawdata = fabio.open(edffile).data
        except:
            print('File must be .edf format; user must have fabio installed.')
        print('\t Shape: %s' % str(np.shape(rawdata)))

        try:
            del self.xrmmap['xrd'][name]
        except:
            pass
        self.xrmmap['xrd'].create_dataset(name, data=np.array(rawdata))

    def add_calibration(self):
        """
        adds calibration to exisiting '/xrmmap' group in an open HDF5 file
        mkak 2016.11.16
        """

        checkFORsubgroup('xrd',self.xrmmap)
        xrdgrp = self.xrmmap['xrd']

        checkFORattrs('calfile',xrdgrp)

        xrdcal = False
        if self.calibration and xrdgrp.attrs['calfile'] != self.calibration:
            print('New calibration file detected: %s' % self.calibration)
            xrdgrp.attrs['calfile'] = '%s' % (self.calibration)
            if os.path.exists(xrdgrp.attrs['calfile']):
                xrdcal = True


        if HAS_pyFAI and xrdcal:
            try:
                ai = pyFAI.load(xrdgrp.attrs['calfile'])
            except:
                print('Not recognized as a pyFAI calibration file: %s' % self.calibration)
                pass

            try:
                xrdgrp.attrs['detector'] = ai.detector.name
            except:
                xrdgrp.attrs['detector'] = ''
            try:
                xrdgrp.attrs['spline']   = ai.detector.splineFile
            except:
                xrdgrp.attrs['spline']   = ''
            xrdgrp.attrs['ps1']        = ai.detector.pixel1 ## units: m
            xrdgrp.attrs['ps2']        = ai.detector.pixel2 ## units: m
            xrdgrp.attrs['distance']   = ai._dist ## units: m
            xrdgrp.attrs['poni1']      = ai._poni1
            xrdgrp.attrs['poni2']      = ai._poni2
            xrdgrp.attrs['rot1']       = ai._rot1
            xrdgrp.attrs['rot2']       = ai._rot2
            xrdgrp.attrs['rot3']       = ai._rot3
            xrdgrp.attrs['wavelength'] = ai._wavelength ## units: m
            ## E = hf ; E = hc/lambda
            hc = constants.value(u'Planck constant in eV s') * \
                   constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
            xrdgrp.attrs['energy']    = hc/(ai._wavelength) ## units: keV

        print('')
        self.h5root.flush()


    def add_data(self, group, name, data, attrs=None, **kws):
        """ creata an hdf5 dataset"""
        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)
        kwargs = {'compression': COMPRESSION_LEVEL}
        kwargs.update(kws)
        d = group.create_dataset(name, data=data, **kwargs)
        if isinstance(attrs, dict):
            for key, val in attrs.items():
                d.attrs[key] = val
        return d

    def add_map_config(self, config):
        """add configuration from Map Folder to HDF5 file
        ROI, DXP Settings, and Config data
        """
        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)

        group = self.xrmmap['config']
        scantext = open(os.path.join(self.folder, self.ScanFile), 'r').read()
        for name, sect in (('scan', 'scan'),
                           ('general', 'general'),
                           ('positioners', 'slow_positioners'),
                           ('motor_controller', 'xps')):
            for key, val in config[sect].items():
                group[name].create_dataset(key, data=val)

        group['scan'].create_dataset('text', data=scantext)

        roidat, calib, extra = readROIFile(os.path.join(self.folder, self.ROIFile))
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

        self.add_data(group['rois'], 'name',     roi_desc)
        self.add_data(group['rois'], 'address',  roi_addr)
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

        self.add_data(group['environ'], 'name',     env_desc)
        self.add_data(group['environ'], 'address',  env_addr)
        self.add_data(group['environ'], 'value',     env_val)
        self.h5root.flush()

    def initialize_xrmmap(self):
        """ initialize '/xrmmap' group in HDF5 file, generally
        possible once at least 1 row of raw data is available
        in the scan folder.
        """
        if self.status == GSEXRM_FileStatus.hasdata:
            return
        if self.status != GSEXRM_FileStatus.created:
            print( 'Warning, cannot initialize xrmmap yet.')
            return

        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)

        if (len(self.rowdata) < 1 or
            (self.dimension is None and isGSEXRM_MapFolder(self.folder))):
            self.read_master()
        if len(self.rowdata) < 1:
            return

        self.last_row = -1
        self.add_map_config(self.mapconf)
        row = self.read_rowdata(0)
        self.build_schema(row,verbose=True)

        self.add_rowdata(row)

        self.status = GSEXRM_FileStatus.hasdata

    def process(self, maxrow=None, force=False, callback=None, verbose=True):
        "look for more data from raw folder, process if needed"

        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)

        if self.status == GSEXRM_FileStatus.created:
            self.initialize_xrmmap()
        if (force or len(self.rowdata) < 1 or
            (self.dimension is None and isGSEXRM_MapFolder(self.folder))):
            self.read_master()
        nrows = len(self.rowdata)
        if maxrow is not None:
            nrows = min(nrows, maxrow)
        if force or self.folder_has_newdata():
            irow = self.last_row + 1
            while irow < nrows:
                # self.dt.add('=>PROCESS %i' % irow)
                if hasattr(callback, '__call__'):
                    callback(row=irow, maxrow=nrows,
                             filename=self.filename, status='reading')
                row = self.read_rowdata(irow)
                # self.dt.add('  == read row data')
                if hasattr(callback, '__call__'):
                    callback(row=irow, maxrow=nrows,
                             filename=self.filename, status='complete')

                if row.read_ok:
                    self.add_rowdata(row, verbose=verbose)
                    irow  = irow + 1
                else:
                    print("==Warning: Read failed at row %i" % irow)
                    break
            # self.dt.show()
        self.resize_arrays(self.last_row+1)
        self.h5root.flush()
        if self.pixeltime is None:
            self.calc_pixeltime()
        print(datetime.datetime.fromtimestamp(time.time()).strftime('End: %Y-%m-%d %H:%M:%S'))

    def calc_pixeltime(self):
        scanconf = self.xrmmap['config/scan']
        rowtime = float(scanconf['time1'].value)
        start = float(scanconf['start1'].value)
        stop = float(scanconf['stop1'].value)
        step = float(scanconf['step1'].value)
        npts = 1 + int((abs(stop - start) + 1.1*step)/step)
        self.pixeltime = rowtime/npts
        return self.pixeltime

    def read_rowdata(self, irow):
        """read a row's worth of raw data from the Map Folder
        returns arrays of data
        """
        try:
            self.flag_xrf
        except:
            self.reset_flags()


        if self.dimension is None or irow > len(self.rowdata):
            self.read_master()

        if self.folder is None or irow >= len(self.rowdata):
            return

        if self.flag_xrf and self.flag_xrd:
            yval, xrff, sisf, xpsf, xrdf, etime = self.rowdata[irow]
        elif self.flag_xrf:
            yval, xrff, sisf, xpsf, etime = self.rowdata[irow]
            xrdf = ''
        else:
            raise IOError('No XRF or XRD flags provided.')
            return
        reverse = (irow % 2 != 0)

        return GSEXRM_MapRow(yval, xrff, xrdf, xpsf, sisf, self.folder,
                             irow=irow, nrows_expected=self.nrows_expected,
                             ixaddr=self.ixaddr, dimension=self.dimension,
                             npts=self.npts, reverse=reverse,
                             FLAGxrf = self.flag_xrf, FLAGxrd = self.flag_xrd)


    def add_rowdata(self, row, verbose=True):
        """adds a row worth of real data"""
        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)

        if not self.flag_xrf and not self.flag_xrd:
            return

        thisrow = self.last_row + 1
        pform = 'Add row %4i, yval=%s' % (thisrow+1, row.yvalue)
        if self.flag_xrf:
            pform = '%s, xrffile=%s' % (pform,row.xrffile)
        if self.flag_xrd:
            pform = '%s, xrdfile=%s' % (pform,row.xrdfile)
        print(pform)

        t0 = time.time()
        if self.flag_xrf:

            nmca, xnpts, nchan = row.counts.shape
            xrm_dets = []

            nrows = 0
            map_items = sorted(self.xrmmap.keys())
            for gname in map_items:
                g = self.xrmmap[gname]
                if g.attrs.get('type', None) == 'mca detector':
                    xrm_dets.append(g)
                    nrows, npts, nchan =  g['counts'].shape

            if thisrow >= nrows:
                self.resize_arrays(32*(1+nrows/32))

            _nr, npts, nchan = xrm_dets[0]['counts'].shape
            npts = min(npts, xnpts, self.npts)
            for idet, grp in enumerate(xrm_dets):
                grp['dtfactor'][thisrow,  :npts]  = row.dtfactor[idet, :npts]
                grp['realtime'][thisrow,  :npts]  = row.realtime[idet, :npts]
                grp['livetime'][thisrow,  :npts]  = row.livetime[idet, :npts]
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

        t1 = time.time()

        if self.flag_xrd:
            ## Unneccessary at this point BUT convenient if two xrd detectors are used
            ## mkak 2016.08.03
            xrdgrp = self.xrmmap['xrd']

            xrdpts, xpixx, xpixy = row.xrd2d.shape
            xrdgrp['data2D'][thisrow,] = row.xrd2d

            if hasattr(self.xrmmap['xrd'],'maskfile'):
                mask = xrdgrp.attrs['maskfile']
            else:
                mask = None
            if hasattr(xrdgrp,'bkgdfile'):
                bkgd = xrdgrp.attrs['bkgdfile']
            else:
                bkgd = None

        t2 = time.time()
        if verbose:
            if self.flag_xrd and self.flag_xrf and hasattr(self.xrmmap['xrd'],'calfile'):
                pform = '\tXRF: %0.2f s; XRD: %0.2f s (%0.2f s); Total: %0.2f s'
                print(pform % (t1-t0,t2-t1,t2-t1a,t2-t0))
            elif self.flag_xrd and self.flag_xrf:
                pform = '\tXRF: %0.2f s; XRD: %0.2f s; Total: %0.2f s'
                print(pform % (t1-t0,t2-t1,t2-t0))
            #elif self.flag_xrf:
            #    pform = '\tTime: %0.2f s'
            #    print(pform % (t2-t0))
            elif self.flag_xrd:
                pform = '\t2D XRD: %0.2f s; 1D XRD %0.2f s; Total: %0.2f s'
                print(pform % (t1a-t0,t2-t1a,t2-t0))

        self.last_row = thisrow
        self.xrmmap.attrs['Last_Row'] = thisrow
        self.h5root.flush()

    def build_schema(self, row, verbose=False):
        """build schema for detector and scan data"""
        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)

        print('XRM Map Folder: %s' % self.folder)
        xrmmap = self.xrmmap

        flaggp = xrmmap['flags']
        flaggp.attrs['xrf'] = self.flag_xrf
        flaggp.attrs['xrd'] = self.flag_xrd

        if self.npts is None:
            self.npts = row.npts
        npts = self.npts

        conf   = self.xrmmap['config']

        if self.flag_xrf:
            nmca, xnpts, nchan = row.counts.shape
            if verbose:
                prtxt = '--- Build XRF Schema: %i, %i ---- MCA: (%i, %i)'
                print(prtxt % (npts, row.npts, nmca, nchan))

            if self.chunksize is None:
                if xnpts < 10: xnpts=10
                nxx = min(xnpts-1, 2**int(np.log2(xnpts)))
                nxm = 1024
                if nxx > 256:
                    nxm = min(1024, int(65536*1.0/ nxx))
                self.chunksize = (1, nxx, nxm)
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
                self.add_data(dgrp, 'roi_name',    roi_names)
                self.add_data(dgrp, 'roi_address', [s % (imca+1) for s in roi_addrs])
                self.add_data(dgrp, 'roi_limits',  roi_limits[:,imca,:])

                dgrp.create_dataset('counts', (NINIT, npts, nchan), np.int16,
                                    compression=COMPRESSION_LEVEL,
                                    chunks=self.chunksize,
                                    maxshape=(None, npts, nchan))
                for name, dtype in (('realtime', np.int),  ('livetime', np.int),
                                    ('dtfactor', np.float32),
                                    ('inpcounts', np.float32),
                                    ('outcounts', np.float32)):
                    dgrp.create_dataset(name, (NINIT, npts), dtype,
                                        compression=COMPRESSION_LEVEL,
                                        maxshape=(None, npts))

            # add 'virtual detector' for corrected sum:
            dgrp = xrmmap.create_group('detsum')
            dgrp.attrs['type'] = 'virtual mca'
            dgrp.attrs['desc'] = 'deadtime corrected sum of detectors'
            en = 1.0*offset[0] + slope[0]*1.0*en_index
            self.add_data(dgrp, 'energy', en, attrs={'cal_offset':offset[0],
                                                     'cal_slope': slope[0]})
            self.add_data(dgrp, 'roi_name',    roi_names)
            self.add_data(dgrp, 'roi_address', [s % 1 for s in roi_addrs])
            self.add_data(dgrp, 'roi_limits',  roi_limits[: ,0, :])
            dgrp.create_dataset('counts', (NINIT, npts, nchan), np.int16,
                                compression=COMPRESSION_LEVEL,
                                chunks=self.chunksize,
                                maxshape=(None, npts, nchan))
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

            self.add_data(scan, 'det_name',    det_desc)
            self.add_data(scan, 'det_address', det_addr)
            self.add_data(scan, 'sum_name',    sums_desc)
            self.add_data(scan, 'sum_list',    sums_list)

            nxx = min(nsca, 8)
            for name, nx, dtype in (('det_raw', nsca, np.int32),
                                    ('det_cor', nsca, np.float32),
                                    ('sum_raw', nsum, np.int32),
                                    ('sum_cor', nsum, np.float32)):
                scan.create_dataset(name, (NINIT, npts, nx), dtype,
                                    compression=COMPRESSION_LEVEL,
                                    chunks=(2, npts, nx),
                                    maxshape=(None, npts, nx))

            # positions
            pos = xrmmap['positions']
            for pname in ('mca realtime', 'mca livetime'):
                self.pos_desc.append(pname)
                self.pos_addr.append(pname)
            npos = len(self.pos_desc)
            self.add_data(pos, 'name',     self.pos_desc)
            self.add_data(pos, 'address',  self.pos_addr)
            pos.create_dataset('pos', (NINIT, npts, npos), dtype,
                               compression=COMPRESSION_LEVEL,
                               maxshape=(None, npts, npos))

        if self.flag_xrd:

            if self.calibration:
                self.add_calibration()

            xrdpts, xpixx, xpixy = row.xrd2d.shape
            self.chunksize_2DXRD    = (1, 1, xpixx, xpixy)

            if verbose:
                prtxt = '--- Build XRD Schema: %i, %i ---- 2D:  (%i, %i)'
                print(prtxt % (npts, row.npts, xpixx, xpixy))

            xrmmap['xrd'].create_dataset('data2D',(xrdpts, xrdpts, xpixx, xpixy), np.uint16,
                                   chunks = self.chunksize_2DXRD,
                                   compression=COMPRESSION_LEVEL)

        print(datetime.datetime.fromtimestamp(time.time()).strftime('\nStart: %Y-%m-%d %H:%M:%S'))

        self.h5root.flush()

    def check_flags(self):
        '''
        check if any XRD OR XRF data in mapfile
        mkak 2016.10.13
        '''
        print( 'running: self.check_flags()')

        try:
            xrdgp = self.xrmmap['xrd']
            xrddata = xrdgp['data2D']
            self.flag_xrd = True
        except:
            self.flag_xrd = False
        try:
            xrfgp = self.xrmmap['xrf']
            xrfdata = xrdgp['det1']
            self.flag_xrf = True
        except:
            self.flag_xrf = False

        self.xrmmap['flags'].attrs['xrf'] = self.flag_xrf
        self.xrmmap['flags'].attrs['xrd'] = self.flag_xrd
        self.h5root.flush()

    def reset_flags(self):
        '''
        Resets the flags according to hdf5; add in flags to hdf5 files missing them.
        mkak 2016.08.30
        '''
        xrmmap = self.xrmmap
        try:
            xrmmap['flags']
        except:
            check_flags(self)

        self.flag_xrf = self.xrmmap['flags'].attrs['xrf']
        self.flag_xrd = self.xrmmap['flags'].attrs['xrd']

    def resize_arrays(self, nrow):
        "resize all arrays for new nrow size"
        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)
        realmca_groups = []
        virtmca_groups = []
        for g in self.xrmmap.values():
            # include both real and virtual mca detectors!
            if g.attrs.get('type', '').startswith('mca det'):
                realmca_groups.append(g)
            elif g.attrs.get('type', '').startswith('virtual mca'):
                virtmca_groups.append(g)
        # print('resize arrays ', realmca_groups)
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

    def ensure_workgroup(self):
        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)
        if not 'work' in self.xrmmap:
            self.xrmmap.create_group('work')
        return self.xrmmap['work']

    def add_work_array(self, data, name, **kws):
        """
        add an array to the work group of processed arrays
        """
        workgroup = self.ensure_workgroup()
        if name is None:
            name = 'array_%3.3i' % (1+len(workgroup))
        if name in workgroup:
            raise ValueError("array name '%s' exists in work arrays" % name)
        ds = workgroup.create_dataset(name, data=data)
        for key, val in kws.items():
            ds.attrs[key] = val
        self.h5root.flush()

    def del_work_array(self, name):
        """
        delete an array to the work group of processed arrays
        """
        workgroup = self.ensure_workgroup()
        name = h5str(name)
        if name in workgroup:
            del workgroup[name]
            self.h5root.flush()

    def get_work_array(self, name):
        """
        get an array from the work group of processed arrays by index or name
        """
        workgroup = self.ensure_workgroup()
        dat = None
        name = h5str(name)
        if name in workgroup:
            dat = workgroup[name]
        return dat

    def work_array_names(self):
        """
        return list of work array descriptions
        """
        workgroup = self.ensure_workgroup()
        return [h5str(g) for g in workgroup.keys()]

    def add_area(self, mask, name=None, desc=None):
        """add a selected area, with optional name
        the area is encoded as a boolean array the same size as the map

        """
        if not self.check_hostid():
            raise GSEXRM_NotOwner(self.filename)

        group = self.xrmmap['areas']
        if name is None:
            name = 'area_001'
        if len(group) > 0:
            count = len(group)
            while name in group and count < 9999:
                name = 'area_%3.3i' % (count)
                count += 1
        ds = group.create_dataset(name, data=mask)
        if desc is None:
            desc = name
        ds.attrs['description'] = desc
        self.h5root.flush()
        return name

    def export_areas(self, filename=None):
        """export areas to datafile """
        if filename is None:
            filename = "%s_Areas.npz" % self.filename
        group = self.xrmmap['areas']
        kwargs = {}
        for aname in group:
            kwargs[aname] = group[aname][:]
        np.savez(filename, **kwargs)
        return filename

    def import_areas(self, filename, overwrite=False):
        """import areas from datafile exported by export_areas()"""
        npzdat = np.load(filename)
        current_areas = self.xrmmap['areas']
        othername = os.path.split(filename)[1]

        if othername.endswith('.h5_Areas.npz'):
            othername = othername.replace('.h5_Areas.npz', '')
        for aname in npzdat.files:
            mask = npzdat[aname]
            outname = '%s_%s' % (aname, othername)
            self.add_area(mask, name=outname, desc=outname)

    def get_area(self, name=None, desc=None):
        """
        get area group by name or description
        """
        group = self.xrmmap['areas']
        if name is not None and name in group:
            return group[name]
        if desc is not None:
            for name in group:
                if desc == group[name].attrs['description']:
                    return group[name]
        return None

    def get_calibration(self, verbose=True):
        """
        return name of calibration file
        """
        try:
            calibration = self.xrmmap['xrd'].attrs['calfile']
            if verbose:
                print('Calibration file: %s' % calibration)
                if HAS_pyFAI:
                    print(pyFAI.load(calibration))
        except:
            return None
        return calibration

    def get_area_stats(self, name=None, desc=None):
        """return statistics for all raw detector counts/sec values

        for each raw detector returns
           name, length, mean, standard_deviation,
           median, mode, minimum, maximum,
           gmean, hmean, skew, kurtosis

        """
        area = self.get_area(name=name, desc=desc)
        if area is None:
            return None

        if 'roistats' in area.attrs:
            return json.loads(area.attrs['roistats'])

        amask = area.value

        roidata = []
        d_addrs = [d.lower() for d in self.xrmmap['roimap/det_address']]
        d_names = [d for d in self.xrmmap['roimap/det_name']]
        # count times
        ctime = [1.e-6*self.xrmmap['roimap/det_raw'][:,:,0][amask]]
        for i in range(self.xrmmap.attrs['N_Detectors']):
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

    def claim_hostid(self):
        "claim ownershipf of file"
        if self.xrmmap is None:
            return
        self.xrmmap.attrs['Process_Machine'] = socket.gethostname()
        self.xrmmap.attrs['Process_ID'] = os.getpid()
        self.h5root.flush()

    def take_ownership(self):
        "claim ownershipf of file"
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
        """checks host and id of file:
        returns True if this process the owner of the file
        """
        if self.xrmmap is None:
            return
        attrs = self.xrmmap.attrs
        self.folder = attrs['Map_Folder']

        file_mach = attrs['Process_Machine']
        file_pid  = attrs['Process_ID']
        if len(file_mach) < 1 or file_pid < 1:
            self.claim_hostid()
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

        self.master_header = header
        self.rowdata = rows
        if self.flag_xrd:
            xrd_files = [fn for fn in os.listdir(self.folder) if fn.endswith('nc')]
            for i,addxrd in enumerate(xrd_files):
                self.rowdata[i].insert(4,addxrd)
        self.scan_version = '1.0'
        self.nrows_expected = None
        self.start_time = time.ctime()
        for line in header:
            words = line.split('=')
            if 'scan.starttime' in words[0].lower():
                self.start_time = words[1].strip()
            elif 'scan.version' in words[0].lower():
                self.scan_version = words[1].strip()
            elif 'scan.nrows_expected' in words[0].lower():
                self.nrows_expected = int(words[1].strip())

        self.folder_modtime = os.stat(self.masterfile).st_mtime
        self.stop_time = time.ctime(self.folder_modtime)

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

    def _det_group(self, det=None):
        "return  XRMMAP group for a detector"
        dgroup= 'detsum'
        if self.ndet is None:
            self.ndet =  self.xrmmap.attrs['N_Detectors']
        if det in range(1, self.ndet+1):
            dgroup = 'det%i' % det
        return self.xrmmap[dgroup]

    def get_energy(self, det=None):
        """return energy array for a detector"""
        group = self._det_group(det)
        return group['energy'].value

    def get_shape(self):
        """returns NY, NX shape of array data"""
        ny, nx, npos = self.xrmmap['positions/pos'].shape
        return ny, nx

    def get_mca_area(self, areaname, det=None, dtcorrect=True, callback = None):
        """return XRF spectra as MCA() instance for
        spectra summed over a pre-defined area

        Parameters
        ---------
        areaname :   str       name of area
        det :        optional, None or int         index of detector
        dtcorrect :  optional, bool [True]         dead-time correct data

        Returns
        -------
        MCA object for XRF counts in area

        """

        try:
            area = self.get_area(areaname).value
        except:
            raise GSEXRM_Exception("Could not find area '%s'" % areaname)

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
                                           mapdat=mapdat, det=det, area=area,
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
        return self._getmca(mapdat, counts, areaname, npixels=npix,
                            real_time=rtime, live_time=ltime)

    def get_mca_rect(self, ymin, ymax, xmin, xmax, det=None, dtcorrect=True):
        """return mca counts for a map rectangle, optionally

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

        """

        mapdat = self._det_group(det)
        counts = self.get_counts_rect(ymin, ymax, xmin, xmax, mapdat=mapdat,
                                      det=det, dtcorrect=dtcorrect)
        name = 'rect(y=[%i:%i], x==[%i:%i])' % (ymin, ymax, xmin, xmax)
        npix = (ymax-ymin+1)*(xmax-xmin+1)
        ltime, rtime = self.get_livereal_rect(ymin, ymax, xmin, xmax, det=det,
                                              dtcorrect=dtcorrect, area=None)

        return self._getmca(mapdat, counts, name, npixels=npix,
                            real_time=rtime, live_time=ltime)


    def get_counts_rect(self, ymin, ymax, xmin, xmax, mapdat=None, det=None,
                     area=None, dtcorrect=True):
        """return counts for a map rectangle, optionally
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
        """
        if mapdat is None:
            mapdat = self._det_group(det)

        nx, ny = (xmax-xmin, ymax-ymin)
        sx = slice(xmin, xmax)
        sy = slice(ymin, ymax)

        ix, iy, nmca = mapdat['counts'].shape
        cell   = mapdat['counts'].regionref[sy, sx, :]
        counts = mapdat['counts'][cell]
        counts = counts.reshape(ny, nx, nmca)
        if dtcorrect:
            if det in range(1, self.ndet+1):
                cell   = mapdat['dtfactor'].regionref[sy, sx]
                dtfact = mapdat['dtfactor'][cell].reshape(ny, nx)
                dtfact = dtfact.reshape(dtfact.shape[0], dtfact.shape[1], 1)
                counts = counts * dtfact
            elif det is None: # indicating sum of deadtime-corrected spectra
                _md    = self._det_group(self.ndet)
                cell   = _md['counts'].regionref[sy, sx, :]
                _cts   = _md['counts'][cell].reshape(ny, nx, nmca)
                cell   = _md['dtfactor'].regionref[sy, sx]
                dtfact = _md['dtfactor'][cell].reshape(ny, nx)
                dtfact = dtfact.reshape(dtfact.shape[0], dtfact.shape[1], 1)
                counts = _cts * dtfact
                for _idet in range(1, self.ndet):
                    _md    = self._det_group(_idet)
                    cell   = _md['counts'].regionref[sy, sx, :]
                    _cts   = _md['counts'][cell].reshape(ny, nx, nmca)
                    cell   = _md['dtfactor'].regionref[sy, sx]
                    dtfact = _md['dtfactor'][cell].reshape(ny, nx)
                    dtfact = dtfact.reshape(dtfact.shape[0], dtfact.shape[1], 1)
                    counts += _cts * dtfact

        elif det is None: # indicating sum un-deadtime-corrected spectra
            _md    = self._det_group(self.ndet)
            cell   = _md['counts'].regionref[sy, sx, :]
            counts = _md['counts'][cell].reshape(ny, nx, nmca)
            for _idet in range(1, self.ndet):
                _md    = self._det_group(_idet)
                cell   = _md['counts'].regionref[sy, sx, :]
                _cts   = _md['counts'][cell].reshape(ny, nx, nmca)
                counts += _cts

        if area is not None:
            counts = counts[area[sy, sx]]
        else:
            counts = counts.sum(axis=0)
        return counts.sum(axis=0)

    def get_livereal_rect(self, ymin, ymax, xmin, xmax, det=None,
                          area=None, dtcorrect=True):
        """return livetime, realtime for a map rectangle, optionally
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

        """
        # need real size, not just slice values, for np.zeros()
        shape = self._det_group(1)['livetime'].shape
        if ymax < 0: ymax += shape[0]
        if xmax < 0: xmax += shape[1]
        nx, ny = (xmax-xmin, ymax-ymin)
        sx = slice(xmin, xmax)
        sy = slice(ymin, ymax)
        if det is None:
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

    def _getmca(self, map, counts, name, npixels=None, **kws):
        """return an MCA object for a detector group
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

        """
        # map  = self.xrmmap[dgroup]
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

        # a workaround for poor practice -- some '1.3.0' files
        # were built with 'roi_names', some with 'roi_name'
        roiname = 'roi_name'
        if roiname not in map:
            roiname = 'roi_names'
        roinames = list(map[roiname])
        roilims  = list(map['roi_limits'])
        for roi, lims in zip(roinames, roilims):
            _mca.add_roi(roi, left=lims[0], right=lims[1])
        _mca.areaname = _mca.title = name
        path, fname = os.path.split(self.filename)
        _mca.filename = fname
        fmt = "Data from File '%s', detector '%s', area '%s'"
        mapname = map.name.split('/')[-1]
        _mca.info  =  fmt % (self.filename, mapname, name)
        return _mca

    def check_xrf(self):
        """
        check if any XRF data in mapfile; returns flags
        mkak 2016.10.06
        """

        try:
            xrfgp = self.xrmmap['xrf']
            data = xrfgp['det1']
        except:
            return False
        return True

    def check_xrd(self):
        """
        check if any XRD data in mapfile; returns flags for 1D and 2D XRD data
        mkak 2016.09.07
        """

        try:
            xrdgrp = self.xrmmap['xrd']
            data2D = xrdgrp['data2D']
            flag2D = True
        except:
            flag2D = False

        try:
            xrdgrp = self.xrmmap['xrd']
            xrdgrp['data1D']
            flag1D = True
        except:
            if flag2D:
                try:
                    xrdgrp.attrs['calfile']
                    flag1D = True
                except:
                    flag1D = False
            else:
                flag1D = False

        return flag1D,flag2D


    def get_xrd_area(self, areaname, callback = None):
        """return 2D XRD pattern for a pre-defined area

        Parameters
        ---------
        areaname :   str       name of area

        Returns
        -------
        2D diffraction pattern for given area

        """

        try:
            area = self.get_area(areaname).value
        except:
            raise GSEXRM_Exception("Could not find area '%s'" % areaname)
            return

        mapdat = self.xrmmap['xrd']
        ix, iy, xpix, ypix = mapdat['data2D'].shape

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
                frames = self.get_frames_rect(ymin, ymax, xmin, xmax,
                                           mapdat=mapdat, area=area)
            except MemoryError:
                use_chunks = True
        if use_chunks:
            frames = np.zeros([xpix,ypix])
            if nx > ny:
                for i in range(step+1):
                    x1 = xmin + int(i*nx/step)
                    x2 = min(xmax, xmin + int((i+1)*nx/step))
                    if x1 >= x2: break
                    if hasattr(callback , '__call__'):
                        callback(i, step, (x2-x1)*ny)
                    frames += self.get_frames_rect(ymin, ymax, x1, x2,
                                                mapdat=mapdat, area=area)
            else:
                for i in range(step+1):
                    y1 = ymin + int(i*ny/step)
                    y2 = min(ymax, ymin + int((i+1)*ny/step))
                    if y1 >= y2: break
                    if hasattr(callback , '__call__'):
                        callback(i, step, nx*(y2-y1))
                    frames += self.get_frames_rect(y1, y2, xmin, xmax,
                                                mapdat=mapdat, area=area)

        return self._getXRD(mapdat, frames, areaname, xpixels=xpix, ypixels=ypix)

    def get_frames_rect(self, ymin, ymax, xmin, xmax, mapdat=None, area=None):
        """return summed frames for a map rectangle, optionally
        applying area mask and deadtime correction

        Parameters
        ---------
        ymin :       int       low y index
        ymax :       int       high y index
        xmin :       int       low x index
        xmax :       int       high x index
        mapdat :     optional, None or map data
        area :       optional, None or area object  area for mask

        Returns
        -------
        summed 2D XRD frames for rectangle

        Does *not* check for errors!

        Note:  if mapdat is None, the map data is taken from the 'xrd/data2D' parameter
        """
        if mapdat is None:
            mapdat = self.xrmmap['xrd']

        nx, ny = (xmax-xmin, ymax-ymin)
        sx = slice(xmin, xmax)
        sy = slice(ymin, ymax)

        ix, iy, xpix, ypix = mapdat['data2D'].shape
        #ix, iy, nmca = mapdat['counts'].shape

        cell   = mapdat['data2D'].regionref[sy, sx, :]
        frames = mapdat['data2D'][cell]
        frames = frames.reshape(ny, nx, xpix, ypix)

        if area is not None:
            frames = frames[area[sy, sx]]
        else:
            frames = frames.sum(axis=0)

        return frames.sum(axis=0)

    def _getXRD(self, map, frames, areaname, xpixels=2048, ypixels=2048):

        name = ('xrd: %s' % areaname)
        _2Dxrd = XRD(data2D=frames, xpixels=xpixels, ypixels=ypixels, name=name)

        _2Dxrd.areaname = _2Dxrd.title = name
        path, fname = os.path.split(self.filename)
        _2Dxrd.filename = fname
        fmt = "Data from File '%s', detector '%s', area '%s'"
        mapname = map.name.split('/')[-1]
        _2Dxrd.info  =  fmt % (self.filename, mapname, name)

        return _2Dxrd

    def get_pattern_rect(self, ymin, ymax, xmin, xmax, mapdat=None, area=None):
        """return summed 1D XRD pattern for a map rectangle, optionally
        applying area mask and deadtime correction

        Parameters
        ---------
        ymin :       int       low y index
        ymax :       int       high y index
        xmin :       int       low x index
        xmax :       int       high x index
        mapdat :     optional, None or map data
        area :       optional, None or area object  area for mask

        Returns
        -------
        summed 1D XRD pattern for rectangle

        Does *not* check for errors!

        Note:  if mapdat is None, the map data is taken from the 'xrd/data1D' parameter
        """
        if mapdat is None:
            mapdat = self.xrmmap['xrd']

        nx, ny = (xmax-xmin, ymax-ymin)
        sx = slice(xmin, xmax)
        sy = slice(ymin, ymax)

        ix, iy, nwedge, nchan = mapdat['data1D'].shape

        cell    = mapdat['data1D'].regionref[sy, sx, :]
        pattern = mapdat['data1D'][cell]
        pattern = pattern.reshape(ny, nx, nwedge, nchan)

        if area is not None:
            pattern = pattern[area[sy, sx]]
        else:
            pattern = pattern.sum(axis=0)
        return pattern.sum(axis=0)

    def _get1Dxrd(self, map, pattern, areaname, nwedge=2, nchan=5001):

        name = ('xrd: %s' % areaname)
        _1Dxrd = XRD(data1D=pattern, nwedge=nwedge, nchan=nchan, name=name)

        _1Dxrd.areaname = _1Dxrd.title = name
        path, fname = os.path.split(self.filename)
        _1Dxrd.filename = fname
        fmt = "Data from File '%s', detector '%s', area '%s'"
        mapname = map.name.split('/')[-1]
        _1Dxrd.info  =  fmt % (self.filename, mapname, name)

        return _1Dxrd

    def get_pos(self, name, mean=True):
        """return  position by name (matching 'roimap/pos_name' if
        name is a string, or using name as an index if it is an integer

        Parameters
        ---------
        name :       str    ROI name
        mean :       optional, bool [True]        return mean x-value

        with mean=True, and a positioner in the first two position,
        returns a 1-d array of mean x-values

        with mean=False, and a positioner in the first two position,
        returns a 2-d array of x values for each pixel
        """
        index = -1
        if isinstance(name, int):
            index = name
        else:
            for ix, nam in enumerate(self.xrmmap['positions/name']):
                if nam.lower() == nam.lower():
                    index = ix
                    break

        if index == -1:
            raise GSEXRM_Exception("Could not find position '%s'" % repr(name))
        pos = self.xrmmap['positions/pos'][:, :, index]
        if index in (0, 1) and mean:
            pos = pos.sum(axis=index)/pos.shape[index]
        return pos

    def get_roimap(self, name, det=None, no_hotcols=True, dtcorrect=True):
        """extract roi map for a pre-defined roi by name

        Parameters
        ---------
        name :       str    ROI name
        det  :       optional, None or int [None]  index for detector
        dtcorrect :  optional, bool [True]         dead-time correct data
        no_hotcols   optional, bool [True]         suprress hot columns

        Returns
        -------
        ndarray for ROI data
        """
        imap = -1
        roi_names = [h5str(r).lower() for r in self.xrmmap['config/rois/name']]
        det_names = [h5str(r).lower() for r in self.xrmmap['roimap/sum_name']]
        work_names = self.work_array_names()
        dat = 'roimap/sum_raw'

        # scaler, non-roi data
        if name.lower() in det_names and name.lower() not in roi_names:
            imap = det_names.index(name.lower())
            if no_hotcols:
                return self.xrmmap[dat][:, 1:-1, imap]
            else:
                return self.xrmmap[dat][:, :, imap]
        elif name in work_names:
            map = self.get_work_array(name)
            if no_hotcols and len(map.shape)==2:
                map = map[:, 1:-1]
            return map

        dat = 'roimap/sum_raw'
        if dtcorrect:
            dat = 'roimap/sum_cor'

        if self.ndet is None:
            self.ndet =  self.xrmmap.attrs['N_Detectors']

        if det in range(1, self.ndet+1):
            name = '%s (mca%i)' % (name, det)
            det_names = [h5str(r).lower() for r in self.xrmmap['roimap/det_name']]
            dat = 'roimap/det_raw'
            if dtcorrect:
                dat = 'roimap/det_cor'

        imap = det_names.index(name.lower())
        if imap < 0:
            raise GSEXRM_Exception("Could not find ROI '%s'" % name)

        if no_hotcols:
            return self.xrmmap[dat][:, 1:-1, imap]
        else:
            return self.xrmmap[dat][:, :, imap]

    def get_mca_erange(self, det=None, dtcorrect=True,
                       emin=None, emax=None, by_energy=True):
        """extract map for an ROI set here, by energy range:

        not implemented
        """
        pass

    def get_rgbmap(self, rroi, groi, broi, det=None, no_hotcols=True,
                   dtcorrect=True, scale_each=True, scales=None):
        """return a (NxMx3) array for Red, Green, Blue from named
        ROIs (using get_roimap).

        Parameters
        ----------
        rroi :       str    name of ROI for red channel
        groi :       str    name of ROI for green channel
        broi :       str    name of ROI for blue channel
        det  :       optional, None or int [None]  index for detector
        dtcorrect :  optional, bool [True]         dead-time correct data
        no_hotcols   optional, bool [True]         suprress hot columns
        scale_each : optional, bool [True]
                     scale each map separately to span the full color range.
        scales :     optional, None or 3 element tuple [None]
                     multiplicative scale for each map.

        By default (scales_each=True, scales=None), each map is scaled by
        1.0/map.max() -- that is 1 of the max value for that map.

        If scales_each=False, each map is scaled by the same value
        (1/max intensity of all maps)

        """
        rmap = self.get_roimap(rroi, det=det, no_hotcols=no_hotcols,
                               dtcorrect=dtcorrect)
        gmap = self.get_roimap(groi, det=det, no_hotcols=no_hotcols,
                               dtcorrect=dtcorrect)
        bmap = self.get_roimap(broi, det=det, no_hotcols=no_hotcols,
                               dtcorrect=dtcorrect)

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
        """add named ROI to an XRMMap file.
        These settings will be propogated through the
        ROI maps and all detectors.

        """
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
        """ delete an ROI"""
        roi_names = [i.lower().strip() for i in self.xrmmap['config/rois/name']]
        if name.lower().strip() not in roi_name:
            print("No ROI named '%s' found to delete" % name)
            return
        iroi = roi_name.index(name.lower().strip())
        roi_names = [i in self.xrmmap['config/rois/name']]
        roi_names.pop(iroi)

def read_xrfmap(filename, root=None):
    """read GSE XRF FastMap data from HDF5 file or raw map folder"""
    key = 'filename'
    if os.path.isdir(filename):
        key = 'folder'
    kws = {key: filename, 'root': root}
    return GSEXRM_MapFile(**kws)

def registerLarchPlugin():
    return ('_xrf', {'read_xrfmap': read_xrfmap})
