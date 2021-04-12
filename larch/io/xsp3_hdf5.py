#!/usr/bin/python
"""
support for netcdf file output files containing MCA spectra
from Epics Mapping Mode with XIA xMXAP electronics
"""
import numpy as np
import time
import h5py
import sys
import os

from .. import Group

# Default tau values for xspress3

## XSPRESS3_TAUS = [109.e-9, 91.e-9, 99.e-9, 98.e-9]
XSPRESS3_TAUS = [100.e-9, 100.e-9, 100.e-9, 100.e-9]

def estimate_icr(ocr, tau, niter=3):
    "estimate icr from ocr and tau"
    maxicr = 1.0/tau
    maxocr = 1/(tau*np.exp(1.0))
    ocr[np.where(ocr>2*maxocr)[0]] = 2*maxocr
    icr = 1.0*ocr
    for c in range(niter):
        delta = (icr - ocr*np.exp(icr*tau))/(icr*tau - 1)
        delta[np.where(delta < 0)[0]] = 0.0
        icr = icr + delta
        icr[np.where(icr>5*maxicr)[0]] = 5*maxicr
    #endfor
    return icr
#enddef


class XSP3Data(object):
    def __init__(self, npix, ndet, nchan):
        self.firstPixel   = 0
        self.numPixels    = 0
        self.realTime     = np.zeros((npix, ndet), dtype='f8')
        self.liveTime     = np.zeros((npix, ndet), dtype='f8')
        self.outputCounts = np.zeros((npix, ndet), dtype='f8')
        self.inputCounts  = np.zeros((npix, ndet), dtype='f8')
        # self.counts       = np.zeros((npix, ndet, nchan), dtype='f4')

def get_counts_carefully(h5link):
    """
    get counts array with some error checking for corrupted files,
    especially those that give
       'OSError: Can't read data (inflate() failed)'
    because one data point is bad.

    This seems to be a common enough failure mode that this function looks
    for such points and replaces offending points by the average of the
    neighboring points
    """
    # will usually succeed, of course.
    try:
        return h5link[:]
    except OSError:
        pass

    # find bad point
    npts = h5link.shape[0]
    ilo, ihi = 0, npts
    imid = (ihi-ilo)//2
    while (ihi-ilo) > 1:
        try:
            _tmp = h5link[ilo:imid]
            ilo, imid = imid, ihi
        except OSError:
            ihi, imid = imid, (imid+ilo)//2

    # retest to make sure there is one bad point
    for i in range(ilo, ihi):
        try:
            _tmp = h5link[i]
        except OSError:
            ibad = i
            break

    # its not unusual to have two bad points in a row:
    p1bad = m1bad = False
    try:
        _tmp = h5link[i+1]
    except OSError:
        p1bad = True
    try:
        _tmp = h5link[i-1]
    except OSError:
        m1bad = True

    if  m1bad:
        ibad = ibad - 1
        p1bad = True

    counts = np.zeros(h5link.shape, dtype=h5link.dtype)
    counts[:ibad] = h5link[:ibad]
    counts[ibad+2:] = h5link[ibad+2:]
    if p1bad: # two in a row
        print("fixing 2 bad points in h5 file")
        counts[ibad]   = h5link[ibad-1]
        counts[ibad+1] = h5link[ibad+2]
    else:
        print("fixing bad point in h5 file")
        counts[ibad+1] = h5link[ibad+1]
        if ibad == 0:
            counts[ibad] = counts[ibad+1]
        elif ibad == npts - 1:
            counts[ibad] = counts[ibad-1]
        else:
            counts[ibad] = ((counts[ibad-1]+counts[ibad+1])/2.0).astype(h5link.dtype)
    return counts


def read_xsp3_hdf5(fname, npixels=None, verbose=False,
                   estimate_dtc=False, _larch=None):
    # Reads a HDF5 file created with the DXP xMAP driver
    # with the netCDF plugin buffers
    npixels = None

    clockrate = 12.5e-3   # microseconds per clock tick: 80MHz clock
    t0 = time.time()
    h5file = h5py.File(fname, 'r')

    root  = h5file['entry/instrument']
    counts = get_counts_carefully(root['detector/data'])

    # support bother newer and earlier location of NDAttributes
    ndattr = None
    try:
        ndattr = root['NDAttributes']
    except KeyError:
        pass

    if 'CHAN1SCA0' not in ndattr:
        try:
            ndattr = root['detector/NDAttributes']
        except KeyError:
            pass
    if 'CHAN1SCA0' not in ndattr:
        raise ValueError("cannot find NDAttributes for '%s'" % fname)

    # note: sometimes counts has npix-1 pixels, while the time arrays
    # really have npix...  So we take npix from the time array, and
    npix = ndattr['CHAN1SCA0'].shape[0]
    ndpix, ndet, nchan = counts.shape
    if npixels is None:
        npixels = npix
        if npixels < ndpix:
            ndpix = npixels

    out = XSP3Data(npixels, ndet, nchan)
    out.numPixels = npixels
    t1 = time.time()

    if ndpix < npix:
        out.counts = np.zeros((npix, ndet, nchan), dtype='f8')
        out.counts[:ndpix, :, :]  = counts
    else:
        out.counts = counts

    if estimate_dtc:
        dtc_taus = XSPRESS3_TAUS
        if _larch is not None and _larch.symtable.has_symbol('_sys.gsecars.xspress3_taus'):
            dtc_taus = _larch.symtable._sys.gsecars.xspress3_taus

    for i in range(ndet):
        chan = "CHAN%i" %(i+1)
        clock_ticks = ndattr['%sSCA0' % chan][()]
        reset_ticks = ndattr["%sSCA1" % chan][()]
        all_events  = ndattr["%sSCA3" % chan][()]
        if "%sEventWidth" in ndattr:
            event_width = 1.0 + ndattr['%sEventWidth' % chan][()]
        else:
            event_width = 6.0

        clock_ticks[np.where(clock_ticks<10)] = 10.0
        rtime = clockrate * clock_ticks
        out.realTime[:, i] = rtime
        out.liveTime[:, i] = rtime
        ocounts = out.counts[:, i, 1:-1].sum(axis=1)
        ocounts[np.where(ocounts<0.1)] = 0.1
        out.outputCounts[:, i] = ocounts

        denom = clock_ticks - (all_events*event_width + reset_ticks)
        denom[np.where(denom<2.0)] = 1.0
        dtfactor = clock_ticks/denom
        out.inputCounts[:, i] = dtfactor * ocounts

        if estimate_dtc:
            ocr = ocounts/(rtime*1.e-6)
            icr = estimate_icr(ocr, dtc_taus[i], niter=3)
            out.inputCounts[:, i] = icr * (rtime*1.e-6)

    h5file.close()
    t2 = time.time()
    if verbose:
        print('   time to read file    = %5.1f ms' % ((t1-t0)*1000))
        print('   time to extract data = %5.1f ms' % ((t2-t1)*1000))
        print('   read %i pixels ' %  npixels)
        print('   data shape:    ' ,  out.counts.shape)
    return out

def test_read(fname):
    print( fname,  os.stat(fname))
    fd = read_xsp3_hdf5(fname, verbose=True)
    print(fd.counts.shape)
