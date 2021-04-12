from __future__ import print_function
import os
import sys
import uuid
import time
import h5py
import numpy as np
import scipy.stats as stats
import json
import multiprocessing as mp
from functools import partial

import larch
from larch.utils import debugtime, isotime
from larch.utils.strutils import fix_filename, bytes2str, version_ge

from larch.io import (nativepath, new_filename, read_xrf_netcdf,
                      read_xsp3_hdf5, read_xrd_netcdf, read_xrd_hdf5)

from larch.xrf import MCA, ROI
from .configfile import FastMapConfig
from .asciifiles import (readASCII, readMasterFile, readROIFile,
                         readEnvironFile, parseEnviron)

from .gsexrm_utils import (GSEXRM_MCADetector, GSEXRM_Area, GSEXRM_Exception,
                           GSEXRM_MapRow, GSEXRM_FileStatus)

from ..xrd import (XRD, E_from_lambda, integrate_xrd_row, q_from_twth,
                   q_from_d, lambda_from_E, read_xrd_data)

from larch.math.tomography import tomo_reconstruction, reshape_sinogram, trim_sinogram

DEFAULT_XRAY_ENERGY = 39987.0  # probably means x-ray energy was not found in meta data
NINIT = 32
COMPRESSION_OPTS = 2
COMPRESSION = 'gzip'
#COMPRESSION = 'lzf'
DEFAULT_ROOTNAME = 'xrmmap'
VALID_ROOTNAMES = ('xrmmap', 'xrfmap')
EXTRA_DETGROUPS =  ('scalars', 'work', 'xrd1d', 'xrd2d')
NOT_OWNER = "Not Owner of HDF5 file %s"
QSTEPS = 2048

H5ATTRS = {'Type': 'XRM 2D Map',
           'Version': '2.1.0',
           # 'Version': '2.0.0',
           # 'Version': '1.0.1',
           'Title': 'Epics Scan Data',
           'Beamline': 'GSECARS, 13-IDE / APS',
           'Start_Time': '',
           'Stop_Time': '',
           'Map_Folder': '',
           'Dimension': 2,
           'Process_Machine': '',
           'Process_ID': 0,
           'Compression': ''}

def h5str(obj):
    '''strings stored in an HDF5 from Python2 may look like
     "b'xxx'", that is containg "b".  strip these out here
    '''
    out = str(obj)
    if out.startswith("b'") and out.endswith("'"):
        out = out[2:-1]
    return out

def get_machineid():
    "machine id / MAC address, independent of hostname"
    return hex(uuid.getnode())[2:]

def strlist(alist):
    return [a.encode('utf-8') for a in alist]

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


def test_h5group(group, folder=None):
    "test h5 group as a XRM Map"
    valid = ('config' in group and 'roimap' in group)
    for attr in  ('Version', 'Map_Folder', 'Dimension', 'Start_Time'):
        valid = valid and attr in group.attrs
    if not valid:
        return None, None
    status = GSEXRM_FileStatus.hasdata
    vers = h5str(group.attrs.get('Version',''))
    fullpath = group.attrs.get('Map_Folder','')
    _parent, _folder = os.path.split(fullpath)
    if folder is not None and folder != _folder:
        status = GSEXRM_FileStatus.wrongfolder
    return status, vers


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

    g = xrmmap.create_group('areas')
    g.attrs['type'] = 'areas'

    g = xrmmap.create_group('positions')
    g.attrs['type'] = 'position arrays'

    g = xrmmap.create_group('scalars')
    g.attrs['type'] = 'scalar detectors'

    g = xrmmap.create_group('work')
    g.attrs['type'] = 'virtual detectors for work/analysis arrays'

    conf = xrmmap['config']
    for name in ('scan', 'general', 'environ', 'positioners', 'notes',
                 'motor_controller', 'rois', 'mca_settings', 'mca_calib'):
        conf.create_group(name)
    h5root.flush()

def ensure_subgroup(subgroup, group, dtype='virtual detector'):
    if subgroup not in group.keys():
        g = group.create_group(subgroup)
        g.attrs['type'] = dtype
        return g
    else:
        g = group[subgroup]
        if 'type' not in g.attrs:
            g.attrs['type'] = dtype
        return g

def toppath(pname, n=4):
    words = []
    for i in range(n):
        pname, f = os.path.split(pname)
        words.append(f)
    return '/'.join(words)


def remove_zigzag(map, zigzag=0):
    if zigzag == 0:
        return map
    nrows, ncols = map.shape
    tmp = 1.0 * map
    even = 0
    if zigzag < 0:
        even = 1
        zigzag = -zigzag
    for i in range(nrows):
        if (i % 2) == even:
            tmp[i, :] = map[i, :]
        else:
            tmp[i, zigzag:]  = map[i, :-zigzag]
    return tmp


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
    XRDCALFile = 'XRD.poni'
    MasterFile = 'Master.dat'

    def __init__(self, filename=None, folder=None, create_empty=False,
                 hotcols=False, zigzag=0, dtcorrect=True, root=None,
                 chunksize=None, xrdcal=None, xrd2dmask=None, xrd2dbkgd=None,
                 xrd1dbkgd=None, azwdgs=0, qstps=QSTEPS, flip=True,
                 bkgdscale=1., has_xrf=True, has_xrd1d=False, has_xrd2d=False,
                 compression=COMPRESSION, compression_opts=COMPRESSION_OPTS,
                 facility='APS', beamline='13-ID-E', run='', proposal='',
                 user='', scandb=None, all_mcas=False, **kws):

        self.filename      = filename
        self.folder        = folder
        self.root          = root
        self.chunksize     = chunksize
        # whether to remove first and last columns from data
        self.hotcols       = hotcols
        # whether to shift rows to fix zig-zag
        self.zigzag        = zigzag
        self.dtcorrect     = dtcorrect
        self.scandb        = scandb
        self.envvar        = None
        self.status        = GSEXRM_FileStatus.err_notfound
        self.dimension     = None
        self.nmca          = None
        self.npts          = None
        self.start_time    = None
        self.xrmmap        = None
        self.h5root        = None
        self.last_row      = -1
        self.rowdata       = []
        self.roi_names     = {}
        self.roi_slices    = None
        self._pixeltime    = None
        self.masterfile    = None
        self.force_no_dtc  = False
        self.all_mcas      = all_mcas
        self.detector_list = None

        self.compress_args = {'compression': compression}
        if compression != 'lzf':
            self.compress_args['compression_opts'] = compression_opts

        self.incident_energy = None
        self.has_xrf       = has_xrf
        self.has_xrd1d     = has_xrd1d
        self.has_xrd2d     = has_xrd2d
        self.pos_desc = []
        self.pos_addr = []
        ## used for XRD
        self.bkgd_xrd2d    = None
        self.bkgd_xrd1d    = None
        self.mask_xrd2d    = None
        self.xrdcalfile    = None
        self.xrd2dmaskfile = None
        self.xrd2dbkgdfile = None
        self.xrd1dbkgdfile = None
        self.bkgdscale     = bkgdscale if bkgdscale > 0 else 1.
        self.azwdgs        = 0 if azwdgs > 36 or azwdgs < 2 else int(azwdgs)
        self.qstps         = int(qstps)
        self.flip          = flip
        self.master_modtime = -1

        ## used for tomography orientation
        self.x           = None
        self.reshape     = None
        self.notes = {'facility'   : facility,
                      'beamline'   : beamline,
                      'run'        : run,
                      'proposal'   : proposal,
                      'user'       : user}

        nmaster = -1
        # initialize from filename or folder
        if self.filename is not None:
            self.getFileStatus(root=root)
            # print("Get File Status ", root, self.status)
            if self.status == GSEXRM_FileStatus.empty:
                ftmp = open(self.filename, 'r')
                self.folder = ftmp.readlines()[0][:-1].strip()
                if '/' in self.folder:
                    self.folder = self.folder.split('/')[-1]
                ftmp.close()
                os.unlink(self.filename)

        if (self.status==GSEXRM_FileStatus.err_notfound and
            self.filename is not None and self.folder is None and
            isGSEXRM_MapFolder(self.filename)):
                self.folder = self.filename
                self.filename = None

        if isGSEXRM_MapFolder(self.folder):
            nmaster = self.read_master()
            if self.filename is None:
                raise GSEXRM_Exception(
                    "'%s' is not a valid GSEXRM Map folder" % self.folder)
            self.getFileStatus(root=root)

        # for existing file, read initial settings
        if self.status in (GSEXRM_FileStatus.hasdata,
                           GSEXRM_FileStatus.created):
            self.open(self.filename, root=self.root, check_status=True)
            self.reset_flags()
            return

        # file exists but is not hdf5
        if self.status ==  GSEXRM_FileStatus.err_nothdf5:
            raise GSEXRM_Exception(
                "'%s' is not a readable HDF5 file" % self.filename)

        # file has no write permission
        if self.status ==  GSEXRM_FileStatus.err_nowrite:
            raise GSEXRM_Exception(
                "'%s' does not have write access" % self.filename)

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

            if nmaster < 1:
                self.read_master()
            if self.status == GSEXRM_FileStatus.wrongfolder:
                self.filename = new_filename(self.filename)
                cfile = FastMapConfig()
                cfile.Read(os.path.join(self.folder, self.ScanFile))
                cfile.config['scan']['filename'] = self.filename
                # cfile.Save(os.path.join(self.folder, self.ScanFile))
            print("Create HDF5 File  ")
            self.h5root = h5py.File(self.filename, 'w')

            if self.dimension is None and isGSEXRM_MapFolder(self.folder):
                if nmaster < 1:
                    self.read_master()
            create_xrmmap(self.h5root, root=self.root, dimension=self.dimension,
                          folder=self.folder, start_time=self.start_time)

            # cfile = FastMapConfig()
            # self.add_map_config(cfile.config, nmca=nmca)

            self.notes['h5_create_time'] = isotime()
            self.status = GSEXRM_FileStatus.created
            self.open(self.filename, root=self.root, check_status=False)

            for xkey, xval in zip(self.xrmmap.attrs.keys(), self.xrmmap.attrs.values()):
                if xkey == 'Version':
                    self.version = xval

            self.add_XRDfiles(xrdcalfile=xrdcal,
                              xrd2dmaskfile=xrd2dmask,
                              xrd2dbkgdfile=xrd2dbkgd,
                              xrd1dbkgdfile=xrd1dbkgd)
        elif (self.filename is not None and
              self.status == GSEXRM_FileStatus.err_notfound and create_empty):
            print("Create HDF5 File")
            self.h5root = h5py.File(self.filename, 'w')
            create_xrmmap(self.h5root, root=None, dimension=2, start_time=self.start_time)
            self.notes['h5_create_time'] = isotime()
            self.xrmmap = self.h5root[DEFAULT_ROOTNAME]
            self.take_ownership()
            # self.status = GSEXRM_FileStatus.created
            cfile = FastMapConfig()
            self.add_map_config(cfile.config, nmca=1)
            self.open(self.filename, root=self.root, check_status=False)
            self.reset_flags()

        else:
            raise GSEXRM_Exception('GSEXMAP Error: could not locate map file or folder')
        print("Initialized done ", self.status, self.version, self.root)

    def __repr__(self):
        fname = ''
        if self.filename is not None:
            fpath, fname = os.path.split(self.filename)
        return "GSEXRM_MapFile('%s')" % fname


    def getFileStatus(self, filename=None, root=None, folder=None):
        '''return status, top-level group, and version'''

        if filename is not None:
            self.filename = filename
        filename = self.filename
        folder = self.folder
        # print("getFileStatus 0 ", filename, folder)
        if folder is not None:
            folder = os.path.abspath(folder)
            parent, folder = os.path.split(folder)
        self.status = GSEXRM_FileStatus.err_notfound
        self.root, self.version = '', ''
        if root not in ('', None):
            self.root = root
        # see if file exists:
        if not (os.path.exists(filename) and os.path.isfile(filename)):
            return
        # see if file is empty/too small(signifies "read from folder")
        if os.stat(filename).st_size < 1024:
            self.status = GSEXRM_FileStatus.empty
            return

        if not os.access(filename, os.W_OK):
            self.status = GSEXRM_FileStatus.err_nowrite
            return

        # see if file is an H5 file
        try:
            fh = h5py.File(filename, 'r')
        except IOError:
            self.status = GSEXRM_FileStatus.err_nothdf5
            return

        status =  GSEXRM_FileStatus.no_xrfmap
        if root is not None and root in fh:
            stat, vers = test_h5group(fh[root], folder=folder)
            if stat is not None:
                self.status = stat
                self.root, self.version = root, vers
        else:
            for root, group in fh.items():
                stat, vers = test_h5group(group, folder=folder)
                if stat is not None:
                    self.status = stat
                    self.root, self.version = root, vers
                    break
        fh.close()
        return

    def get_det(self, index):
        return GSEXRM_MCADetector(self.xrmmap, index=index)

    def area_obj(self, index, det=None):
        return GSEXRM_Area(self.xrmmap, index, det=det)

    def get_coarse_stages(self):
        '''return coarse stage positions for map'''
        stages = []
        env_addrs = [h5str(s) for s in self.xrmmap['config/environ/address']]
        env_vals  = [h5str(s) for s in self.xrmmap['config/environ/value']]
        for addr, pname in self.xrmmap['config/positioners'].items():
            name = h5str(pname[()])
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
            self.getFileStatus(filename, root=root)
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
            self.dimension = self.xrmmap['config/scan/dimension'][()]
        except:
            pass

        if (len(self.rowdata) < 1 or
            (self.dimension is None and isGSEXRM_MapFolder(self.folder))):
            self.read_master()

        if self.nmca is None:
            self.nmca = self.xrmmap.attrs.get('N_Detectors', 1)

    def close(self):
        if self.check_hostid():
            self.xrmmap.attrs['Process_Machine'] = ''
            self.xrmmap.attrs['Process_ID'] = 0
            self.xrmmap.attrs['Last_Row'] = self.last_row
        try:
            self.h5root.close()
        except RuntimeError:
            print("Got Runtime Error ")
            print(sys.exc_info())

        self.h5root = None

    def add_XRDfiles(self, flip=None, xrdcalfile=None, xrd2dmaskfile=None,
                     xrd2dbkgdfile=None, xrd1dbkgdfile=None):
        '''
        adds mask file to exisiting '/xrmmap' group in an open HDF5 file
        mkak 2018.02.01
        '''
        xrd1dgrp = ensure_subgroup('xrd1d', self.xrmmap)

        if xrdcalfile is not None:
            self.xrdcalfile = xrdcalfile
        if os.path.exists(str(self.xrdcalfile)):
            print('Calibration file loaded: %s' % self.xrdcalfile)
            xrd1dgrp.attrs['calfile'] = str(self.xrdcalfile)


        self.flip = flip if flip is not None else self.flip

        if xrd1dbkgdfile is not None:
            self.xrd1dbkgdfile= xrd1dbkgdfile
        if os.path.exists(str(self.xrd1dbkgdfile)):
            print('xrd1d background file loaded: %s' % self.xrd1dbkgdfile)
            xrd1dgrp.attrs['1Dbkgdfile'] = '%s' % (self.xrd1dbkgdfile)
            self.bkgd_xrd1d = read_xrd_data(self.xrd1dbkgdfile)*self.bkgdscale

        if xrd2dbkgdfile is not None:
            self.xrd2dbkgdfile= xrd2dbkgdfile
        if os.path.exists(str(self.xrd2dbkgdfile)):
            print('2DXRD background file loaded: %s' % self.xrd2dbkgdfile)
            xrd1dgrp.attrs['2Dbkgdfile'] = '%s' % (self.xrd2dbkgdfile)
            self.bkgd_xrd2d = read_xrd_data(self.xrd2dbkgdfile)*self.bkgdscale

        if xrd2dmaskfile is not None:
            self.xrd2dmaskfile= xrd2dmaskfile
        if os.path.exists(str(self.xrd2dmaskfile)):
            print('Mask file loaded: %s' % self.xrd2dmaskfile)
            xrd1dgrp.attrs['maskfile'] = '%s' % (self.xrd2dmaskfile)
            self.mask_xrd2d = read_xrd_data(self.xrd2dmaskfile)

        self.h5root.flush()

    def add_data(self, group, name, data, attrs=None, **kws):
        ''' creata an hdf5 dataset, replacing existing dataset if needed'''
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        kws.update(self.compress_args)
        if name in group:
            del group[name]
        d = group.create_dataset(name, data=data, **kws)
        if isinstance(attrs, dict):
            for key, val in attrs.items():
                d.attrs[key] = val
        return d

    def add_map_config(self, config, nmca=None):
        '''add configuration from Map Folder to HDF5 file
        ROI, DXP Settings, and Config data
        '''
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        group = self.xrmmap['config']
        for name, sect in (('scan', 'scan'),
                           ('general', 'general'),
                           ('positioners', 'slow_positioners'),
                           ('motor_controller', 'xps')):
            for key, val in config[sect].items():
                if key in group[name]:
                    del group[name][key]
                group[name].create_dataset(key, data=val)

        scanfile = os.path.join(self.folder, self.ScanFile)
        if os.path.exists(scanfile):
            scantext = open(scanfile, 'r').read()
        else:
            scantext = ''
        if 'text' in group['scan']:
            del group['scan']['text']
        group['scan'].create_dataset('text', data=scantext)

        roifile = os.path.join(self.folder, self.ROIFile)
        self.nmca = 0
        if nmca is not None:
            self.nmca = nmca

        if os.path.exists(roifile):
            roidat, calib, extra = readROIFile(roifile)
            self.xrmmap.attrs['N_Detectors'] = self.nmca = len(calib['slope'])
            roi_desc, roi_addr, roi_lim = [], [], []
            roi_slices = []

            for iroi, label, lims in roidat:
                roi_desc.append(label)
                try:
                    xrf_prefix = config['xrf']['prefix']
                except KeyError: # very old map files
                    xrf_prefix = 'xrf_det:'
                roi_addr.append("%smca%%i.R%i" % (xrf_prefix, iroi))
                roi_lim.append([lims[i] for i in range(self.nmca)])
                roi_slices.append([slice(lims[i][0], lims[i][1]) for i in range(self.nmca)])
            roi_lim = np.array(roi_lim)
            self.add_data(group['rois'], 'name',   strlist(roi_desc))
            self.add_data(group['rois'], 'address', strlist(roi_addr))
            self.add_data(group['rois'], 'limits',   roi_lim)

            for key, val in calib.items():
                self.add_data(group['mca_calib'], key, val)

            for key, val in extra.items():
                try:
                    self.add_data(group['mca_settings'], key, val)
                except TypeError:
                    pass

            self.roi_desc = roi_desc
            self.roi_addr = roi_addr
            self.roi_slices = roi_slices
            self.calib = calib
        else:
            nmca = self.nmca
            roilims = np.array([ [[0, 1]] for i in range(nmca)])
            self.add_data(group['rois'], 'name',     [b'roi1']*nmca)
            self.add_data(group['rois'], 'address',  [b'addr%i.ROI1']*nmca)
            self.add_data(group['rois'], 'limits',   roilims)
            self.add_data(group['mca_calib'], 'offset', [0.00]*nmca)
            self.add_data(group['mca_calib'], 'slope',  [0.01]*nmca)
            self.add_data(group['mca_calib'], 'quad',   [0.00]*nmca)

        # add env data
        envfile = os.path.join(self.folder, self.EnvFile)
        if os.path.exists(envfile):
            envdat = readEnvironFile(envfile)
        else:
            envdat = ['Facility.Ring_Current (UnknownPV) = 0']
        env_desc, env_addr, env_val = parseEnviron(envdat)

        self.add_data(group['environ'], 'name',    strlist(env_desc))
        self.add_data(group['environ'], 'address', strlist(env_addr))
        self.add_data(group['environ'], 'value',   strlist(env_val))

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

        self.process_row(0, flush=True, callback=callback, nrows_expected=len(self.rowdata))

        self.status = GSEXRM_FileStatus.hasdata

    def process_row(self, irow, flush=False, offset=None, callback=None, nrows_expected=None):
        row = self.read_rowdata(irow, offset=offset)
        if irow == 0:
            nmca, nchan = 0, 2048
            if row.counts is not None:
                nmca, xnpts, nchan = row.counts.shape
            xrd2d_shape = None
            if row.xrd2d is not None:
                xrd2d_shape = rows.xrd2d.shape
            self.build_schema(row.npts, nmca=nmca, nchan=nchan,
                              scaler_names=row.scaler_names,
                              scaler_addrs=row.scaler_addrs,
                              xrd2d_shape=xrd2d_shape, verbose=True,
                              nrows_expected=nrows_expected)
        if row.read_ok:
            self.add_rowdata(row, callback=callback)

        # print("process row ", self.last_row, flush, callable(callback), callback)
        if flush:
            self.resize_arrays(self.last_row+1, force_shrink=True)
            self.h5root.flush()
            if self._pixeltime is None:
                self.calc_pixeltime()
            if callable(callback):
                callback(filename=self.filename, status='complete')

    def process(self, maxrow=None, force=False, callback=None, offset=None,
                force_no_dtc=False, all_mcas=None):
        "look for more data from raw folder, process if needed"
        self.force_no_dtc = force_no_dtc
        if all_mcas is not None:
            self.all_mcas = all_mcas

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
                flush = nrows-irow<=1  or (irow % 50 == 0)
                self.process_row(irow, flush=flush, offset=offset, callback=callback)
                irow  = irow + 1


    def set_roidata(self, row_start=0, row_end=None):
        if row_end is None:
            row_end = self.last_row

        # print("Process ROIs for rows %d to %d " % (row_start+1, row_end+1))
        rows = slice(row_start, row_end+1)
        roigrp = self.xrmmap['roimap']
        conf = self.xrmmap['config']
        roi_names = [h5str(s) for s in conf['rois/name']]
        roi_limits = conf['rois/limits'][()]
        # print("roi names ", roi_names, roi_limits)

        for roiname, lims in zip(roi_names, roi_limits):
            dt = debugtime()
            roi_slice = lims[0]
            # dt.add('get slice')
            sumraw = roigrp['mcasum'][roiname]['raw'][rows,]
            # dt.add('get sum raw')
            sumcor = roigrp['mcasum'][roiname]['cor'][rows,]
            # dt.add('get sum cor')

            for detname in self.mca_dets:
                mcaraw = self.xrmmap[detname]['counts'][rows,:,roi_slice].sum(axis=2)
                # dt.add(" mcaraw %s " % detname)
                mcacor = mcaraw*self.xrmmap[detname]['dtfactor'][rows,:]
                # dt.add(" mcacor %s " % detname)
                roigrp[detname][roiname]['raw'][rows,] = mcaraw
                roigrp[detname][roiname]['cor'][rows,] = mcacor
                # dt.add(" set roigrps for %s " % detname)
                sumraw += mcaraw
                sumcor += mcacor
                # dt.add(" sum  %s " % detname)
            #dt.show()

            roigrp['mcasum'][roiname]['raw'][rows,] = sumraw
            roigrp['mcasum'][roiname]['cor'][rows,] = sumcor
        self.h5root.flush()

    def calc_pixeltime(self):
        scanconf = self.xrmmap['config/scan']
        rowtime = float(scanconf['time1'][()])
        start = float(scanconf['start1'][()])
        stop = float(scanconf['stop1'][()])
        step = float(scanconf['step1'][()])
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
        if self.dimension is None or irow > len(self.rowdata):
            self.read_master()

        if self.folder is None or irow >= len(self.rowdata):
            return

        if self.has_xrd1d and self.xrdcalfile is None:
            self.xrdcalfile = bytes2str(self.xrmmap['xrd1d'].attrs.get('calfile',''))
        if self.xrdcalfile in (None, ''):
            calfile = os.path.join(nativepath(self.folder), self.XRDCALFile)
            if os.path.exists(calfile):
                self.xrdcalfile = calfile
        scan_version = getattr(self, 'scan_version', 1.00)
        # print(" read row data, scan version  ", scan_version, self.xrdcalfile)

        # if not self.has_xrf and not self.has_xrd2d and not self.has_xrd1d:
        #    raise IOError('No XRF or XRD flags provided.')
        #    return

        if scan_version > 1.35 or self.has_xrd2d or self.has_xrd1d:
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
            self.has_xrd1d = False
            self.has_xrd2d = False

        # eiger XRD maps with 1D data
        if (xrdf.startswith('eig') and xrdf.endswith('.h5') or
            xrdf.startswith('pexrd')):
            self.has_xrd2d = False
            self.has_xrd1d = True

        if '_unused_' in xrff:
            self.has_xrf = False

        reverse = True
        ioffset = 0
        if scan_version > 1.35:
            ioffset = 1
        if scan_version >= 2.0:
            reverse = False
        if offset is not None:
            ioffset = offset
        self.has_xrf = self.has_xrf and xrff != '_unused_'
        return GSEXRM_MapRow(yval, xrff, xrdf, xpsf, sisf, self.folder,
                             irow=irow, nrows_expected=self.nrows_expected,
                             ixaddr=0, dimension=self.dimension,
                             npts=self.npts,
                             reverse=reverse,
                             ioffset=ioffset,
                             force_no_dtc=self.force_no_dtc,
                             masterfile=self.masterfile, flip=self.flip,
                             xrdcal=self.xrdcalfile,
                             xrd2dmask=self.mask_xrd2d,
                             xrd2dbkgd=self.bkgd_xrd2d, wdg=self.azwdgs,
                             steps=self.qstps, has_xrf=self.has_xrf,
                             has_xrd2d=self.has_xrd2d,
                             has_xrd1d=self.has_xrd1d)


    def add_rowdata(self, row, callback=None, flush=True):
        '''adds a row worth of real data'''
        dt = debugtime()
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        thisrow = self.last_row + 1
        if hasattr(callback, '__call__'):
            callback(row=(thisrow+1), maxrow=len(self.rowdata), filename=self.filename)

        pform = 'Add row %4i, yval=%s' % (thisrow+1, row.yvalue)
        if self.has_xrf:
            pform = '%s, xrffile=%s' % (pform, row.xrffile)
        if self.has_xrd2d or self.has_xrd1d:
            pform = '%s, xrdfile=%s' % (pform, row.xrdfile)
        print(pform)

        dt.add(" ran callback, print, version  %s"  %self.version)

        if version_ge(self.version, '2.0.0'):

            mcasum_raw,mcasum_cor = [],[]
            nrows = 0
            map_items = sorted(self.xrmmap.keys())
            dt.add(" get %d map items" % len(map_items))
            for gname in map_items:
                g = self.xrmmap[gname]
                if bytes2str(g.attrs.get('type', '')).startswith('scalar detect'):
                    first_det = list(g.keys())[0]
                    nrows, npts =  g[first_det].shape

            dt.add(" got %d map items" % len(map_items))
            if thisrow >= nrows:
                self.resize_arrays(NINIT*(1+nrows/NINIT), force_shrink=False)

            dt.add(" resized ")
            sclrgrp = self.xrmmap['scalars']
            for ai, aname in enumerate(row.scaler_names):
                sclrgrp[aname][thisrow,  :npts] = row.sisdata[:npts].transpose()[ai]
            dt.add(" add scaler group")
            if self.has_xrf:

                npts = min([len(p) for p in row.posvals])
                pos    = self.xrmmap['positions/pos']
                rowpos = np.array([p[:npts] for p in row.posvals])

                tpos = rowpos.transpose()
                pos[thisrow, :npts, :] = tpos[:npts, :]
                nmca, xnpts, nchan = row.counts.shape
                mca_dets = []
                dt.add(" map xrf 1")
                for gname in map_items:
                    g = self.xrmmap[gname]
                    if bytes2str(g.attrs.get('type', '')).startswith('mca detect'):
                        mca_dets.append(gname)
                        nrows, npts, nchan =  g['counts'].shape
                dt.add(" map xrf 2")
                _nr, npts, nchan = self.xrmmap['mcasum']['counts'].shape
                npts = min(npts, xnpts, self.npts)
                dt.add(" map xrf 3")
                # print("ADD ROW ", self.all_mcas, mca_dets, self.nmca)
                if self.all_mcas:
                    for idet, gname in enumerate(mca_dets):
                        grp = self.xrmmap[gname]
                        grp['counts'][thisrow, :npts, :] = row.counts[idet, :npts, :]
                        grp['dtfactor'][thisrow,  :npts] = row.dtfactor[idet, :npts]
                        grp['realtime'][thisrow,  :npts] = row.realtime[idet, :npts]
                        grp['livetime'][thisrow,  :npts] = row.livetime[idet, :npts]
                        grp['inpcounts'][thisrow, :npts] = row.inpcounts[idet, :npts]
                        grp['outcounts'][thisrow, :npts] = row.outcounts[idet, :npts]

                livetime = np.zeros(npts, dtype=np.float64)
                realtime = np.zeros(npts, dtype=np.float64)
                dtfactor = np.zeros(npts, dtype=np.float32)
                inpcounts = np.zeros(npts, dtype=np.float32)
                outcounts = np.zeros(npts, dtype=np.float32)
                dt.add(" map xrf 4a: alloc ")
                # print("ADD ", inpcounts.dtype, row.inpcounts.dtype)
                for idet in range(self.nmca):
                    realtime += row.realtime[idet, :npts]
                    livetime += row.livetime[idet, :npts]
                    inpcounts += row.inpcounts[idet, :npts]
                    outcounts += row.outcounts[idet, :npts]
                livetime /= (1.0*self.nmca)
                realtime /= (1.0*self.nmca)
                dt.add(" map xrf 4b: time sums")

                sumgrp = self.xrmmap['mcasum']
                sumgrp['counts'][thisrow, :npts, :nchan] = row.total[:npts, :nchan]
                dt.add(" map xrf 4b: set counts")
                # print("add realtime ", sumgrp['realtime'].shape, self.xrmmap['roimap/det_raw'].shape, thisrow)
                sumgrp['realtime'][thisrow,  :npts] = realtime
                sumgrp['livetime'][thisrow,  :npts] = livetime
                sumgrp['dtfactor'][thisrow,  :npts] = row.total_dtfactor[:npts]
                sumgrp['inpcounts'][thisrow,  :npts] = inpcounts
                sumgrp['outcounts'][thisrow,  :npts] = outcounts
                dt.add(" map xrf 4c: set time data ")

                if version_ge(self.version, '2.1.0'): # version 2.1
                    det_raw = self.xrmmap['roimap/det_raw']
                    det_cor = self.xrmmap['roimap/det_cor']
                    sum_raw = self.xrmmap['roimap/sum_raw']
                    sum_cor = self.xrmmap['roimap/sum_cor']

                    detraw = list(row.sisdata[:npts].transpose())
                    detcor = detraw[:]
                    sumraw = detraw[:]
                    sumcor = detraw[:]

                    if self.roi_slices is None:
                        lims = self.xrmmap['config/rois/limits'][()]
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
                    dt.add(" map xrf 5a: got simple  ROIS")
                    det_raw[thisrow, :npts, :] = np.array(detraw).transpose()
                    det_cor[thisrow, :npts, :] = np.array(detcor).transpose()
                    sum_raw[thisrow, :npts, :] = np.array(sumraw).transpose()
                    sum_cor[thisrow, :npts, :] = np.array(sumcor).transpose()


                else: # version 2.0
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
                dt.add(" map xrf 6")
        else:  # version 1.0.1
            if self.has_xrf:
                nmca, xnpts, nchan = row.counts.shape
                xrm_dets = []

                nrows = 0
                map_items = sorted(self.xrmmap.keys())
                for gname in map_items:
                    g = self.xrmmap[gname]
                    if bytes2str(g.attrs.get('type', '')).startswith('mca detect'):
                        xrm_dets.append(g)
                        nrows, npts, nchan =  g['counts'].shape

                if thisrow >= nrows:
                    self.resize_arrays(NINIT*(1+nrows/NINIT), force_shrink=False)

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
                    lims = self.xrmmap['config/rois/limits'][()]
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

        if self.has_xrd1d and row.xrdq is not None:
            if thisrow < 2:
                if len(row.xrdq.shape) == 1:
                    self.xrmmap['xrd1d/q'][:] = row.xrdq
                else:
                    self.xrmmap['xrd1d/q'][:] = row.xrdq[0]

            if self.bkgd_xrd1d is not None:
                self.xrmmap['xrd1d/counts'][thisrow,] = row.xrd1d - self.bkgd_xrd1d
            else:
                _ni, _nc, _nq  = self.xrmmap['xrd1d/counts'].shape
                _rc, _rq = row.xrd1d.shape
                _nc = min(_nc, _rc)
                _nq = min(_nq, _rq)
                self.xrmmap['xrd1d/counts'][thisrow, :_nc, :_nq] = row.xrd1d[:_nc,:_nq]

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


        if self.has_xrd2d and row.xrd2d is not None:
            self.xrmmap['xrd2d/counts'][thisrow,] = row.xrd2d
        dt.add("xrd done")
        self.last_row = thisrow
        self.xrmmap.attrs['Last_Row'] = thisrow
        #self.h5root.flush()
        # dt.add("flushed h5 file")
        # dt.show()


    def build_schema(self, npts, nmca=1, nchan=2048, scaler_names=None,
                     scaler_addrs=None, xrd2d_shape=None, nrows_expected=None,
                     verbose=False):
        '''build schema for detector and scan data'''
        self.t0 = time.time()
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        xrmmap = self.xrmmap
        for xkey, xval in xrmmap.attrs.items():
            if xkey == 'Version':
                self.version = xval

        self.xrmmap.attrs['N_Detectors'] = nmca
        if scaler_names is None:
            scaler_names = []
        if scaler_addrs is None:
            scaler_addrs = [''] * len(scaler_names)

        conf = xrmmap['config']
        for key in self.notes:
            conf['notes'].attrs[key] = self.notes[key]

        if self.npts is None:
            self.npts = npts

        if self.chunksize is None:
            self.chunksize = (1, min(2048, npts), nchan)

        if nrows_expected is not None:
            NSTART = max(NINIT, nrows_expected)
        NSTART = NINIT*2

        # positions
        pos = xrmmap['positions']
        for pname in ('mca realtime', 'mca livetime'):
            self.pos_desc.append(pname)
            self.pos_addr.append(pname)
        npos = len(self.pos_desc)
        self.add_data(pos, 'name',    strlist(self.pos_desc))
        self.add_data(pos, 'address', strlist(self.pos_addr))
        pos.create_dataset('pos', (NSTART, npts, npos), np.float32,
                           maxshape=(None, npts, npos), **self.compress_args)

        ##
        # cfile = FastMapConfig()
        # print(" build_schema -> mapconfig")
        # self.add_map_config(cfile.config, nmca=nmca)
        conf = xrmmap['config']

        offset = conf['mca_calib/offset'][()]
        slope  = conf['mca_calib/slope'][()]
        quad = np.array([0.0]*len(offset))
        if 'quad' in conf['mca_calib']:
            quad   = conf['mca_calib/quad'][()]

        if len(offset) != nmca:
            raise GSEXRM_Exception("incorrect XRF calibration data: need %d MCAs, not %d" % (nmca, len(offset)))


        _ex = np.arange(nchan, dtype=np.float64)
        enarr = []
        for i in range(len(offset)):
            enarr.append(offset[i] + slope[i]*_ex + quad[i]*_ex**2)

        if version_ge(self.version, '2.0.0'):
            sismap = xrmmap['scalars']
            sismap.attrs['type'] = 'scalar detector'
            for aname in scaler_names:
                sismap.create_dataset(aname, (NSTART, npts), np.float32,
                                      chunks=self.chunksize[:-1],
                                      maxshape=(None, npts), **self.compress_args)

            roishape = conf['rois/name'].shape
            if roishape[0] > 0:
                roi_names = [h5str(s) for s in conf['rois/name']]
                roi_limits = np.einsum('jik->ijk', conf['rois/limits'][()])
            else:
                roi_names = ['_']
                roi_limits = np.array([[[0, 2]]])

            if verbose:
                allmcas = 'with all mcas' if self.all_mcas else 'with only mca sum'
                msg = '--- Build XRF Schema: %i ---- MCA: (%i, %i) %s'
                print(msg % (npts, nmca, nchan, allmcas))

            ## mca1 to mcaN
            if self.all_mcas:
                for i in range(nmca):
                    imca = "mca%d" % (i+1)
                    for grp in (xrmmap, xrmmap['roimap']):
                        dgrp = grp.create_group(imca)
                        dgrp.attrs['type'] = 'mca detector'
                        dgrp.attrs['desc'] = imca

                    dgrp = xrmmap[imca]
                    self.add_data(dgrp, 'energy', enarr[i],
                                  attrs={'cal_offset':offset[i],
                                         'cal_slope': slope[i],
                                         'cal_quad': quad[i]})
                    dgrp.create_dataset('counts', (NSTART, npts, nchan), np.uint32,
                                        chunks=self.chunksize,
                                        maxshape=(None, npts, nchan), **self.compress_args)

                    for name, dtype in (('realtime',  np.int64),
                                        ('livetime',  np.int64),
                                        ('dtfactor',  np.float32),
                                        ('inpcounts', np.float32),
                                        ('outcounts', np.float32)):
                        dgrp.create_dataset(name, (NSTART, npts), dtype,
                                            maxshape=(None, npts), **self.compress_args)

                    dgrp = xrmmap['roimap'][imca]
                    for rname, rlimit in zip(roi_names,roi_limits[i]):
                        rgrp = dgrp.create_group(rname)
                        for aname,dtype in (('raw', np.uint32),
                                            ('cor', np.float32)):
                            rgrp.create_dataset(aname, (1, npts), dtype,
                                                chunks=self.chunksize[:-1],
                                                maxshape=(None, npts), **self.compress_args)

                        rlimit = [max(0, rlimit[0]), min(len(enarr[i])-1, rlimit[1])]
                        lmtgrp = rgrp.create_dataset('limits', data=enarr[i][rlimit])
                        lmtgrp.attrs['type'] = 'energy'
                        lmtgrp.attrs['units'] = 'keV'

            ## mcasum
            for grp in (xrmmap, xrmmap['roimap']):
                dgrp = grp.create_group('mcasum')
                dgrp.attrs['type'] = 'virtual mca detector'
                dgrp.attrs['desc'] = 'sum of detectors'

            dgrp = xrmmap['mcasum']
            if len(enarr) == 0:
                enarr = [np.zeros(nchan)]
                counts = [np.zeros(nchan)]
                offset = slope = quad =  [0.0]
            self.add_data(dgrp, 'energy', enarr[0],
                          attrs={'cal_offset':offset[0],
                                 'cal_slope': slope[0],
                                 'cal_quad': quad[0]})
            dgrp.create_dataset('counts', (NSTART, npts, nchan), np.float64,
                                chunks=self.chunksize,
                                maxshape=(None, npts, nchan), **self.compress_args)

            for name, dtype in (('realtime',  np.int64),
                                ('livetime',  np.int64),
                                ('dtfactor',  np.float32),
                                ('inpcounts', np.float32),
                                ('outcounts', np.float32)):
                dgrp.create_dataset(name, (NSTART, npts), dtype,
                                    maxshape=(None, npts), **self.compress_args)


            dgrp = xrmmap['roimap']['mcasum']
            for rname, rlimit in zip(roi_names, roi_limits[0]):
                rgrp = dgrp.create_group(rname)
                for aname,dtype in (('raw', np.uint32),
                                    ('cor', np.float32)):
                    rgrp.create_dataset(aname, (1, npts), dtype,
                                        chunks=self.chunksize[:-1],
                                        maxshape=(None, npts), **self.compress_args)
                rlimit = [max(0, rlimit[0]), min(len(enarr[0])-1, rlimit[1])]

                lmtgrp = rgrp.create_dataset('limits', data=enarr[0][rlimit],
                                             **self.compress_args)
                lmtgrp.attrs['type'] = 'energy'
                lmtgrp.attrs['units'] = 'keV'

            if version_ge(self.version, '2.1.0'):  # NEW ROI RAW DAT
                rdat = xrmmap['roimap']
                det_addr = [i.strip() for i in scaler_addrs]
                det_desc = [i.strip() for i in scaler_names]
                for addr in conf['rois/address']:
                    det_addr.extend([h5str(addr) % (i+1) for i in range(nmca)])

                for nam in roi_names:
                    det_desc.extend(["%s (mca%i)" % (nam, i+1) for i in range(nmca)])

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

                self.add_data(rdat, 'det_name',   strlist(det_desc))
                self.add_data(rdat, 'det_address', strlist(det_addr))
                self.add_data(rdat, 'sum_name',  strlist(sums_desc))
                self.add_data(rdat, 'sum_list',  sums_list)

                for name, nx, dtype in (('det_raw', nsca, np.uint32),
                                        ('det_cor', nsca, np.float32),
                                        ('sum_raw', nsum, np.uint32),
                                        ('sum_cor', nsum, np.float32)
                                        ):
                    rdat.create_dataset(name, (NSTART, npts, nx), dtype,
                                        chunks=(2, npts, nx),
                                       maxshape=(None, npts, nx), **self.compress_args)

        else:  # version 1.*
            if verbose:
                msg = '--- Build XRF Schema: {:d}  MCA: ({:d}, {:d})'
                print(msg.format(npts, nmca, nchan))

            roi_names = [h5str(s) for s in conf['rois/name']]
            roi_addrs = [h5str(s) for s in conf['rois/address']]
            roi_limits = conf['rois/limits'][()]
            for imca in range(nmca):
                dname = 'det%i' % (imca+1)
                dgrp = xrmmap.create_group(dname)
                dgrp.attrs['type'] = 'mca detector'
                dgrp.attrs['desc'] = 'mca%i' % (imca+1)
                self.add_data(dgrp, 'energy', enarr[imca],
                              attrs={'cal_offset':offset[imca],
                                     'cal_slope': slope[imca],
                                     'cal_quad': quad[imca]})
                self.add_data(dgrp, 'roi_name',  strlist(roi_names))
                self.add_data(dgrp, 'roi_address', strlist([s % (imca+1) for s in roi_addrs]))
                self.add_data(dgrp, 'roi_limits',  roi_limits[:,imca,:])

                dgrp.create_dataset('counts', (NSTART, npts, nchan), np.uint32,
                                    chunks=self.chunksize,
                                    maxshape=(None, npts, nchan), **self.compress_args)
                for name, dtype in (('realtime', np.int64),
                                    ('livetime', np.int64),
                                    ('dtfactor', np.float32),
                                    ('inpcounts', np.float32),
                                    ('outcounts', np.float32)):
                    dgrp.create_dataset(name, (NSTART, npts), dtype,
                                        maxshape=(None, npts), **self.compress_args)

            # add 'virtual detector' for corrected sum:
            dgrp = xrmmap.create_group('detsum')
            dgrp.attrs['type'] = 'virtual mca'
            dgrp.attrs['desc'] = 'deadtime corrected sum of detectors'
            self.add_data(dgrp, 'energy', enarr[0],
                          attrs={'cal_offset':offset[0],
                                 'cal_slope': slope[0],
                                 'cal_quad': quad[0]})
            self.add_data(dgrp, 'roi_name',    strlist(roi_names))
            self.add_data(dgrp, 'roi_address', strlist((s % 1) for s in roi_addrs))
            self.add_data(dgrp, 'roi_limits',  roi_limits[: ,0, :])
            dgrp.create_dataset('counts', (NSTART, npts, nchan), np.uint32,
                                chunks=self.chunksize,
                                maxshape=(None, npts, nchan), **self.compress_args)
            # roi map data
            scan = xrmmap['roimap']
            det_addr = [i.strip() for i in scaler_addrs]
            det_desc = [i.strip() for i in scaler_names]
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

            self.add_data(scan, 'det_name',    strlist(det_desc))
            self.add_data(scan, 'det_address', strlist(det_addr))
            self.add_data(scan, 'sum_name',    strlist(sum_desc))
            self.add_data(scan, 'sum_list',    sums_list)

            nxx = min(nsca, 8)
            for name, nx, dtype in (('det_raw', nsca, np.uint32),
                                    ('det_cor', nsca, np.float32),
                                    ('sum_raw', nsum, np.uint32),
                                    ('sum_cor', nsum, np.float32)):
                scan.create_dataset(name, (NSTART, npts, nx), dtype,
                                    chunks=(2, npts, nx),
                                    maxshape=(None, npts, nx), **self.compress_args)


        if self.has_xrd2d or self.has_xrd1d:
            if self.has_xrd2d:
                xrdpts, xpixx, xpixy = xrd2d_shape # row.xrd2d.shape
                if verbose:
                    prtxt = '--- Build XRD Schema: %i ---- 2D XRD:  (%i, %i)'
                    print(prtxt % (npts, xpixx, xpixy))

                xrdgrp = ensure_subgroup('xrd2d', xrmmap, dtype='2DXRD')

                xrdgrp.attrs['type'] = 'xrd2d detector'
                xrdgrp.attrs['desc'] = '' #'add detector name eventually'

                xrdgrp.create_dataset('mask', (xpixx, xpixy), np.uint16, **self.compress_args)
                xrdgrp.create_dataset('background', (xpixx, xpixy), np.uint16, **self.compress_args)

                chunksize_2DXRD = (1, npts, xpixx, xpixy)
                xrdgrp.create_dataset('counts', (NSTART, npts, xpixx, xpixy), np.uint32,
                                      chunks = chunksize_2DXRD,
                                      maxshape=(None, npts, xpixx, xpixy), **self.compress_args)

            if self.has_xrd1d:
                xrdgrp = ensure_subgroup('xrd1d', xrmmap)
                xrdgrp.attrs['type'] = 'xrd1d detector'
                xrdgrp.attrs['desc'] = 'pyFAI calculation from xrd2d data'

                xrdgrp.create_dataset('q',          (self.qstps,), np.float32, **self.compress_args)
                xrdgrp.create_dataset('background', (self.qstps,), np.float32, **self.compress_args)

                chunksize_xrd1d  = (1, npts, self.qstps)
                xrdgrp.create_dataset('counts',
                                      (NSTART, npts, self.qstps),
                                      np.float32,
                                      chunks = chunksize_xrd1d,
                                      maxshape=(None, npts, self.qstps), **self.compress_args)

                if self.azwdgs > 1:
                    xrmmap['work'].create_group('xrdwedge')
                    for azi in range(self.azwdgs):
                        wdggrp = xrmmap['work/xrdwedge'].create_group('wedge_%02d' % azi)

                        wdggrp.create_dataset('q', (self.qstps,), np.float32, **self.compress_args)

                        wdggrp.create_dataset('counts',
                                              (NSTART, npts, self.qstps),
                                              np.float32,
                                              chunks = chunksize_xrd1d,
                                              maxshape=(None, npts, self.qstps), **self.compress_args)

                        #wdggrp.create_dataset('limits', (2,), np.float32)
                        wdg_sz = 360./self.azwdgs
                        wdg_lmts = np.array([azi*wdg_sz, (azi+1)*wdg_sz]) - 180
                        wdggrp.create_dataset('limits', data=wdg_lmts)

        try:
            print('\nStart: %s' % isotime(self.starttime))
        except:
            pass

        self.h5root.flush()


    def add_xrd1d(self, qstps=None):

        xrd1dgrp = ensure_subgroup('xrd1d',self.xrmmap)
        xrdcalfile = bytes2str(xrd1dgrp.attrs.get('calfile', ''))
        if os.path.exists(xrdcalfile):
            print('Using calibration file : %s' % xrdcalfile)
            try:
                nrows, npts , xpixx, xpixy = self.xrmmap['xrd2d/counts'].shape
            except:
                return

            if qstps is not None: self.qstps = qstps

            pform ='\n--- Build XRD1D Schema (%i, %i, %i) from 2D XRD (%i, %i, %i, %i) ---'
            print(pform % (nrows, npts, self.qstps, nrows, npts, xpixx, xpixy))

            try:
                xrd1dgrp.attrs['type'] = 'xrd1d detector'
                xrd1dgrp.attrs['desc'] = 'pyFAI calculation from xrd2d data'
                xrd1dgrp.create_dataset('q',          (self.qstps,), np.float32)
                xrd1dgrp.create_dataset('background', (self.qstps,), np.float32)

                chunksize_xrd1d  = (1, npts, self.qstps)
                xrd1dgrp.create_dataset('counts',
                                       (nrows, npts, self.qstps),
                                       np.float32,
                                       chunks = chunksize_xrd1d)

                attrs = {'steps':self.qstps,'mask':self.xrd2dmaskfile,'flip':self.flip}
                print('\nStart: %s' % isotime())
                for i in np.arange(nrows):
                    rowq, row1d = integrate_xrd_row(self.xrmmap['xrd2d/counts'][i],xrdcalfile,**attrs)
                    if i == 0:
                        self.xrmmap['xrd1d/q'][:] = rowq[0]
                    self.xrmmap['xrd1d/counts'][i,] = row1d

                self.has_xrd1d = True
                # print('End: %s' % isotime())
            except:
                print('xrd1d data already in file.')
                return

    def get_slice_y(self):
        for name, val in zip([h5str(a) for a in self.xrmmap['config/environ/name']],
                             [h5str(a) for a in self.xrmmap['config/environ/value']]):
            name = str(name).lower()
            if name.startswith('sample'):
                name = name.replace('samplestage.', '')
                if name.lower() == 'fine y' or name.lower() == 'finey':
                    return float(val)

    def get_datapath_list(self, remove='raw'):
        def find_detector(group):
            sub_list = []
            if 'counts' in group.keys():
                sub_list += [group['counts'].name]
            elif 'scal' in group.name:
                for key, val in dict(group).items():
                    sub_list += [group[key].name]
            return sub_list

        dlist = []
        for det in self.get_detector_list():
           for idet in find_detector(self.xrmmap[det]):
               if not (remove in idet):
                   dlist.append(idet)

        return dlist


    def get_roi_list(self, det_name, force=False):
        """
        get a list of rois from detector
        """
        detname = self.get_detname(det_name)
        if not force and (detname not in EXTRA_DETGROUPS):
            roilist = self.roi_names.get(detname, None)
            if roilist is not None:
                return roilist

        roigrp = ensure_subgroup('roimap', self.xrmmap, dtype='roi maps')
        def sort_roi_limits(roidetgrp):
            roi_name, roi_limits = [],[]
            for name in roidetgrp.keys():
                roi_name   += [name]
                roi_limits += [list(roidetgrp[name]['limits'][:])]
            return [x for (y,x) in sorted(zip(roi_limits,roi_name))]
        rois = []
        if version_ge(self.version, '2.0.0'):
            if detname in roigrp.keys():
                rois = sort_roi_limits(roigrp[detname])
            else:
                det = self.xrmmap[detname]
                if (detname in EXTRA_DETGROUPS or
                    'detector' in det.attrs.get('type')):
                    rois = list(det.keys())
        else:
            if detname in EXTRA_DETGROUPS:
                rois = list(self.xrmmap[detname].keys())
            elif detname in self.xrmmap.keys():
                rois = list(roigrp['sum_name']) + rois
                try:
                    rois = sort_roi_limits(roigrp[detname]) + rois
                except:
                    pass
        rois.append('1')
        self.roi_names[detname] = [h5str(a) for a in rois]
        return self.roi_names[detname]

    def get_detector_list(self, use_cache=True):
        """get a list of detector groups,
        ['mcasum', 'mca1', ..., 'scalars', 'work', 'xrd1d', ...]
        """
        workgroup = ensure_subgroup('work', self.xrmmap)
        if use_cache and self.detector_list is not None:
            return self.detector_list
        def build_dlist(group):
            detlist, sumslist = [], []
            for key, grp in group.items():
                if ('det' in bytes2str(grp.attrs.get('type', '')) or
                    'mca' in bytes2str(grp.attrs.get('type', ''))):
                    if 'sum' in key.lower():
                        sumslist.append(key)
                    else:
                        detlist.append(key)
            return sumslist + detlist

        xrmmap = self.xrmmap
        det_list = []
        if version_ge(self.version, '2.0.0'):
            det_list = build_dlist(xrmmap['roimap'])
        else:
            det_list = build_dlist(xrmmap)
            for det in build_dlist(xrmmap['roimap']):
                if det not in det_list:
                    det_list.append(det)

        # add any other groups with 'detector' in the `type` attribute:
        for det, grp in xrmmap.items():
            if det not in det_list and 'detector' in h5str(grp.attrs.get('type', '')):
                det_list.append(det)
        self.detector_list = det_list
        if len(det_list) < 1:
            det_list = ['']
            self.detector_list = None
        return det_list

    def reset_flags(self):
        '''
        Reads hdf5 file for data and sets the flags.
        mkak 2016.08.30 // rewritten mkak 2017.08.03 // rewritten mkak 2017.12.05
        '''
        for det in self.get_detector_list():
            if det in self.xrmmap:

                detgrp = self.xrmmap[det]

                dettype = bytes2str(detgrp.attrs.get('type', '')).lower()
                if 'mca' in dettype:
                    self.has_xrf   = 'counts' in detgrp
                elif 'xrd2d' in dettype:
                    self.has_xrd2d = 'counts' in detgrp
                elif 'xrd1d' in dettype:
                    self.has_xrd1d = 'counts' in detgrp
                elif det == 'xrd': ## compatible with old version
                    try:
                        detgrp['data1d']
                        self.has_xrd1d = True
                    except:
                        pass
                    try:
                        detgrp['data2D']
                        self.has_xrd2d = True
                    except:
                        pass

    def print_flags(self):
        print('   HAS XRF, XRD1D, XRD2D: %s, %s, %s' % (self.has_xrf,
                                                        self.has_xrd1d,
                                                        self.has_xrd2d))

    def resize_arrays(self, nrow, force_shrink=True):
        "resize all arrays for new nrow size"
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)
        if version_ge(self.version, '2.0.0'):

            g = self.xrmmap['positions/pos']
            old, npts, nx = g.shape
            if nrow < old and not force_shrink:
                return
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
                        for aname in ('livetime', 'realtime',
                                      'inpcounts', 'outcounts', 'dtfactor'):
                            if aname in g:
                                g[aname].resize((nrow, npts))

                    elif type_attr.startswith('xrd2d'):
                        oldnrow, npts, xpixx, xpixy = g['counts'].shape
                        g['counts'].resize((nrow, npts, xpixx, xpixy))
                    elif type_attr.startswith('xrd1d'):
                        oldnrow, npts, qstps = g['counts'].shape
                        g['counts'].resize((nrow, npts, qstps))

            if self.azwdgs > 1:
                for g in self.xrmmap['work/xrdwedge'].values():
                    g['counts'].resize((nrow, npts, qstps))

            if version_ge(self.version, '2.1.0'):
                for bname in ('det_raw', 'det_cor', 'sum_raw', 'sum_cor'):
                    g = self.xrmmap['roimap'][bname]
                    old, npts, nx = g.shape
                    g.resize((nrow, npts, nx))
            else:
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
                    elif type_attr.startswith('xrd2d'):
                        oldnrow, npts, xpixx, xpixy = g['counts'].shape
                        g['counts'].resize((nrow, npts, xpixx, xpixy))
                    elif type_attr.startswith('xrd1d'):
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

    def add_work_array(self, data, name, parent='work',
                       dtype='virtual detector', **kws):
        '''
        add an array to the work group of processed arrays
        '''
        workgroup = ensure_subgroup(parent, self.xrmmap, dtype=dtype)
        if name is None:
            name = 'array_%3.3i' % (1+len(workgroup))
        if name in workgroup:
            raise ValueError("array name '%s' exists in '%s" % (name, parent))
        ds = workgroup.create_dataset(name, data=data)
        for key, val in kws.items():
            ds.attrs[key] = val
        self.h5root.flush()

    def del_work_array(self, name, parent='work'):
        '''
        delete an array to the work group of processed arrays
        '''
        workgroup = ensure_subgroup(parent, self.xrmmap)
        name = h5str(name)
        if name in workgroup:
            del workgroup[name]
            self.h5root.flush()

    def get_work_array(self, name, parent='work'):
        '''
        get an array from the work group of processed arrays by index or name
        '''
        workgroup = ensure_subgroup(parent, self.xrmmap)
        dat = None
        name = h5str(name)
        if name in workgroup:
            dat = workgroup[name]
        return dat

    def work_array_names(self, parent='work'):
        '''
        return list of work array descriptions
        '''
        workgroup = ensure_subgroup(parent, self.xrmmap)
        return [h5str(g) for g in workgroup.keys()]

    def add_area(self, amask, name=None, desc=None):
        '''add a selected area, with optional name
        the area is encoded as a boolean array the same size as the map

        '''
        if not self.check_hostid():
            raise GSEXRM_Exception(NOT_OWNER % self.filename)

        area_grp = ensure_subgroup('areas', self.xrmmap, dtype='areas')
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
        # ds.attrs['tomograph']   = tomo
        self.h5root.flush()
        return name

    def export_areas(self, filename=None):
        '''export areas to datafile '''
        if filename is None:
            file_str = '%s_Areas.npz'
            filename = file_str % self.filename

        areas = ensure_subgroup('areas', self.xrmmap, dtype='areas')
        kwargs = {key: val[:] for key, val in areas.items()}
        np.savez(filename, **kwargs)
        return filename

    def import_areas(self, filename, overwrite=False):
        '''import areas from datafile exported by export_areas()'''
        fname = os.path.split(filename)[1]
        if fname.endswith('.h5_Areas.npz'):
            fname = fname.replace('.h5_Areas.npz', '')

        areas = ensure_subgroup('areas', self.xrmmap, dtype='areas')

        npzdat = np.load(filename)
        for aname in npzdat.files:
            desc = name = aname
            if name in areas and not overwrite:
                name = '%s_%s' % (name, fname)
                desc = '%s from %s' % (aname, fname)
            self.add_area(npzdat[aname], name=name, desc=desc)

    def get_area(self, name=None):
        '''
        get area group by name or description
        '''
        area_grp = ensure_subgroup('areas', self.xrmmap, dtype='areas')
        if name is not None and name in area_grp:
            return area_grp[name]
        else:
            for aname in area_grp:
                if name == bytes2str(area_grp[aname].attrs.get('description','')):
                    return area_grp[aname]
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

        amask = area[()]

        roidata = []
        d_addrs = [d.lower() for d in self.xrmmap['roimap/det_address']]
        d_names = [d for d in self.xrmmap['roimap/det_name']]
        # count times
        ctime = [1.e-6*self.xrmmap['roimap/det_raw'][:,:,0][amask]]
        for i in range(self.xrmmap.attrs.get('N_Detectors',0)):
            tname = 'det%i/realtime' % (i+1)
            ctime.append(1.e-6*self.xrmmap[tname][()][amask])

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

    def get_translation_axis(self, hotcols=None):
        if hotcols is None:
            hotcols = self.hotcols
        posnames = [bytes2str(n.lower()) for n in self.xrmmap['positions/name']]
        if 'x' in posnames:
            x = self.get_pos('x', mean=True)
        elif 'fine x' in posnames:
            x = self.get_pos('fine x', mean=True)
        else:
            x = self.get_pos(0, mean=True)

        if hotcols and x is not None:
           if len(x) == self.xrmmap[self.get_detname()]['counts'].shape[1]:
               x = x[1:-1]

        return x

    def get_rotation_axis(self, axis=None, hotcols=None):
        if hotcols is None:
            hotcols = self.hotcols
        posnames = [bytes2str(n.lower()) for n in self.xrmmap['positions/name']]
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
           if len(omega) == self.xrmmap[self.get_detname()]['counts'].shape[1]:
               omega = omega[1:-1]
        return omega

    def get_tomography_center(self):
        tomogrp = ensure_subgroup('tomo', self.xrmmap)
        try:
            return tomogrp['center'][()]
        except:
            self.set_tomography_center()

        return tomogrp['center'][()]

    def set_tomography_center(self,center=None):
        if center is None:
            center = len(self.get_translation_axis())/2.

        tomogrp = ensure_subgroup('tomo', self.xrmmap)
        try:
            del tomogrp['center']
        except:
            pass
        tomogrp.create_dataset('center', data=center)

        self.h5root.flush()

    def get_sinogram(self, roi_name, det=None, trim_sino=False,
                     hotcols=None, dtcorrect=None, **kws):
        '''extract roi map for a pre-defined roi by name

        Parameters
        ---------
        roiname    :  str                  ROI name
        det        :  str                  detector name
        dtcorrect  :  None or bool [None]  deadtime correction
        hotcols    :  None or bool [None]  suppress hot columns

        Returns
        -------
        sinogram for ROI data
        sinogram_order (needed for knowing shape of sinogram)

        Notes
        -----
        if dtcorrect or hotcols is None, they are taken from
        self.dtcorrect and self.hotcols
        '''
        if hotcols is None:
            hotcols = self.hotcols
        if dtcorrect is None:
            dtcorrect = self.dtcorrect

        sino  = self.get_roimap(roi_name, det=det, hotcols=hotcols, **kws)
        x     = self.get_translation_axis(hotcols=hotcols)
        omega = self.get_rotation_axis(hotcols=hotcols)

        if omega is None:
            print('\n** Cannot compute tomography: no rotation axis specified in map. **')
            return

        if trim_sino:
            sino, x, omega = trim_sinogram(sino, x, omega)

        return reshape_sinogram(sino, x, omega)

    def get_tomograph(self, sino, omega=None, center=None, hotcols=None, **kws):
        '''
        returns tomo_center, tomo
        '''
        if hotcols is None:
            hotcols = self.hotcols
        if center is None:
            center = self.get_tomography_center()
        if omega  is None:
            omega = self.get_rotation_axis(hotcols=hotcols)
        if omega is None:
            print('\n** Cannot compute tomography: no rotation axis specified in map. **')
            return

        center, recon = tomo_reconstruction(sino, omega, center=center, **kws)
        self.set_tomography_center(center=center)
        return recon

    def save_tomograph(self, datapath, algorithm='gridrec',
                       filter_name='shepp', num_iter=1, dtcorrect=None,
                       hotcols=None, **kws):
        '''
        saves group for tomograph for selected detector
        '''
        if hotcols is None:
            hotcols = self.hotcols
        if dtcorrect is None:
            dtcorrect = self.dtcorrect

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
                grp = ensure_subgroup(kpath ,grp)
        tomogrp = grp

        ## define sino group from datapath
        if 'scalars' in datapath or 'xrd' in datapath:
            sino = datagroup[()]
        elif dtcorrect:
            if 'sum' in datapath:
                sino = np.zeros(np.shape(np.einsum('jki->ijk', datagroup[()])))
                for i in range(self.nmca):
                    idatapath = datapath.replace('sum', str(i+1))
                    idatagroup = self.xrmmap[idatapath]
                    idetpath  = detpath.replace('sum', str(i+1))
                    idetgroup = self.xrmmap[idetpath]
                    sino += np.einsum('jki->ijk', idatagroup[()]) * idetgroup['dtfactor'][()]

            else:
                sino = np.einsum('jki->ijk', datagroup[()]) * detgroup['dtfactor'][()]
        else:
            sino = datagroup[()]

        sino,order = reshape_sinogram(sino, x, omega)

        center, tomo = tomo_reconstruction(sino, algorithm=algorithm,
                                           filter_name=filter_name,
                                           num_iter=num_iter, omega=omega,
                                           center=center, sinogram_order=order)

        tomogrp.attrs['tomo_alg'] = '-'.join([str(t) for t in (algorithm, filter_name)])
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

        for key, val in dict(detgroup.attrs).items():
            tomogrp.attrs[key] = val

        self.h5root.flush()

    def take_ownership(self):
        "claim ownership of file"
        if self.xrmmap is None:
            return
        self.xrmmap.attrs['Process_Machine'] = get_machineid()
        self.xrmmap.attrs['Process_ID'] = os.getpid()
        self.h5root.flush()

    def release_ownership(self):
        self.xrmmap.attrs['Process_Machine'] = ''
        self.xrmmap.attrs['Process_ID'] = 0
        self.xrmmap.attrs['Last_Row'] = self.last_row

    def check_ownership(self, take_ownership=True):
        return self.check_hostid(take_ownership=take_ownership)

    def check_hostid(self, take_ownership=True):
        '''checks host and id of file:
        returns True if this process the owner of the file

        By default, this takes ownership if it can.
        '''
        if self.xrmmap is None:
            return
        attrs = self.xrmmap.attrs
        self.folder = attrs['Map_Folder']
        file_mach = attrs['Process_Machine']
        file_pid  = attrs['Process_ID']
        if len(file_mach) < 1 or file_pid < 1:
            if take_ownership:
                self.take_ownership()
            return True
        return (file_mach == get_machineid() and file_pid == os.getpid())

    def folder_has_newdata(self):
        if self.folder is not None and isGSEXRM_MapFolder(self.folder):
            self.read_master()
            return (self.last_row < len(self.rowdata)-1)
        return False

    def read_master(self):
        "reads master file for toplevel scan info"
        if self.folder is None or not isGSEXRM_MapFolder(self.folder):
            return
        self.masterfile = os.path.join(nativepath(self.folder), self.MasterFile)
        header, rows, mtime = [], [], -1
        if self.scandb is not None:
            # check that this map folder is the one currently running from scandb:
            try:
                db_folder = toppath(self.scandb.get_info('map_folder'))
            except:
                db_folder = None
            disk_folder = toppath(os.path.abspath(self.folder))

            if db_folder == disk_folder: # this is the current map
                mastertext = self.scandb.get_slewscanstatus()
                mtime = time.time()
                header, rows = [], []
                for srow in mastertext:
                    line = str(srow.text.strip())
                    if line.startswith('#'):
                        header.append(line)
                    else:
                        rows.append(line.split())

        if len(header) < 1 or mtime < 0:  # this is *not* the map that is currently being collected:
            # if file the master file is not new, the current row data is OK:

            try:
                header, rows = readMasterFile(self.masterfile)
            except IOError:
                raise GSEXRM_Exception("cannot read Master file from '%s'" %
                                       self.masterfile)

            mtime = os.stat(self.masterfile).st_mtime
            if mtime < (self.master_modtime+1.0) and len(self.rowdata) > 1:
                # print("READ MASTER not a new masterfile ", len(self.rowdata), len(rows))
                return len(self.rowdata)

        self.master_modtime = mtime

        self.notes['end_time'] = isotime(mtime)
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

        self.scan_version = 1.00
        self.nrows_expected = None
        self.start_time = time.ctime()
        for line in header:
            words = line.split('=')
            if 'scan.starttime' in words[0].lower():
                self.start_time = words[1].strip()
                self.notes['scan_start_time'] = self.start_time
            elif 'scan.version' in words[0].lower():
                self.scan_version = words[1].strip()
            elif 'scan.nrows_expected' in words[0].lower():
                self.nrows_expected = int(words[1].strip())
        self.scan_version = float(self.scan_version)

        # print("read_master scan version = ", self.scan_version)
        self.stop_time = time.ctime(self.master_modtime)
        try:
            last_file = os.path.join(self.folder,rows[-1][2])
            self.stop_time = time.ctime(os.stat(last_file).st_ctime)
        except:
            pass
        self.notes['scan_end_time'] = self.stop_time
        self.notes['scan_version'] = self.scan_version

        if self.scan_version < 1.35 and (self.has_xrd2d or self.has_xrd1d):
            xrd_files = [fn for fn in os.listdir(self.folder) if fn.endswith('nc')]
            for i, addxrd in enumerate(xrd_files):
                self.rowdata[i].insert(4, addxrd)

        cfile = FastMapConfig()
        cfile.Read(os.path.join(self.folder, self.ScanFile))
        mapconf = self.mapconf = cfile.config

        if self.filename is None:
            self.filename = mapconf['scan']['filename']
        if not self.filename.endswith('.h5'):
            self.filename = "%s.h5" % self.filename

        slow_pos = mapconf['slow_positioners']
        fast_pos = mapconf['fast_positioners']

        scanconf = mapconf['scan']
        self.dimension = scanconf['dimension']
        start = mapconf['scan']['start1']
        stop  = mapconf['scan']['stop1']
        step  = mapconf['scan']['step1']
        span = abs(stop-start)
        self.npts = int(abs(abs(step)*1.01 + span)/abs(step))

        pos1 = scanconf['pos1']
        self.pos_addr = [pos1]
        self.pos_desc = [slow_pos[pos1]]
        # note: XPS gathering file now saving ONLY data for the fast axis

        if self.dimension > 1:
            yaddr = scanconf['pos2']
            self.pos_addr.append(yaddr)
            self.pos_desc.append(slow_pos[yaddr])

        return len(rows)

    def get_detname(self, det=None):
        "return XRMMAP group for a detector"

        mcastr = 'mca' if version_ge(self.version, '2.0.0') else 'det'
        detname =  '%ssum' % mcastr

        if isinstance(det, str):
            for d in self.get_detector_list():
                if det.lower() == d.lower():
                    detname = d
        elif isinstance(det, int):
            if det in range(1, self.nmca+1):
                detname = '%s%i' % (mcastr, det)

        return detname

    def get_detgroup(self, det=None):
        "return  XRMMAP group for a detector"
        return self.xrmmap[self.get_detname(det)]

    def get_energy(self, det=None):
        '''return energy array for a detector'''
        try:
            group = self.xrmmap[det]
        except:
            group = self.get_detgroup(det)
        return group['energy'][()]

    def get_shape(self):
        '''returns NY, NX shape of array data'''
        ny, nx, npos = self.xrmmap['positions/pos'].shape
        return ny, nx

    def get_envvar(self, name):
        """get environment value by name"""
        if self.envvar is None:
            self.envvar = {}
            env_names = [h5str(a) for a in self.xrmmap['config/environ/name']]
            env_vals  = [h5str(a) for a in self.xrmmap['config/environ/value']]
            for name, val in zip(env_names, env_vals):
                name = h5str(name).lower()
                val = h5str(val)
                try:
                    fval = float(val)
                except:
                    fval = val

                self.envvar[name] = fval
        name = name.lower()
        if name in self.envvar:
            return self.envvar[name]

    def get_incident_energy(self):
        """ special case of get_envvar"""
        env_names = [h5str(a) for a in self.xrmmap['config/environ/name']]
        env_vals  = [h5str(a) for a in self.xrmmap['config/environ/value']]
        for name, val in zip(env_names, env_vals):
            name = name.lower().replace('.', ' ')
            if name.startswith('mono energy'):
                return float(val)
        return DEFAULT_XRAY_ENERGY

    def get_counts_rect(self, ymin, ymax, xmin, xmax, mapdat=None,
                        det=None, dtcorrect=None):
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
        dtcorrect :  optional, bool [None]         dead-time correct data

        Returns
        -------
        ndarray for XRF counts in rectangle

        Does *not* check for errors!

        Note:  if mapdat is None, the map data is taken from the 'det' parameter
        '''
        if dtcorrect is None:
            dtcorrect = self.dtcorrect
        if mapdat is None:
            mapdat = self.get_detgroup(det)

        nx, ny = (xmax-xmin, ymax-ymin)
        sx = slice(xmin, xmax)
        sy = slice(ymin, ymax)

        if len(mapdat['counts'].shape) == 4:
            counts = mapdat['counts'][sy, sx, :, :]
        else:
            counts = mapdat['counts'][sy, sx, :]
        # print("get_counts_rect: ", det, dtcorrect, mapdat, 'dtfactor' in mapdat,
        #   mapdat['counts'].shape, counts.shape, counts.dtype)

        if dtcorrect and 'dtfactor' in mapdat:
            b = counts.sum()
            c = mapdat['dtfactor'][sy, sx].mean()
            counts = counts*mapdat['dtfactor'][sy, sx].reshape(ny, nx, 1)
        return counts

    def get_mca_area(self, areaname, det=None, dtcorrect=None):
        '''return XRF spectra as MCA() instance for
        spectra summed over a pre-defined area

        Parameters
        ---------
        areaname :   str       name of area
        dtcorrect :  optional, bool [None]       dead-time correct data

        Returns
        -------
        MCA object for XRF counts in area

        '''
        try:
            area = self.get_area(areaname)[()]
        except:
            raise GSEXRM_Exception("Could not find area '%s'" % areaname)
        if dtcorrect is None:
            dtcorrect = self.dtcorrect
        npixels = area.sum()
        if npixels < 1:
            return None

        dgroup = self.get_detname(det)

        # first get data for bounding rectangle
        _ay, _ax = np.where(area)
        ymin, ymax, xmin, xmax = _ay.min(), _ay.max()+1, _ax.min(), _ax.max()+1
        opts = {'dtcorrect': dtcorrect, 'det': det}
        counts = self.get_counts_rect(ymin, ymax, xmin, xmax, **opts)
        ltime, rtime = self.get_livereal_rect(ymin, ymax, xmin, xmax, **opts)
        ltime = ltime[area[ymin:ymax, xmin:xmax]].sum()
        rtime = rtime[area[ymin:ymax, xmin:xmax]].sum()
        counts = counts[area[ymin:ymax, xmin:xmax]]
        while(len(counts.shape) > 1):
            counts = counts.sum(axis=0)
        return self._getmca(dgroup, counts, areaname, npixels=npixels,
                            real_time=rtime, live_time=ltime)

    def get_mca_rect(self, ymin, ymax, xmin, xmax, det=None, dtcorrect=None):
        '''return mca counts for a map rectangle, optionally

        Parameters
        ---------
        ymin :       int       low y index
        ymax :       int       high y index
        xmin :       int       low x index
        xmax :       int       high x index
        det :        optional, None or int         index of detector
        dtcorrect :  optional, bool [None]         dead-time correct data

        Returns
        -------
        MCA object for XRF counts in rectangle

        '''
        if dtcorrect is None:
            dtcorrect = self.dtcorrect
        dgroup = self.get_detname(det)
        mapdat = self.get_detgroup(det)
        counts = self.get_counts_rect(ymin, ymax, xmin, xmax, mapdat=mapdat,
                                      det=det, dtcorrect=dtcorrect)
        name = 'rect(y=[%i:%i], x==[%i:%i])' % (ymin, ymax, xmin, xmax)
        npix = (ymax-ymin+1)*(xmax-xmin+1)
        ltime, rtime = self.get_livereal_rect(ymin, ymax, xmin, xmax, det=det,
                                              dtcorrect=dtcorrect)
        counts = counts.sum(axis=0).sum(axis=0)
        return self._getmca(dgroup, counts, name, npixels=npix,
                            real_time=rtime.sum(), live_time=ltime.sum())


    def get_livereal_rect(self, ymin, ymax, xmin, xmax, det=None, **kws):
        '''return livetime, realtime for a map rectangle, optionally
        applying area mask and deadtime correction

        Parameters
        ---------
        ymin :       int       low y index
        ymax :       int       high y index
        xmin :       int       low x index
        xmax :       int       high x index
        det :        optional, None or int      index of detector

        Returns
        -------
        realtime, livetime in seconds

        '''
        tshape = self.get_shape()
        dmap = self.get_detgroup(det)

        if ymax < 0: ymax += tshape[0]
        if xmax < 0: xmax += tshape[1]
        nx, ny = (xmax-xmin, ymax-ymin)
        sx = slice(xmin, xmax)
        sy = slice(ymin, ymax)

        if 'livetime' in dmap:
            livetime = 1.e-6*dmap['livetime'][sy, sx]
            realtime = 1.e-6*dmap['realtime'][sy, sx]
        else:
            livetime = self.pixeltime * np.ones((ny, nx))
            realtime = self.pixeltime * np.ones((ny, nx))

        return livetime, realtime

    def _getmca(self, dgroup, counts, name, npixels=None, **kws):
        '''return an MCA object for a detector group
        (map is one of the  'mca1', ... 'mcasum')
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
        map  = self.xrmmap[dgroup]
        cal  = map['energy'].attrs
        _mca = MCA(counts=counts, offset=cal['cal_offset'],
                   slope=cal['cal_slope'], **kws)
        if self.incident_energy is None:
            self.incident_energy = self.get_incident_energy()

        _mca.incident_energy = 0.001*self.incident_energy
        _mca.energy =  map['energy'][()]
        env_names = [h5str(a) for a in self.xrmmap['config/environ/name']]
        env_addrs = [h5str(a) for a in self.xrmmap['config/environ/address']]
        env_vals  = [h5str(a) for a in self.xrmmap['config/environ/value']]
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

            roinames = [h5str(a) for a in map[roiname]]
            roilim0  = [lim[0] for lim in map['roi_limits']]
            roilim1  = [lim[1] for lim in map['roi_limits']]
            for roi, lim0, lim1 in zip(roinames, roilim0, roilim1):
                _mca.add_roi(roi, left=lim0, right=lim1)

        _mca.areaname = _mca.title = name
        path, fname = os.path.split(self.filename)
        _mca.filename = fix_filename(fname)
        fmt = "Data from File '%s', detector '%s', area '%s'"
        _mca.info  =  fmt % (self.filename, dgroup, name)

        return _mca

    def get_xrd1d_area(self, areaname, callback=None, **kws):
        '''return 1D XRD pattern for a pre-defined area

        Parameters
        ---------
        areaname :   str       name of area

        Returns
        -------
        diffraction pattern for given area

        '''
        try:
            area = self.get_area(areaname)[()]
        except:
            raise GSEXRM_Exception("Could not find area '%s'" % areaname)
            return
        npix = area.sum()
        if npix < 1:
            return None

        stps, xpix, ypix, qdat = 0, 0, 0, None
        sy, sx = [slice(min(_a), max(_a)+1) for _a in np.where(area)]
        xmin, xmax, ymin, ymax = sx.start, sx.stop, sy.start, sy.stop
        nx, ny = (xmax-xmin), (ymax-ymin)

        xrdgroup = 'xrd1d'
        mapdat = self.xrmmap[xrdgroup]
        counts = self.get_counts_rect(ymin, ymax, xmin, xmax,
                                      mapdat=mapdat, dtcorrect=False)
        counts = counts[area[ymin:ymax, xmin:xmax]]

        name = '%s: %s' % (xrdgroup, areaname)
        kws['energy'] = energy = 0.001 * self.get_incident_energy()
        kws['wavelength'] = lambda_from_E(energy, E_units='keV')

        counts = counts.sum(axis=0)
        xrd = XRD(data1D=counts, steps=len(counts), name=name, **kws)
        if xrdgroup != 'xrd1d':
            xpix, ypix = counts.shape
            xrd = XRD(data2D=counts, xpixels=xpix, ypixels=ypix, name=name, **kws)

        path, fname = os.path.split(self.filename)
        xrd.filename = fname
        xrd.areaname = xrd.title = name
        xrd.mapname = mapdat.name
        fmt = "Data from File '%s', detector '%s', area '%s'"
        xrd.info  =  fmt % (self.filename, mapdat.name, name)
        xrd.q = mapdat['q'][()]
        return xrd

    def get_xrd2d_area(self, areaname, callback=None, **kws):
        '''return 2D XRD pattern for a pre-defined area

        Parameters
        ---------
        areaname :   str       name of area

        Returns
        -------
        diffraction pattern for given area

        Notes
        ------
        slow because it really reads from the raw XRD h5 files
        '''
        try:
            area = self.get_area(areaname)[()]
        except:
            raise GSEXRM_Exception("Could not find area '%s'" % areaname)
            return
        npix = area.sum()
        if npix < 1:
            return None

        xrdgroup = 'xrd2d'
        xrdgrp = ensure_subgroup('xrd2d', self.xrmmap, dtype='2DXRD')

        stps, xpix, ypix, qdat = 0, 0, 0, None
        sy, sx = [slice(min(_a), max(_a)+1) for _a in np.where(area)]
        xmin, xmax, ymin, ymax = sx.start, sx.stop, sy.start, sy.stop
        nx, ny = (xmax-xmin), (ymax-ymin)
        xrd_file = os.path.join(self.folder, self.rowdata[0][4])
        if os.path.exists(xrd_file):
            print("Reading XRD Patterns for rows %d to %d" %(ymin, ymax))
            data = None
            for yrow in range(ymin, ymax+1):
                xrd_file = os.path.join(self.folder, self.rowdata[yrow][4])
                print("row ", yrow)
                h5file = h5py.File(xrd_file, 'r')
                rowdat = h5file['entry/data/data'][1:,:,:]
                h5file.close()
                if (yrow  % 2) == 1:
                    rowdat = rowdat[::-1, :, :]
                rowdat = rowdat[np.where(area[yrow])[0], :, :].sum(axis=0)
                if data is None:
                    data = rowdat
                else:
                    data += rowdat

        name = '%s: %s' % (xrdgroup, areaname)
        kws = {}
        kws['energy'] = energy = 0.001 * self.get_incident_energy()
        kws['wavelength'] = lambda_from_E(energy, E_units='keV')
        xrd = XRD(data2D=data, name=name, **kws)
        print("made xrd ", xrd, kws)
        path, fname = os.path.split(self.filename)
        xrd.filename = fname
        xrd.areaname = xrd.title = areaname
        fmt = "Data from File '%s', XRD 2d, area '%s'"
        xrd.info  =  fmt % (self.filename, areaname)
        xrd.ponifile = self.xrdcalfile
        return xrd


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
                if bytes2str(nam.lower()) == name.lower():
                    index = ix
                    break
        if index == -1:
            raise GSEXRM_Exception("Could not find position %s" % repr(name))
        pos = self.xrmmap['positions/pos'][:, :, index]
        if index in (0, 1) and mean:
            pos = pos.sum(axis=index)/pos.shape[index]
        return pos


    def build_xrd_roimap(self, xrd='1d'):
        detname = None
        xrdtype = 'xrd%s detector' % xrd

        roigroup = ensure_subgroup('roimap', self.xrmmap, dtype='roi maps')
        for det, grp in self.xrmmap.items():
            if bytes2str(grp.attrs.get('type', '')).startswith(xrdtype):
                detname = det
                ds = ensure_subgroup(det, roigroup)
                ds.attrs['type'] = xrdtype
        return roigroup, detname

    def add_xrd2droi(self, xyrange, roiname, unit='pixels'):

        if version_ge(self.version, '2.0.0'):
            if not self.has_xrd2d:
                return

            roigroup, detname = self.build_xrd_roimap(xrd='2d')
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
            self.get_roi_list(detname, force=True)

        else:
            print('Only compatible with newest hdf5 mapfile version.')


    def read_xrd1d_ROIFile(self,filename,verbose=False):

        roidat = readROIFile(filename,xrd=True)
        print('\nReading 1D-XRD ROI file: %s' % filename)
        for iroi, label, xunit, xrange in roidat:
            print(' Adding ROI: %s' % label)
            self.add_xrd1droi(xrange,label,unit=xunit)
        print('Finished.\n')

    def add_xrd1droi(self, xrange, roiname, unit='q', subtract_bkg=False):
        if not version_ge(self.version, '2.0.0'):
            print('Only compatible with newest hdf5 mapfile version.')
            return

        if not self.has_xrd1d:
            print('No 1D-XRD data in file')
            return

        if self.incident_energy is None:
            self.incident_energy = self.get_incident_energy()

        if unit.startswith('2th'): ## 2th to 1/A
            qrange = q_from_twth(xrange,
                                 lambda_from_E(self.incident_energy, E_units='eV'))
        elif unit == 'd':           ## A to 1/A
            qrange = q_from_d(xrange)
        else:
            qrange = xrange

        roigroup, detname  = self.build_xrd_roimap(xrd='1d')

        if roiname in roigroup[detname]:
            raise ValueError("Name '%s' exists in 'roimap/%s' arrays." % (roiname, detname))

        # print("ADD XRD1D ROI ", detname, xrange, roiname, unit)
        counts = self.xrmmap[detname]['counts']
        q = self.xrmmap[detname]['q'][:]

        imin = (np.abs(q-qrange[0])).argmin()
        imax = (np.abs(q-qrange[1])).argmin()+1

        xrd1d_sum = xrd1d_cor = counts[:, :, imin:imax].sum(axis=2)
        if subtract_bkg and imax > imin:
            ibkglo = max(0, imin-3)
            ibkghi = min(len(q), imax+3)
            bkglo = counts[:,:,ibkglo:imin].sum(axis=2)/(imin-ibkglo)
            bkghi = counts[:,:,imax::ibkghi].sum(axis=2)/(ibkghi-imax)
            xrd1d_cor -=  (imax-imin)* (bkglo + bkghi)/2.0
        # print("ADD XRD1D ROI ", roiname, detname,
        #       xrd1d_sum.sum(), xrd1d_sum.mean())
        self.save_roi(roiname, detname, xrd1d_sum, xrd1d_cor,
                      qrange,'q', '1/A')
        self.get_roi_list(detname, force=True)


    def del_all_xrd1droi(self):

        ''' delete all 1D-XRD ROI'''

        roigrp_xrd1d = ensure_subgroup('xrd1d', self.xrmmap['roimap'])

        for roiname in roigrp_xrd1d.keys():
            self.del_xrd1droi(roiname)

    def del_xrd1droi(self, roiname):

        ''' delete a 1D-XRD ROI'''

        roigrp_xrd1d = ensure_subgroup('xrd1d', self.xrmmap['roimap'])

        if roiname not in roigrp_xrd1d.keys():
            print("No ROI named '%s' found to delete" % roiname)
            return

        roiname = h5str(roiname)
        if roiname in roigrp_xrd1d:
            del roigrp_xrd1d[roiname]
            self.h5root.flush()


    def save_roi(self,roiname,det, raw, cor, drange, dtype, units):
        ds = ensure_subgroup(roiname, self.xrmmap['roimap'][det])
        ds.create_dataset('raw',    data=raw   )
        ds.create_dataset('cor',    data=cor   )
        ds.create_dataset('limits', data=drange )
        ds['limits'].attrs['type']  = dtype
        ds['limits'].attrs['units'] = units

        self.h5root.flush()

    def build_mca_roimap(self):
        det_list = []
        sumdet = None
        roigroup = ensure_subgroup('roimap', self.xrmmap, dtype='roi map')
        for det, grp in zip(self.xrmmap.keys(),self.xrmmap.values()):
            if bytes2str(grp.attrs.get('type', '')).startswith('mca det'):
                det_list   += [det]
                ds = ensure_subgroup(det, roigroup)
                ds.attrs['type'] = 'mca detector'
            if bytes2str(grp.attrs.get('type', '')).startswith('virtual mca'):
                sumdet = det
                ds = ensure_subgroup(det,roigroup)
                ds.attrs['type'] = 'virtual mca detector'

        return roigroup, det_list, sumdet

    def add_xrfroi(self, Erange, roiname, unit='keV'):

        if not self.has_xrf:
            return

        if unit == 'eV': Erange[:] = [x/1000. for x in Erange] ## eV to keV

        roigroup, det_list, sumdet  = self.build_mca_roimap()
        if sumdet is None: sumdet = 'mcasum'

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
        self.get_roi_list('mcasum', force=True)



    def check_roi(self, roiname, det=None, version=None):
        if version is None:
            version = self.version

        if (type(det) is str and det.isdigit()) or type(det) is int:
            det = int(det)
            detname = 'mca%i' % det
        else:
            detname = det

        if roiname is not None: roiname = roiname.lower()

        if version_ge(version, '2.0.0'):
            for d in self.get_detector_list():
                if detname.lower() == d.lower():
                    for rname in self.xrmmap[d]:
                        if roiname.lower() == rname.lower():
                            return rname, d

            if detname is not None:
                detname = detname.replace('det', 'mca')

            if detname is None:
                detname = 'roimap/mcasum'
            elif not detname.startswith('roimap'):
                detname = 'roimap/%s' % detname

            try:
                roi_list = [r for r in self.xrmmap[detname]]
                if roiname is None:
                    return roi_list, detname
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

            if detname in ['det%d' % (i+1) for i in range(self.nmca)]:
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


    def get_roimap(self, roiname, det=None, hotcols=None, zigzag=None,
                   dtcorrect=None, minval=None, maxval=None):
        '''extract roi map for a pre-defined roi by name
        Parameters
        ---------
        roiname    :  str                     ROI name
        det        :  str                     detector name
        dtcorrect  :  optional, bool [None]   dead-time correct data
        hotcols    :  optional, bool [None]   suppress hot columns
        minval:     float, trim to minimum value
        maxval:     float, trim to maximum value

        Returns
        -------
        ndarray for ROI data
        '''
        if hotcols is None:
            hotcols = self.hotcols
        if zigzag is None:
            zigzag = self.zigzag
        if dtcorrect is None:
            dtcorrect = self.dtcorrect

        nrow, ncol, npos = self.xrmmap['positions']['pos'].shape
        out = np.zeros((nrow, ncol))

        det = self.get_detname(det)
        dtcorrect = dtcorrect and ('mca' in det or 'det' in det)

        if roiname == '1' or roiname == 1:
            out = np.ones((nrow, ncol))
            if hotcols:
                out = out[1:-1]
            return out

        roi, detaddr = self.check_roi(roiname, det)
        ext = ''
        if detaddr.startswith('roimap'):
            ext = 'raw'
        if dtcorrect:
            ext = 'cor'

        # print("GetROIMAP roiname=%s|roi=%s|det=%s" % (roiname, roi, det))
        # print("detaddr=%s|ext=%s|version=%s" % (detaddr, ext, self.version))
        if version_ge(self.version, '2.0.0'):
            if detaddr.startswith('roimap'):
                roi_ext = '%s/' + ext
            else:
                roi_ext = '%s_' + ext if ext == 'raw' else '%s'
            roiaddr =  roi_ext % roi
            # print("looking for detattr, roiaddr ", detaddr, roiaddr)
            try:
                out = self.xrmmap[detaddr][roiaddr][:]
            except (KeyError, OSError):
                _roiname, _roic = roiaddr.split('/')
                try:
                    del self.xrmmap[detaddr][_roiname]
                except:
                    pass
                rgrp = self.xrmmap[detaddr].create_group(_roiname)
                for aname,dtype in (('raw', np.uint32),
                                    ('cor', np.float32)):
                    rgrp.create_dataset(aname, (1, ncol), dtype,
                                        chunks=(1, ncol),
                                        maxshape=(None, ncol), **self.compress_args)
                lmtgrp = rgrp.create_dataset('limits', data=[0., 0.], **self.compress_args)
                lmtgrp.attrs['type'] = 'energy'
                lmtgrp.attrs['units'] = 'keV'

                out = np.zeros([1, ncol])
            # print("found roi data ", out.shape, nrow, ncol)
            if version_ge(self.version, '2.1.0') and out.shape != (nrow, ncol):
                _roi, _detaddr = self.check_roi(roiname, det, version='1.0.0')
                detname = '%s%s' % (_detaddr, ext)
                out = self.xrmmap[detname][:, :, _roi]
                self.xrmmap[detaddr][roiaddr].resize((nrow, ncol))
                self.xrmmap[detaddr][roiaddr][:, :] = out

        else:  # version1
            if det in EXTRA_DETGROUPS:
                detname = "%s/%s" % (det, roiname)
                out = self.xrmmap[detname][:,:]
            else:
                detname = '%s%s' % (detaddr, ext)
                out = self.xrmmap[detname][:, :, roi]

        if zigzag is not None and zigzag != 0:
            out = remove_zigzag(out, zigzag)
        elif hotcols:
            out = out[:, 1:-1]
        if minval is not None:
            out[np.where(out<minval)] = minval
        if maxval is not None:
            out[np.where(out>maxval)] = maxval
        return out


    def get_mca_erange(self, det=None, dtcorrect=None,
                       emin=None, emax=None, by_energy=True):
        '''extract map for an ROI set here, by energy range:

        not implemented
        '''
        pass

    def get_rgbmap(self, rroi, groi, broi, det=None, rdet=None, gdet=None, bdet=None,
                   hotcols=None, dtcorrect=None, scale_each=True, scales=None):
        '''return a (NxMx3) array for Red, Green, Blue from named
        ROIs (using get_roimap).

        Parameters
        ----------
        rroi :       str    name of ROI for red channel
        groi :       str    name of ROI for green channel
        broi :       str    name of ROI for blue channel
        det  :       optional, None or int [None]  index for detector
        dtcorrect :  optional, bool [None]         dead-time correct data
        hotcols   :  optional, bool [None]         suppress hot columns
        scale_each : optional, bool [True]
                     scale each map separately to span the full color range.
        scales :     optional, None or 3 element tuple [None]
                     multiplicative scale for each map.

        By default (scales_each=True, scales=None), each map is scaled by
        1.0/map.max() -- that is 1 of the max value for that map.

        If scales_each=False, each map is scaled by the same value
        (1/max intensity of all maps)

        '''
        if hotcols is None:
            hotcols = self.hotcols
        if dtcorrect is None:
            dtcorrect = self.dtcorrect
        if det is not None:
            rdet = gdet = bdet = det

        kws = dict(hotcols=hotcols, dtcorrect=dtcorrect)
        rmap = self.get_roimap(rroi, det=rdet, **kws)
        gmap = self.get_roimap(groi, det=gdet, **kws)
        bmap = self.get_roimap(broi, det=bdet, **kws)

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

    def del_roi(self, name):
        ''' delete an ROI'''
        roi_names = [i.lower().strip() for i in self.xrmmap['config/rois/name']]
        if name.lower().strip() not in roi_names:
            print("No ROI named '%s' found to delete" % name)
            return
        iroi = roi_names.index(name.lower().strip())
        roi_names = [i in self.xrmmap['config/rois/name']]
        roi_names.pop(iroi)


def read_xrmmap(filename, root=None, **kws):
    '''read GSE XRF FastMap data from HDF5 file or raw map folder'''
    key = 'filename'
    if os.path.isdir(filename):
        key = 'folder'
    kws.update({key: filename, 'root': root})

    return GSEXRM_MapFile(**kws)

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
