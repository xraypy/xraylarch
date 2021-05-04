import os
import numpy as np
import time

import larch

from larch.io import (read_xsp3_hdf5, read_xrf_netcdf,
                      read_xrd_netcdf, read_xrd_hdf5)
from larch.utils.strutils import fix_varname
from .asciifiles import (readASCII, readMasterFile, readROIFile,
                         readEnvironFile, read1DXRDFile, parseEnviron)

from ..xrd import integrate_xrd_row

def fix_xrd1d_filename(xrd_file):
    """check for 1D XRD file from Eiger or other detector --
    avoids having to read hdf5 file at all
    """
    # first append '.npy'
    xrd1d_file = xrd_file  + '.npy'
    if os.path.exists(xrd1d_file):
        return xrd1d_file

    # second, eiger .h5 -> .npy
    xrd1d_file = xrd_file.replace('.h5', '.npy').replace('_master', '')
    if os.path.exists(xrd1d_file):
        return xrd1d_file

    return None

def parse_sisnames(text):
    return [fix_varname(s.strip()) for s in text.replace('#', '').split('|')]

class GSEXRM_FileStatus:
    no_xrfmap    = 'hdf5 does not have top-level XRF map'
    no_xrdmap    = 'hdf5 does not have top-level XRD map'
    created      = 'hdf5 has empty schema'  # xrm map exists, no data
    hasdata      = 'hdf5 has map data'      # array sizes known
    wrongfolder  = 'hdf5 exists, but does not match folder name'
    err_notfound = 'file not found'
    empty        = 'file is empty (read from folder)'
    err_nothdf5  = 'file is not hdf5 (or cannot be read)'
    err_nowrite  = 'user does not have write permission'


class GSEXRM_Exception(Exception):
    '''GSEXRM Exception: General Errors'''
    pass


class GSEXRM_MCADetector(object):
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
    def __init__(self, xrmmap, prefix='mca', index=None):
        self.xrmmap = xrmmap
        self.prefix = prefix
        self.__ndet =  xrmmap.attrs.get('N_Detectors', 0)
        self.det = None
        self.rois = []
        detname = '%s1' % prefix
        if index is not None:
            detname = '%s%i' % (prefix, index)
            self.det = self.xrmmap[detname]

        self.shape =  self.xrmmap['%s/livetime' % detname].shape

        # energy
        self.energy = self.xrmmap['%s/energy' % detname][()]

        # set up rois
        rnames = self.xrmmap['%s/roi_names' % detname][()]
        raddrs = self.xrmmap['%s/roi_addrs' % detname][()]
        rlims  = self.xrmmap['%s/roi_limits' % detname][()]
        for name, addr, lims in zip(rnames, raddrs, rlims):
            self.rois.append(ROI(name=name, address=addr,
                                 left=lims[0], right=lims[1]))

    def __getval(self, param):
        if self.det is None:
            out = self.xrmmap['%s1/%s' % (self.prefix, param)][()]
            for i in range(2, self.__ndet):
                out += self.xrmmap['%s%i/%s' % (self.prefix, i, param)][()]
            return out
        return self.det[param][()]

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
        self.det = GSEXRM_Detector(xrmmap, index=det)
        if isinstance(index, int):
            index = 'area_%3.3i' % index
        self._area = self.xrmmap['areas/%s' % index]
        self.npts = self._area[()].sum()

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


class GSEXRM_MapRow:
    '''
    read one row worth of data:
    '''
    def __init__(self, yvalue, xrffile, xrdfile, xpsfile, sisfile, folder,
                 reverse=False, ixaddr=0, dimension=2, ioffset=0,
                 npts=None,  irow=None, dtime=None, nrows_expected=None,
                 masterfile=None, xrftype=None, xrdtype=None,
                 xrdcal=None, xrd2dmask=None, xrd2dbkgd=None,
                 wdg=0, steps=4096, flip=True, force_no_dtc=False,
                 has_xrf=True, has_xrd2d=False, has_xrd1d=False):

        self.read_ok = False
        self.nrows_expected = nrows_expected

        offslice = slice(None, None, None)
        if ioffset is None:
            ioffset = 0
        if ioffset > 0:
            offslice = slice(ioffset, None, None)
        elif ioffset < 0:
            offslice = slice(None, ioffset, None)
        self.npts = npts
        self.irow = irow
        if self.irow is None:
            self.irow = 0

        self.yvalue  = yvalue
        self.xrffile = xrffile
        self.xpsfile = xpsfile
        self.sisfile = sisfile
        self.xrdfile = xrdfile
        self.counts  = None

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
        if has_xrf:
            if xrftype is None:
                xrftype = 'netcdf'
                if xrffile.startswith('xsp3'):
                    xrftype = 'hdf5'
            if xrftype == 'netcdf':
                xrf_reader = read_xrf_netcdf
            else:
                xrf_reader = read_xsp3_hdf5

        if has_xrd2d or has_xrd1d:
            if xrdtype == 'hdf5' or xrdfile.endswith('.h5'):
                xrd_reader = read_xrd_hdf5
            elif xrdtype == 'netcdf' or xrdfile.endswith('nc'):
                xrd_reader = read_xrd_netcdf
            else:
                xrd_reader = read_xrd_netcdf

            # print( "xrd_reader ", xrd_reader, xrdtype, xrdfile, ' cal :%s: ' % xrdcal)
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

        # extrapolate gathering data by in case final end-point trigger was missed
        gather_extra = (2*gdata[-1] - gdata[-2]).reshape((1, gdata.shape[1]))
        gdata = np.concatenate((gdata, gather_extra))
        gnpts, ngather  = gdata.shape
        self.sishead = shead
        self.scaler_names = parse_sisnames(self.sishead[-1])
        self.scaler_addrs = ['']*len(self.scaler_names)
        for sline in shead:
            if sline.startswith('# Column'):
                l, val = sline.split(': ')
                val = val.strip()
                label, addr, formula = [x.strip() for x in val.split('|')]
                if label in self.scaler_names:
                    i = self.scaler_names.index(label)
                    self.scaler_addrs[i] = addr

        if dtime is not None:
            dtime.add('maprow: read ascii files')
        t0 = time.time()
        atime = -1
        xrf_dat, xrf_file = None, os.path.join(folder, xrffile)
        xrd_dat, xrd_file = None, os.path.join(folder, xrdfile)
        xrd1d_file = fix_xrd1d_filename(xrd_file)
        has_xrd1d = xrd1d_file is not None
        while atime < 0 and time.time()-t0 < 10:
            try:
                atime = os.stat(os.path.join(folder, sisfile)).st_ctime
                if has_xrf:
                    xrf_dat = xrf_reader(xrf_file, npixels=self.nrows_expected, verbose=False)
                    if xrf_dat is None:
                        print( 'Failed to read XRF data from %s' % self.xrffile)
                if has_xrd2d or (has_xrd1d and xrd1d_file is None):
                    xrd_dat = xrd_reader(xrd_file, verbose=False)
                    if xrd_dat is None:
                        print( 'Failed to read XRD data from %s' % self.xrdfile)

            except (IOError, IndexError):
                time.sleep(0.025)

        if atime < 0:
            print( 'Failed to read data.')
            return
        if dtime is not None:
            dtime.add('maprow: read XRM files')

        ## SPECIFIC TO XRF data
        if has_xrf:
            self.counts    = xrf_dat.counts[offslice]
            self.inpcounts = xrf_dat.inputCounts[offslice]
            self.outcounts = xrf_dat.outputCounts[offslice]

            if self.inpcounts.max() < 1:
                self.inpcounts = self.counts.sum(axis=2)
            if self.outcounts.max() < 1:
                self.outcounts = self.inpcounts*1.0

            self.livetime  = xrf_dat.liveTime[offslice]
            self.realtime  = xrf_dat.realTime[offslice]
            if self.livetime.max() < 0.01:
                self.livetime = 0.100 * np.ones(self.livetime.shape)
            if self.realtime.max() < 0.01:
                self.realtime = 0.100 * np.ones(self.realtime.shape)

            dt_denom = self.outcounts*self.livetime
            dt_denom[np.where(dt_denom < 1)] = 1.0
            self.dtfactor  = self.inpcounts*self.realtime/dt_denom
            self.dtfactor[np.where(np.isnan(self.dtfactor))] = 1.0
            self.dtfactor[np.where(self.dtfactor < 0.95)] = 0.95
            if force_no_dtc: # in case deadtime info is unreliable (some v old data)
                self.outcounts = self.inpcounts*1.0
                self.livetime  = self.realtime*1.0
                self.dtfactor  = np.ones(self.dtfactor.shape)

        ## SPECIFIC TO XRD data
        if has_xrd2d or has_xrd1d:
            if has_xrd2d:
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

            # print("read XRD1D file? ", irow, has_xrd1d, xrdcal, xrdcal is not None, xrd1d_file)
            if has_xrd1d and xrdcal is not None:
                attrs = dict(steps=steps, flip=flip)
                if xrd1d_file is not None:
                    xdat = np.load(xrd1d_file)
                    self.xrdq  = xdat[0, :]
                    self.xrd1d = xdat[1:, :]
                    # print(">>>READ XRDQ 1D ", xrd1d_file, self.xrdq.shape, self.xrd1d.shape)
                if self.xrdq is None and self.xrd2d is not None: # integrate data if needed.
                    print("will try to integrate 2DXRD data ", self.xrd2d.shape)
                    # attrs['flip'] = True
                    # self.xrd2d = self.xrd2d[:, 1:-1, 3:-3]
                    # maxval = 2**32 - 2**14
                    self.xrd2d[np.where(self.xrd2d>maxval)] = 0
                    self.xrdq, self.xrd1d = integrate_xrd_row(self.xrd2d, xrdcal,
                                                              **attrs)
                    # print("Integrated to ", self.xrdq.shape)
                if wdg > 1:
                    self.xrdq_wdg, self.xrd1d_wdg = [], []
                    wdg_sz = 360./int(wdg)
                    for iwdg in range(wdg):
                        wdg_lmts = np.array([iwdg*wdg_sz, (iwdg+1)*wdg_sz]) - 180
                        attrs.update({'wedge_limits':wdg_lmts})
                        q, counts = integrate_xrd_row(self.xrd2d, xrdcal, **attrs)
                        self.xrdq_wdg  += [q]
                        self.xrd1d_wdg += [counts]

                    self.xrdq_wdg  = np.einsum('kij->ijk', self.xrdq_wdg)
                    self.xrd1d_wdg = np.einsum('kij->ijk', self.xrd1d_wdg)


        xnpts, nmca = gnpts, 1
        if has_xrf:
            xnpts, nmca, nchan = self.counts.shape

        snpts, nscalers = sdata.shape

        # print("Row npts=%s, gather=%d, sis=%d, xrf=%d" %
        #       (repr(self.npts), gnpts, snpts, xnpts))

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
            if has_xrf:
                self.counts    = self.counts[:self.npts]
                self.realtime  = self.realtime[:self.npts]
                self.livetime  = self.livetime[:self.npts]
                self.dtfactor  = self.dtfactor[:self.npts]
                self.inpcounts = self.inpcounts[:self.npts]
                self.outcounts = self.outcounts[:self.npts]
            if has_xrd2d:
                self.xrd2d = self.xrd2d[:self.npts]
            if has_xrd1d:
                # self.xrdq, self.xrd1d = self.xrdq[:self.npts], self.xrd1d[:self.npts]
                # print(" -- has xrd1d ->  ",  xnpts, self.npts, self.xrdq.shape)
                if self.xrdq_wdg is not None:
                    self.xrdq_wdg    = self.xrdq_wdg[:self.npts]
                    self.xrd1d_wdg   = self.xrd1d_wdg[:self.npts]

        points = list(range(1, self.npts+1))
        # auto-reverse: counter-intuitively (because stage is upside-down and so
        # backwards wrt optical view), left-to-right scans from high to low value
        # so reverse those that go from low to high value
        # first, find fast axis:
        ixaddr, gvarmax = 0, -1
        for ig in range(ngather):
            gvar = gdata[:, ig].std()
            if gvar > gvarmax:
                gvarmax = gvar
                ixaddr = ig

        if reverse:
            do_reverse = gdata[0, ixaddr] < gdata[-1, ixaddr]
        else:
            do_reverse = gdata[0, ixaddr] > gdata[-1, ixaddr]

        do_reverse = (irow % 2) == 1
        self.reversed = do_reverse
        if do_reverse:
            points.reverse()
            self.sisdata  = self.sisdata[::-1]
            if has_xrf:
                self.counts  = self.counts[::-1]
                self.realtime = self.realtime[::-1]
                self.livetime = self.livetime[::-1]
                self.dtfactor = self.dtfactor[::-1]
                self.inpcounts= self.inpcounts[::-1]
                self.outcounts= self.outcounts[::-1]
            if has_xrd2d and self.xrd2d is not None:
                self.xrd2d = self.xrd2d[::-1]
            if has_xrd1d and self.xrd1d is not None:
                self.xrd1d = self.xrd1d[::-1]
                if self.xrdq_wdg is not None:
                    self.xrdq_wdg        = self.xrdq_wdg[::-1]
                    self.xrd1d_wdg       = self.xrd1d_wdg[::-1]

        if has_xrf:
            xvals = [(gdata[i, ixaddr] + gdata[i-1, ixaddr])/2.0 for i in points]
            self.posvals = [np.array(xvals)]
            if dimension == 2:
                self.posvals.append(np.array([float(yvalue) for i in points]))
            self.posvals.append(self.realtime.sum(axis=1).astype('float32') / nmca)
            self.posvals.append(self.livetime.sum(axis=1).astype('float32') / nmca)

            self.dtfactor = self.dtfactor.astype('float32').swapaxes(0, 1)
            self.inpcounts= self.inpcounts.swapaxes(0, 1)
            self.outcounts= self.outcounts.swapaxes(0, 1)
            self.livetime = self.livetime.swapaxes(0, 1)
            self.realtime = self.realtime.swapaxes(0, 1)
            self.counts   = self.counts.swapaxes(0, 1)
            iy, ix = self.dtfactor.shape

            self.total = self.counts.sum(axis=0)
            # dtfactor for total
            total_dtc = (self.counts * self.dtfactor.reshape(iy, ix, 1)).sum(axis=0).sum(axis=1)
            dt_denom = self.total.sum(axis=1)
            dt_denom[np.where(dt_denom < 1)] = 1.0
            dtfact  = total_dtc / dt_denom
            dtfact[np.where(np.isnan(dtfact))] = 1.0
            dtfact[np.where(dtfact < 0.95)] = 0.95
            dtfact[np.where(dtfact > 50.0)] = 50.0
            self.total_dtfactor = dtfact
        self.read_ok = True
