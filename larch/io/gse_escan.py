#!/usr/bin/env python

import os
import sys
import copy
import time
import gc

import numpy
from larch import Group
from larch.utils import isotime

def _cleanfile(x):
    for o in ' ./?(){}[]",&%^#@$': x = x.replace(o,'_')
    return x

class EscanData:
    """ Epics Scan Data """
    mode_names = ('2d', 'epics scan',
                  'user titles', 'pv list',
                  '-----','=====','n_points',
                  'scan began at', 'scan ended at',
                  'column labels', 'scan regions','data')

    def __init__(self, fname=None, bad=None, **args):
        self.path = suffix = fname
        if fname is not None:
            pref, suffix = os.path.split(fname)
        self.filename    = suffix
        self.bad_channels = bad
        self.clear_data()

        self.progress    = None
        self.message     = self.message_printer

        for k in args.keys():
            if (k == 'progress'): self.progress = args[k]
            if (k == 'message'):  self.message  = args[k]

        if self.path not in ('',None):
            self.status = self.read_data_file(fname=self.path)

    def clear_data(self):
        self.xdesc       = ''
        self.ydesc       = ''
        self.xaddr       = ''
        self.yaddr       = ''
        self.start_time  = ''
        self.stop_time   = ''
        self.dimension   = 1
        self.scan_prefix = ''
        self.user_titles = []
        self.scan_regions= []

        self.env_desc    = []
        self.env_addr    = []
        self.env_val     = []
        self.pos         = []
        self.det         = []
        self.data        = []
        self.pos_desc    = []
        self.pos_addr    = []
        self.det_desc    = []
        self.det_addr    = []
        self.det_mcas    = []
        self.sums       = []
        self.sums_names = []
        self.sums_list  = []
        self.dt_factor       = None

        self.has_fullxrf    = False
        self.xrf_data     = []
        self.xrf_sum      = []
        self.xrf_energies = []
        self.xrf_header = ''
        self.xrf_dict   = {}
        self.xrf_merge  = None
        self.xrf_merge_corr  = None
        self.roi_names  = []
        self.roi_llim   = []
        self.roi_hlim  = []

        self.x = numpy.array(0)
        self.y = numpy.array(0)
        if self.bad_channels is None:
            self.bad_channels = []
        gc.collect()


    def message_printer(self,s,val):
        sys.stdout.write("%s\n" % val)

    def my_progress(self,val):
        sys.stdout.write("%f .. " % val)
        sys.stdout.flush()

    def filetype(self,fname=None):
        """ checks file type of file, returning:
        'escan'  for  Epics Scan
        None     otherwise
        """
        try:
            u = open(fname,'r')
            t = u.readline()
            u.close()
            if 'Epics Scan' in t: return 'escan'

        except IOError:
            pass

        return None

    def get_map(self,name=None,norm=None):
        return self.get_data(name=name,norm=norm)

    def get_data(self, name=None, norm=None, correct=True):
        """return data array by name"""
        dat = self._getarray(name, correct=correct)
        if norm is not None and dat is not None:
            norm = self._getarray(norm,  correct=True)
            dat  = dat/norm
        return dat

    def match_detector_name(self, sname, strict=False):
        """return index in self.det_desc most closely matching supplied string"""
        s  = sname.lower()
        sw = s.split()
        dnames  = [i.lower() for i in self.det_desc]

        # look for exact match
        for nam in dnames:
            if s == nam:  return dnames.index(nam)

        # look for inexact match 1: compare 1st words
        for nam in dnames:
            sx = nam.split()
            if sw[0] == sx[0]:
                return dnames.index(i)

        # check for 1st word in the det name
        if not strict:
            for dnam in dnames:
                j = dnam.find(sw[0])
                if (j >= 0):  return dnames.index(i)
        # found no matches
        return -1

    def ShowProgress(self,val,row=-1):
        if (self.progress != None):
            self.progress(val)
        elif (row>-1):
            print( " %3i " % (row),)
            if (row %10 == 0): print("")

    def ShowMessage(self,val,state='state'):
        if (self.message != None):
            self.message(state,val)

    def PrintMessage(self,s):
        sys.stdout.write(s)
        sys.stdout.flush()

    def read_data_file(self,fname=None):
        """generic data file reader"""
        if fname is None:
            fname = self.path
        read_ascii = True
        if read_ascii:
            retval = self.read_ascii(fname=fname)
            if retval is not None:
                msg = "problem reading file %s" % fname
                self.ShowMessage(msg)
            gc.collect()
        return retval

    def _getarray(self, name=None, correct=True):
        i = None
        arr = None
        for ip, pname in enumerate(self.pos_desc):
            if name.lower() == pname.lower():
                return self.pos[ip]
        if 'mca' in name:
            name = name.replace('(', '').replace(')', '')
            words = name.replace('mca', '@@').split('@@', 2)
            name = words[0].strip().lower()
            mca = int(words[1])
            if len(self.det_mcas) < 1:
                self.det_mcas = [None for i in self.det_desc]
                for idet, addr in enumerate(self.det_addr):
                    a = addr.lower().split('.')[0]
                    if 'mca' in a:
                         w = a.split('mca')[1]
                         self.det_mcas[idet] = int(w)
            for idet, nam in enumerate(self.det_desc):
                name1 = nam.strip().lower()
                # print( idet, name, name1, mca, self.det_mcas[idet])
                if name == name1 and mca == self.det_mcas[idet]:
                    i = idet
                    break
            # print('GETARRAY with mca in name: ', name, mca,  ' --> ', i)
            arr = self.det
            if correct: arr = self.det_corr
        elif name in self.sums_names:
            i = self.sums_names.index(name)
            arr = self.sums
            if correct: arr = self.sums_corr
        else:
            i = self.match_detector_name(name)
            arr = self.det
            if correct: arr = self.det_corr
        if i is not None:
            return arr[i]

        return None


    def _open_ascii(self,fname=None):
        """open ascii file, return lines after some checking"""
        if fname is None:
            fname = self.path
        if fname is None: return None

        self.ShowProgress(1.0)
        #  self.ShowMessage("opening file %s  ... " % fname)
        try:
            f = open(fname,'r')
            lines = f.readlines()
            lines.reverse()
            f.close()
        except:
            self.ShowMessage("ERROR: general error reading file %s " % fname)
            return None

        line1    = lines.pop()
        if 'Epics Scan' not in line1:
            self.ShowMessage("Error: %s is not an Epics Scan file" % fname)
            return None
        return lines

    def _getline(self,lines):
        "return mode keyword,"
        inp = lines.pop()
        is_comment = True
        mode = None
        if len(inp) > 2:
            is_comment = inp[0] in (';','#')
            s   = inp[1:].strip().lower()
            for j in self.mode_names:
                if s.startswith(j):
                    mode = j
                    break
            if mode is None and not is_comment:
                w1 = inp.strip().split()[0]
                try:
                    x = float(w1)
                    mode = 'data'
                except ValueError:
                    pass
        return (mode, inp)


    def _make_arrays(self, tmp_dat, col_legend, col_details):
        # convert tmp_dat to numpy 2d array
        dat = numpy.array(tmp_dat).transpose()
        # make raw position and detector data, using column labels
        npos = len( [i for i in col_legend if i.lower().startswith('p')])
        ndet = len( [i for i in col_legend if i.lower().startswith('d')])

        self.pos  = dat[0:npos,:]
        self.det  = dat[npos:,:]

        # parse detector labels
        for i in col_details:
            try:
                key,detail = i.split('=')
            except:
                break
            label,pvname = [i.strip() for i in detail.split('-->')]
            label = label[1:-1]
            if key.startswith('P'):
                self.pos_desc.append(label)
                self.pos_addr.append(pvname)
            else:
                self.det_desc.append(label)
                self.det_addr.append(pvname)


        # make sums of detectors with same name and isolate icr / ocr
        self.sums       = []
        self.sums_names = []
        self.sums_list  = []
        self.dt_factor       = None
        self.correct_deadtime = False
        icr, ocr = [], []
        detpvs = []
        sum_name = None
        isum = -1

        for i, det in enumerate(self.det_desc):
            thisname, thispv = det, self.det_addr[i]
            # avoid pvs listed more than once
            if thispv in detpvs:
                continue
            else:
                detpvs.append(thispv)
            if 'mca' in thisname and ':' in thisname:
                thisname = thisname.replace('mca','').split(':')[1].strip()
            if thisname != sum_name:
                sum_name = thisname
                self.sums_names.append(sum_name)
                isum  = isum + 1
                self.sums.append( self.det[i][:] )
                o = [i]
                self.sums_list.append(o)
            else:
                if i not in self.bad_channels:
                    self.sums[isum] = self.sums[isum] + self.det[i][:]
                    o.append(i)
                    self.sums_list[isum] = o
            if 'inputcountrate' in thisname.lower():
                icr.append(self.det[i][:])
                self.correct_deadtime = True
            if 'outputcountrate' in thisname.lower(): ocr.append(self.det[i][:])

        self.sums = numpy.array(self.sums)

        # print( '_make arrays: ICR OCR ', len(icr), len(icr[0]))
        # if icr/ocr data is included, pop them from
        # the detector lists.

        self.dt_factor = None
        if len(icr)>0 and len(ocr)==len(icr):
            try:
                self.dt_factor  = numpy.array(icr)/numpy.array(ocr)
                self.dt_factor[numpy.where(numpy.isnan(self.dt_factor))] = 1.0
            except:
                self.dt_factor  = numpy.ones(len(icr))

            n_icr     = self.dt_factor.shape[0]
            self.det  = self.det[0:-2*n_icr]
            self.sums = self.sums[0:-2*n_icr]
            self.sums_list  = self.sums_list[:-2*n_icr]
            self.sums_names = self.sums_names[:-2*n_icr]
            self.det_desc   = self.det_desc[:-2*n_icr]
            self.det_addr   = self.det_addr[:-2*n_icr]
            self.correct_deadtime = True

        if self.dimension == 2:
            print( '2D ', len(self.y), len(tmp_dat))
            ny = len(self.y)
            nx = len(tmp_dat)/ny

            self.det.shape  = (self.det.shape[0],  ny, nx)
            self.pos.shape  = (self.pos.shape[0],  ny, nx)
            self.sums.shape = (self.sums.shape[0], ny, nx)
            if self.dt_factor is not None:
                self.dt_factor.shape = (self.dt_factor.shape[0], ny, nx)

            self.x = self.pos[0,0,:]
        else:
            self.x = self.pos[0]
            nx = len(self.x)
            self.y = []

        self.data = numpy.vstack((self.pos, self.det))
        tnsums = [len(i) for i in self.sums_list]
        tnsums.sort()
        nsums = tnsums[-1]
        for s in self.sums_list:
            while len(s) < nsums:  s.append(-1)

        # finally, icr/ocr corrected sums
        self.det_corr  = 1.0 * self.det[:]
        self.sums_corr = 1.0 * self.sums[:]

        if self.correct_deadtime:
            idet = -1
            nmca = -1
            for label, pvname in zip(self.det_desc,self.det_addr):
                idet = idet + 1
                if 'mca' in pvname:
                    nmca = int(pvname.split('mca')[1].split('.')[0]) -1
                    if idet in self.bad_channels:
                        self.det_corr[idet,:] *= 0
                    else:
                        self.det_corr[idet,:] *= self.dt_factor[nmca,:]

            isum = -1
            for sumlist in self.sums_list:
                isum  = isum + 1
                if isinstance(sumlist, (list,tuple)):
                    self.sums_corr[isum] = self.det_corr[sumlist[0]]
                    for i in sumlist[1:]:
                        if i > 0 and i not in self.bad_channels:
                            self.sums_corr[isum] += self.det_corr[i]
                else:
                    self.sums_corr[isum] = self.det_corr[sumlist]
        return

    def read_ascii(self,fname=None):
        """read ascii data file"""
        lines = self._open_ascii(fname=fname)
        if lines is None: return -1

        maxlines = len(lines)

        iline = 1
        ndata_points = None
        tmp_dat = []
        tmp_y   = []
        col_details = []
        col_legend = None
        ntotal_at_2d = []
        ny_counter = 0
        mode = None
        while lines:
            key, raw = self._getline(lines)
            iline= iline+1
            if key is not None and key != mode:
                mode = key

            if (len(raw) < 3): continue
            self.ShowProgress( iline* 100.0 /(maxlines+1))

            if mode == '2d':
                self.dimension = 2
                sx   = raw.split()
                yval = float(sx[2])
                tmp_y.append(yval)
                self.yaddr = sx[1].strip()
                if self.yaddr.endswith(':'): self.yaddr = self.yaddr[:-1]
                mode = None
                if len(tmp_dat)>0:
                    ntotal_at_2d.append(len(tmp_dat))
            elif mode == 'epics scan':             # real numeric column data
                print( 'Warning: file appears to have a second scan appended!')
                break

            elif mode == 'data':             # real numeric column data
                tmp_dat.append(numpy.array([float(i) for i in raw.split()]))

            elif mode == '-----':
                if col_legend is None:
                    col_legend = lines.pop()[1:].strip().split()

            elif mode in ( '=====', 'n_points'):
                pass

            elif mode == 'user titles':
                self.user_titles.append(raw[1:].strip())

            elif mode == 'pv list':
                str = raw[1:].strip().replace('not connected',' = not connected')
                if str.lower().startswith(mode): continue
                desc = str
                addr = ''
                val  = 'unknown'
                try:
                    x =   str.split('=')
                    desc = x[0].replace('\t','').strip()
                    val = x[1].strip()
                    if '(' in desc and desc.endswith(')'):
                        n = desc.rfind('(')
                        addr = desc[n+1:-1]
                        desc = desc[:n].rstrip()
                except:
                    pass
                self.env_addr.append(addr)
                self.env_desc.append(desc)
                self.env_val.append(val)

            elif mode == 'scan regions':
                self.scan_regions.append(raw[1:].strip())

            elif mode == 'scan ended at':
                self.stop_time = raw[20:].strip()

            elif mode == 'scan began at':
                self.start_time = raw[20:].strip()

            elif mode == 'column labels':
                col_details.append(raw[1:].strip())

            elif mode is None:
                sx = [i.strip() for i in raw[1:].split('=')]
                if len(sx)>1:
                    if sx[0] == 'scan prefix':
                        self.scan_prefix = sx[1]
                    if sx[0] == 'scan dimension':
                        self.dimension = int(float(sx[1]))

            else:
                print( 'UNKOWN MODE = ',mode, raw[:20])

        del lines

        try:
            col_details.pop(0)

        except IndexError:
            print( 'Empty Scan File')
            return -2

        if len(self.user_titles) > 1: self.user_titles.pop(0)
        if len(self.scan_regions) > 1: self.scan_regions.pop(0)

        # check that 2d maps are of consistent size
        if self.dimension == 2:
            ntotal_at_2d.append(len(tmp_dat))
            np_row0 = ntotal_at_2d[0]
            nrows   = len(ntotal_at_2d)
            npts    = len(tmp_dat)
            if npts != np_row0 * nrows:
                for i,n in enumerate(ntotal_at_2d):
                    if n == np_row0*(i+1):
                        nrows,npts_total = i+1,n

                if len(tmp_y) > nrows or len(tmp_dat)> npts_total:
                    print( 'Warning: Some trailing data may be lost!')
                    tmp_y   = tmp_y[:nrows]
                    tmp_dat = tmp_dat[:npts_total]
            #
        self.y = numpy.array(tmp_y)
        # done reading file
        self._make_arrays(tmp_dat,col_legend,col_details)
        tmp_dat = None

        self.xaddr = self.pos_addr[0].strip()

        for addr,desc in zip(self.env_addr,self.env_desc):
            if self.xaddr == addr: self.xdesc = desc
            if self.yaddr == addr: self.ydesc = desc

        self.has_fullxrf = False
        if os.path.exists("%s.fullxrf" %fname):
            self.read_fullxrf("%s.fullxrf" %fname, len(self.x), len(self.y))

    def read_fullxrf(self,xrfname, n_xin, n_yin):
        inpf = open(xrfname,'r')

        atime = os.stat(xrfname)[8]

        prefix = os.path.splitext(xrfname)[0]
        print('Reading Full XRF spectra from %s'  % xrfname)

        first_line = inpf.readline()
        if not first_line.startswith('; MCA Spectra'):
            print('Warning: %s is not a QuadXRF File' % xrffile)
            inpf.close()
            return

        self.has_fullxrf = True
        isHeader= True
        nheader = 0
        header = {'CAL_OFFSET':None,'CAL_SLOPE':None,'CAL_QUAD':None}
        rois   = []

        n_energies = 2048

        while isHeader:
            line = inpf.readline()
            nheader = nheader + 1
            isHeader = line.startswith(';') and not line.startswith(';----')
            words = line[2:-1].split(':')
            if words[0] in header.keys():
                header[words[0]] = [float(i) for i in words[1].split()]
            elif words[0].startswith('ROI'):
                roinum = int(words[0][3:])
                rois.append((words[1].strip(),int(words[2]),int(words[3])))

        # end of header: read one last line
        line = inpf.readline()
        nelem = self.nelem = len(header['CAL_OFFSET'])

        nheader = nheader + 1
        # print('==rois==' , len(rois), len(rois)/nelem, nelem)

        allrois = []
        nrois =  len(rois)/nelem

        for i in range(nrois):
            tmp = [rois[i+j*nrois] for j in range(nelem)]
            allrois.append( tuple(tmp) )

        for i in range(nrois):
            nam = []
            lo = []
            hi = []
            for j in range(nelem):
                r = rois[i+j*nrois]
                nam.append(r[0])
                lo.append(r[1])
                hi.append(r[2])
            self.roi_names.append(nam)
            self.roi_llim.append(lo)
            self.roi_hlim.append(hi)

        roi_template ="""ROI_%i_LEFT:   %i %i %i %i
ROI_%i_RIGHT:  %i %i %i %i
ROI_%i_LABEL:  %s & %s & %s & %s & """

        rout = []
        for i in range(nrois):
            vals = [i] + self.roi_llim[i] + [i] + self.roi_hlim[i] + [i] + self.roi_names[i]
            rout.append(roi_template % tuple(vals))

        xrf_header= """VERSION:    3.1
ELEMENTS:              %i
DATE:       %s
CHANNELS:           %i
ROIS:        %i %i %i %i
REAL_TIME:   1.0 1.0 1.0 1.0
LIVE_TIME:   1.0 1.0 1.0 1.0
CAL_OFFSET:  %15.8e %15.8e %15.8e %15.8e
CAL_SLOPE:   %15.8e %15.8e %15.8e %15.8e
CAL_QUAD:    %15.8e %15.8e %15.8e %15.8e
TWO_THETA:   10.0000000 10.0000000 10.0000000 10.0000000"""


        hout = [nelem, time.ctime(atime),n_energies, nrois, nrois, nrois, nrois]
        hout.extend( header['CAL_OFFSET'])
        hout.extend( header['CAL_SLOPE'])
        hout.extend( header['CAL_QUAD'])

        obuff ="%s\n%s" % (xrf_header % tuple(hout), '\n'.join(rout))
        rois = []
        allrois = []
        self.xrf_header = obuff

        # dir = prefix
        self.xrf_energies = []
        x_en = numpy.arange(n_energies)*1.0
        for i in range(nelem):
            off   = header['CAL_OFFSET'][i]
            slope = header['CAL_SLOPE'][i]
            quad  = header['CAL_QUAD'][i]
            self.xrf_energies.append(off + x_en * (slope + x_en * quad))

        self.xrf_energies = numpy.array(self.xrf_energies)

        self.xrf_dict = {}
        processing = True
        iyold = 1
        ix    = 0
        iy    = 0
        # lines = inpf.readlines()

        progress_save = self.progress
        self.progress = self.my_progress
        # slow part: ascii text to numpy array
        for line in inpf:# enumerate(lines):
            raw = numpy.fromstring(line[:-1],sep=' ')
            ix  = raw[0]
            iy  = raw[1]
            dat = raw[2:]

            if iy != iyold:
                iyold = iy
                if iy>1: self.PrintMessage('. ')
            self.xrf_dict['%i/%i' % (ix,iy)] = dat

        inpf.close()

        xrf_shape =  (n_xin, nelem, n_energies)
        if self.dimension == 2:
            xrf_shape =  (n_yin, n_xin, nelem, n_energies)
        # print( 'xrf_shape ', xrf_shape)
        self.xrf_data = -1*numpy.ones(xrf_shape)
        xrf_dt_factor = self.dt_factor * 1.0

        if self.dimension == 2:
            xrf_dt_factor = xrf_dt_factor.transpose((1,2,0))[:,:,:,numpy.newaxis]
            for iy in range(n_yin):
                for ix in range(n_xin):
                    key = '%i/%i' % (ix+1,iy+1)
                    if key in self.xrf_dict:
                        d = numpy.array(self.xrf_dict[key])
                        d.shape = (nelem,n_energies)
                        self.xrf_data[iy,ix,:,:] = d
        else:
            xrf_dt_factor = xrf_dt_factor.transpose((1,0))[:,:,numpy.newaxis]
            for ix in range(n_xin):
                key = '%i/%i' % (ix+1,iy)
                d = numpy.array(self.xrf_dict[key])
                d.shape = (nelem, n_energies)
                self.xrf_data[ix,:,:] = d

        self.xrf_corr = self.xrf_data * xrf_dt_factor

        # merge XRF data

        en_merge = self.xrf_energies[0]
        if self.dimension == 2:
            self.xrf_merge      = self.xrf_data[:,:,0,:]*1.0
            self.xrf_merge_corr = self.xrf_corr[:,:,0,:]*1.0
            self.PrintMessage('\n')
            for iy in range(n_yin):
                self.PrintMessage('. ')
                for ix in range(n_xin):
                    sum_r = self.xrf_merge[iy,ix,:]*1.0
                    sum_c = self.xrf_merge_corr[iy,ix,:]*1.0
                    for idet in range(1,nelem):
                        en     = self.xrf_energies[idet]
                        dat_r  = self.xrf_data[iy,ix,idet,:]
                        dat_c  = self.xrf_corr[iy,ix,idet,:]
                        sum_r += numpy.interp(en_merge, en, dat_r)
                        sum_c += numpy.interp(en_merge, en, dat_c)
                    self.xrf_merge[iy,ix,:] = sum_r
                    self.xrf_merge_corr[iy,ix,:] = sum_c

        else:
            self.xrf_merge      = self.xrf_data[:,0,:]*1.0
            self.xrf_merge_corr = self.xrf_corr[:,0,:]*1.0

            for ix in range(n_xin):
                sum_r = self.xrf_merge[ix,:]*1.0
                sum_c = self.xrf_merge_corr[ix,:]*1.0
                for idet in range(1,nelem):
                    en     = self.xrf_energies[idet]
                    dat_r  = self.xrf_data[ix,idet,:]
                    dat_c  = self.xrf_corr[ix,idet,:]
                    sum_r += numpy.interp(en_merge, en, dat_r)
                    sum_c += numpy.interp(en_merge, en, dat_c)
                self.xrf_merge[ix,:] = sum_r
                self.xrf_merge_corr[ix,:] = sum_c

        self.progress = progress_save
        inpf.close()
        self.xrf_dict = None


    def save_sums_ascii(self,fname=None, correct=True,extension='dat'):
        if fname is None:
            fname = self.path

        map = None
        correct = correct and hasattr(self,'det_corr')

        outf = _cleanfile(fname)

        fout = open("%s.%s" % (outf,extension),'w')
        fout.write("# ASCII data from  %s\n" % self.filename)
        fout.write("# x positioner %s = %s\n" % (self.xaddr,self.xdesc))
        if self.dimension==2:
            fout.write("# y positioner %s = %s\n" % (self.yaddr,self.ydesc))

        fout.write("# Dead Time Correction applied: %s\n" % correct)
        fout.write("#-----------------------------------------\n")

        labels = [self.xdesc]
        if self.dimension == 2:
            ydesc = self.ydesc
            if ydesc in ('',None): ydesc = 'Y'
            labels.append(ydesc)

        labels.extend(self.sums_names)
        labels = ["%5s" % _cleanfile(l) for l in labels]
        olabel = '        '.join(labels)
        fout.write("#  %s\n" % olabel)

        sums = self.sums
        if correct: sums = self.sums_corr


        if self.dimension ==1:
            for i,x in enumerate(self.x):
                o = ["%10.5f" % x]
                o.extend(["%12g" % s for s in sums[:,i]])
                fout.write(" %s\n" % " ".join(o) )

        else:
            for i,x in enumerate(self.x):
                for j,y in enumerate(self.y):
                    o = [" %10.5f" % x, " %10.5f" % y]
                    o.extend(["%12g" % s for s in sums[:,j,i]])
                    fout.write(" %s\n" % " ".join(o))

        fout.close()


def gsescan_group(fname, _larch=None, bad=None, **kws):
    """simple mapping of EscanData file to larch groups"""
    escan = EscanData(fname, bad=bad)
    if escan.status is not None:
        raise ValueError('Not a valid Escan Data file')

    group = Group()
    group.__name__ ='GSE Escan Data file %s' % fname
    for key, val in escan.__dict__.items():
        if not key.startswith('_'):
            setattr(group, key, val)

    group.array_labels = group.pos_desc + group.sums_names
    group.get_data = escan.get_data
    return group



GSE_header_IDE= ['# XDI/1.0  GSE/1.0',
             '# Beamline.name:  13-ID-E, GSECARS',
             '# Monochromator.name:  Si 111, LN2 Cooled',
             '# Monochromator.dspacing:  3.13477',
             '# Facility.name: APS',
             '# Facility.xray_source: 3.6 cm undulator',
             '# Detectors.i0:  20cm ion chamber, He',
             '# Detectors.ifluor:  Si SDD Vortex ME-4, XIA xMAP, 4 elements',
             '# Column.1: energy eV',
             '# Column.2: mufluor',
             '# Column.3: i0',
             '# Column.4: ifluor   (corrected for deadtime)',
             '# Column.5: ifluor_raw (not corrected) '  ]

GSE_header_BMD = ['# XDI/1.0  GSE/1.0',
             '# Beamline.name:  13-BM-D, GSECARS',
             '# Monochromator.name:  Si 111, water cooled ',
             '# Monochromator.dspacing:  3.13477',
             '# Facility.name: APS',
             '# Facility.xray_source: bending magnet',
             '# Detectors.i0:  10cm ion chamber, N2',
             '# Detectors.ifluor:  Ge SSD detector, XIA xMAP, 12 elements',
             '# Column.1: energy eV',
             '# Column.2: mufluor',
             '# Column.3: i0',
             '# Column.4: ifluor   (corrected for deadtime)',
             '# Column.5: ifluor_raw (not corrected) '    ]



def gsescan_deadtime_correct(fname, channelname, subdir='DT_Corrected',
                             bad=None, _larch=None):
    """convert GSE ESCAN fluorescence XAFS scans to dead time corrected files"""
    try:
       sg = gsescan_group(fname, bad=bad)
    except:
      print('%s is not a valid ESCAN file' % fname)
      return
    energy =  sg.x
    i0 = sg.get_data('i0')

    ix = -1
    channelname = channelname.lower()
    for ich, ch in enumerate(sg.sums_names):
        if ch.lower().startswith(channelname):
           ix = ich
           break
    if ix < 0:
        print('Cannot find Channel %s in file %s  ' % (channelname, fname))
        return

    chans = list(sg.sums_list[ix])
    chans.pop()
    chans = numpy.array(chans)
    dchans = chans - chans[0]

    fl_raw  = sg.det[chans].sum(axis=0)
    fl_corr = (sg.dt_factor[dchans] * sg.det[chans]).sum(axis=0)
    mufluor = fl_corr / i0
    sg.i0  = i0
    sg.fl_raw = fl_raw
    sg.fl_corr = fl_corr
    sg.mufluor = mufluor
    sg.energy = energy

    npts = len(energy)
    header = GSE_header_IDE[:]
    if 'BM' in sg.scan_prefix:
        header = GSE_header_BMD[:]

    i1, iref = None, None
    ncol, lref = 6, 'iref'
    labels = [l.lower() for l in sg.sums_names]
    if 'i1' in labels:
        i1 = sg.get_data('i1')
    if 'iref' in labels:
        iref = sg.get_data('iref')
    elif 'i2' in labels:
        iref = sg.get_data('i2')

    if i1 is not None:
        header.append('# Column.%i: itrans ' % ncol)
        ncol += 1
    if iref is not None:
        header.append('# Column.%i: irefer ' % ncol)
        ncol += 1
    buff = [l.strip() for l in header]
    buff.append("# Scan.start_time: %s" %
                isotime(os.stat(fname).st_ctime), with_tzone=True)

    thead = ["# ///",
             "# summed %s fluorescence data from %s" % (channelname, fname),
             "# Dead-time correction applied",
             "#---------------------------------"]

    arrlabel = "# energy     mufluor    i0    fluor_corr   fluor_raw"
    if i1 is not None:
        arrlabel = "%s  itrans"  % arrlabel

    if iref is not None:
        arrlabel = "%s  irefer"  % arrlabel

    thead.append(arrlabel)
    buff.extend(thead)
    fmt = "   %.3f   %.5f   %.1f   %.5f   %.1f"
    for i in range(npts):
        dline = fmt % (energy[i],  mufluor[i], i0[i], fl_corr[i], fl_raw[i])
        if i1 is not None:
            dline = "%s  %.1f" % (dline, i1[i])
        if iref is not None:
            dline = "%s  %.1f" % (dline, iref[i])
        buff.append(dline)

    ofile = fname[:]
    if ofile.startswith('..'):
        ofile = ofile[3:]
    ofile = ofile.replace('.', '_') + '.dat'
    ofile = os.path.join(subdir, ofile)
    if not os.path.exists(subdir):
        os.mkdir(subdir)
    try:
       fout = open(ofile, 'w')
       fout.write("\n".join(buff))
       fout.close()
       print("wrote %s, npts=%i, channel='%s'" % (ofile, npts, channelname))
    except:
       print("could not open / write to output file %s" % ofile)

    return sg
