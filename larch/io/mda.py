#!/usr/bin/env python
# adopted with few changes from Tim Mooney's mda.py

# version 2.1 Tim Mooney 2/15/2012
# merge of mda.py and mda_f.py
# - supports reading, writing, and arithmetic operations for
#   up to 4-dimensional MDA files.

from __future__ import print_function

__version__ = '2.1'

import sys
import os
import string

import numpy


have_fast_xdr = False
try:
    import f_xdrlib as xdr
    have_fast_xdr = True
except:
    import xdrlib as xdr

try:
    import Tkinter
    have_Tkinter = True
except:
    have_Tkinter = False
#     try:
#         import wx
#         have_wx = True
#     except:
#         have_wx = False

if have_Tkinter:
    import tkFileDialog

# If we can import numpy, and if caller asks us to use it, we'll
# return data in numpy arrays.  Otherwise, we'll return data in lists.

import copy

################################################################################
# classes
# scanDim holds all of the data associated with a single execution of a single sscan record.
class scanDim:
    def __init__(self):
        self.rank = 0            # [1..n]  1 means this is the "innermost" or only scan dimension
        self.dim = 0            # dimensionality of data (numerically same as rank)
        self.npts = 0            # number of data points planned
        self.curr_pt = 0        # number of data points actually acquired
        self.plower_scans = 0    # file offsets of next lower rank scans
        self.name = ""            # name of sscan record that acquired the data
        self.time = ""            # time at which scan (dimension) started
        self.np = 0                # number of positioners
        self.p = []                # list of scanPositioner instances
        self.nd = 0                # number of detectors
        self.d = []                # list of scanDetector instances
        self.nt = 0                # number of detector triggers
        self.t = []                # list of scanTrigger instances

    def __str__(self):
        if self.name != '':
            s = "%dD data from \"%s\" acquired on %s:\n%d/%d pts; %d positioners, %d detectors" % (
                self.dim, self.name, self.time, self.curr_pt, self.npts, self.np, self.nd)
        else:
            s = "%dD data (not read in)" % (self.dim)

        return s

# scanPositioner holds all the information associated with a single positioner, and
# all the data written and acquired by that positioner during an entire (possibly
# multidimensional) scan.
class scanPositioner:
    def __init__(self):
        self.number = 0                # positioner number in sscan record
        self.fieldName = ""            # name of sscanRecord PV
        self.name = ""                # name of EPICS PV this positioner wrote to
        self.desc = ""                # description of 'name' PV
        self.step_mode = ""            # 'LINEAR', 'TABLE', or 'FLY'
        self.unit = ""                # units of 'name' PV
        self.readback_name = ""        # name of EPICS PV this positioner read from, if any
        self.readback_desc = ""        # description of 'readback_name' PV
        self.readback_unit = ""        # units of 'readback_name' PV
        self.data = []                # list of values written to 'name' PV.  If rank==2, lists of lists, etc.

    def __str__(self):
        data = self.data

        n = data.ndim
        if n==1:
            dimString = '(' + str(data.shape[0]) + ')'
        else:
            dimString = str(data.shape)

        s = "positioner <scanRecord>.%s\nPV name  '%s'\nPV desc. '%s'\nPV units    '%s'\nstep mode: %s\nRB name  '%s'\nRB desc. '%s'\nRB units    '%s'\ndata: %dD array %s\n" % (self.fieldName,
        self.name, self.desc, self.unit, self.step_mode, self.name, self.desc, self.unit, n, dimString)
        return s

# scanDetector holds all the information associated with a single detector, and
# all the data acquired by that detector during an entire (possibly multidimensional) scan.
class scanDetector:
    def __init__(self):
        self.number = 0            # detector number in sscan record
        self.fieldName = ""        # name of sscanRecord PV
        self.name = ""            # name of EPICS PV this detector read from
        self.desc = ""            # description of 'name' PV
        self.unit = ""            # units of 'name' PV
        self.data = []            # list of values read from 'name' PV.  If rank==2, lists of lists, etc.

    def __str__(self):
        data = self.data
        n = data.ndim
        if n==1:
            dimString = '(' + str(data.shape[0]) + ')'
        else:
            dimString = str(data.shape)
        s = "detector <scanRecord>.%s\nPV name  '%s'\nPV desc. '%s'\nPV units    '%s'\ndata: %dD array %s\n" % (self.fieldName,
        self.name, self.desc, self.unit, n, dimString)
        return s

# scanTrigger holds all the information associated with a single detector trigger.
class scanTrigger:
    def __init__(self):
        self.number = 0            # detector-trigger number in sscan record
        self.name = ""            # name of sscanRecord PV
        self.command = 0.0        # value written to 'name' PV

    def __str__(self):
        s = "trigger %d (%s), command=%f\n" % (self.number,
            self.name, self.command)
        return s

# scanBuf is a private data structure used to assemble data that will be written to an MDA file.
class scanBuf:
    def __init__(self):
        self.npts = 0
        self.offset = 0
        self.bufLen = 0
        self.preamble = None
        self.pLowerScans = []
        self.pLowerScansBuf = ""
        self.postamble = None
        self.data = None
        self.inner = []    # inner scans, if any

# mdaBuf is a private data structure used to assemble data that will be written to an MDA file.
class mdaBuf:
    def __init__(self):
        self.header = None
        self.pExtra = None    # file offset to extraPV section
        self.scan = None
        self.extraPV = None    # extraPV section

################################################################################
# read MDA file

# Given a detector number, return the name of the associated sscanRecord PV, 'D01'-'D99'.
# (Currently, only 70 detectors are ever used.)
def detName(i):
    if i < 100:
        return "D%02d"%(i+1)
    else:
        return "?"

# Given a detector number, return the name of the associated sscanRecord PV, for the
# old sscanRecord, which had only 15 detectors 'D1'-'DF'.
def oldDetName(i):
    if i < 15:
        return string.upper("D%s"%(hex(i+1)[2]))
    elif i < 85:
        return "D%02d"%(i-14)
    else:
        return "?"

# Given a positioner number, , return the name of the associated sscanRecord PV, "P1'-'P4'
def posName(i):
    if i < 4:
        return "P%d" % (i+1)
    else:
        return "?"

def verboseData(data, out=sys.stdout):
    if ((len(data)>0) and (type(data[0]) == type([]))):
        for i in len(data):
            verboseData(data[i], out)
    else:
        out.write("[")
        for datum in data:
            if (type(datum) == type(0)):
                out.write(" %d" % datum)
            else:
                out.write(" %.5f" % datum)
        out.write(" ]\n")

def readScan(scanFile, verbose=0, out=sys.stdout, unpacker=None):
    """usage: (scan,num) = readScan(scanFile, verbose=0, out=sys.stdout)"""

    scan = scanDim()    # data structure to hold scan info and data
    buf = scanFile.read(10000) # enough to read scan header
    if unpacker == None:
        u = xdr.Unpacker(buf)
    else:
        u = unpacker
        u.reset(buf)

    scan.rank = u.unpack_int()
    if (scan.rank > 20) or (scan.rank < 0):
        print("* * * readScan('%s'): rank > 20.  probably a corrupt file" % scanFile.name)
        return None

    scan.npts = u.unpack_int()
    scan.curr_pt = u.unpack_int()
    if verbose:
        print("scan.rank = ", scan.rank)
        print("scan.npts = ", scan.npts)
        print("scan.curr_pt = ", scan.curr_pt)

    if (scan.rank > 1):
        # if curr_pt < npts, plower_scans will have garbage for pointers to
        # scans that were planned for but not written
        if have_fast_xdr:
            scan.plower_scans = u.unpack_farray_int(scan.npts)
        else:
            scan.plower_scans = u.unpack_farray(scan.npts, u.unpack_int)
        if verbose:
                        print("scan.plower_scans = ", scan.plower_scans)
    namelength = u.unpack_int()
    scan.name = u.unpack_string()
    if verbose:
                print("scan.name = ", scan.name)
    timelength = u.unpack_int()
    scan.time = u.unpack_string()
    if verbose:
                print("scan.time = ", scan.time)
    scan.np = u.unpack_int()
    if verbose:
                print("scan.np = ", scan.np)
    scan.nd = u.unpack_int()
    if verbose:
                print("scan.nd = ", scan.nd)
    scan.nt = u.unpack_int()
    if verbose:
                print("scan.nt = ", scan.nt)
    for j in range(scan.np):
        scan.p.append(scanPositioner())
        scan.p[j].number = u.unpack_int()
        scan.p[j].fieldName = posName(scan.p[j].number)
        if verbose:
                        print("positioner ", j)
        length = u.unpack_int() # length of name string
        if length:
                        scan.p[j].name = u.unpack_string()
        if verbose:
                        print("scan.p[%d].name = %s" % (j, scan.p[j].name))
        length = u.unpack_int() # length of desc string
        if length:
                        scan.p[j].desc = u.unpack_string()
        if verbose:
                        print("scan.p[%d].desc = %s" % (j, scan.p[j].desc))
        length = u.unpack_int() # length of step_mode string
        if length:
                        scan.p[j].step_mode = u.unpack_string()
        if verbose:
                        print("scan.p[%d].step_mode = %s" % (j, scan.p[j].step_mode))
        length = u.unpack_int() # length of unit string
        if length:
                        scan.p[j].unit = u.unpack_string()
        if verbose:
                        print("scan.p[%d].unit = %s" % (j, scan.p[j].unit))
        length = u.unpack_int() # length of readback_name string
        if length:
                        scan.p[j].readback_name = u.unpack_string()
        if verbose:
                        print("scan.p[%d].readback_name = %s" % (j, scan.p[j].readback_name))
        length = u.unpack_int() # length of readback_desc string
        if length:
                        scan.p[j].readback_desc = u.unpack_string()
        if verbose:
                        print("scan.p[%d].readback_desc = %s" % (j, scan.p[j].readback_desc))
        length = u.unpack_int() # length of readback_unit string
        if length:
                        scan.p[j].readback_unit = u.unpack_string()
        if verbose:
                        print("scan.p[%d].readback_unit = %s" % (j, scan.p[j].readback_unit))

    file_loc_det = scanFile.tell() - (len(buf) - u.get_position())

    for j in range(scan.nd):
        scan.d.append(scanDetector())
        scan.d[j].number = u.unpack_int()
        scan.d[j].fieldName = detName(scan.d[j].number)
        if verbose:
                        print("detector ", j)
        length = u.unpack_int() # length of name string
        if length:
                        scan.d[j].name = u.unpack_string()
        if verbose:
                        print("scan.d[%d].name = %s" % (j, scan.d[j].name))
        length = u.unpack_int() # length of desc string
        if length:
                        scan.d[j].desc = u.unpack_string()
        if verbose:
                        print("scan.d[%d].desc = %s" % (j, scan.d[j].desc))
        length = u.unpack_int() # length of unit string
        if length:
                        scan.d[j].unit = u.unpack_string()
        if verbose:
                        print("scan.d[%d].unit = %s" % (j, scan.d[j].unit))

    for j in range(scan.nt):
        scan.t.append(scanTrigger())
        scan.t[j].number = u.unpack_int()
        if verbose:
                        print("trigger ", j)
        length = u.unpack_int() # length of name string
        if length:
                        scan.t[j].name = u.unpack_string()
        if verbose:
                        print("scan.t[%d].name = %s" % (j, scan.t[j].name))
        scan.t[j].command = u.unpack_float()
        if verbose:
                        print("scan.t[%d].command = %s" % (j, scan.t[j].command))

    ### read data
    # positioners
    file_loc_data = scanFile.tell() - (len(buf) - u.get_position())
    scanFile.seek(file_loc_data)
    buf = scanFile.read(scan.npts * (scan.np * 8 + scan.nd *4))
    u.reset(buf)

    if have_fast_xdr:
        data = u.unpack_farray_double(scan.npts*scan.np)
    else:
        data = u.unpack_farray(scan.npts*scan.np, u.unpack_double)
    start = 0
    end = scan.npts
    for j in range(scan.np):
        start = j*scan.npts
        scan.p[j].data = data[start:end]
        start = end
        end += scan.npts

    # detectors
    if have_fast_xdr:
        data = u.unpack_farray_float(scan.npts*scan.nd)
    else:
        data = u.unpack_farray(scan.npts*scan.nd, u.unpack_float)
    start = 0
    end = scan.npts
    for j in range(scan.nd):
        scan.d[j].data = data[start:end]
        start = end
        end += scan.npts

    return (scan, (file_loc_data-file_loc_det))

useDetToDatOffset = 1
def readScanQuick(scanFile, unpacker=None, detToDat_offset=None):
    """usage: readScanQuick(scanFile, unpacker=None)"""

    scan = scanDim()    # data structure to hold scan info and data
    buf = scanFile.read(10000) # enough to read scan header
    if unpacker == None:
        u = xdr.Unpacker(buf)
    else:
        u = unpacker
        u.reset(buf)

    scan.rank = u.unpack_int()
    if (scan.rank > 20) or (scan.rank < 0):
        print("* * * readScanQuick('%s'): rank > 20.  probably a corrupt file" % scanFile.name)
        return None

    scan.npts = u.unpack_int()
    scan.curr_pt = u.unpack_int()

    if (scan.rank > 1):
        if have_fast_xdr:
            scan.plower_scans = u.unpack_farray_int(scan.npts)
        else:
            scan.plower_scans = u.unpack_farray(scan.npts, u.unpack_int)

    namelength = u.unpack_int()
    scan.name = u.unpack_string()
    timelength = u.unpack_int()
    scan.time = u.unpack_string()

    scan.np = u.unpack_int()
    scan.nd = u.unpack_int()
    scan.nt = u.unpack_int()

    for j in range(scan.np):
        scan.p.append(scanPositioner())
        scan.p[j].number = u.unpack_int()
        n = u.unpack_int() # length of name string
        if n: u.set_position(u.get_position()+4+(n+3)//4*4)
        n = u.unpack_int() # length of desc string
        if n: u.set_position(u.get_position()+4+(n+3)//4*4)
        n = u.unpack_int() # length of step_mode string
        if n: u.set_position(u.get_position()+4+(n+3)//4*4)
        n = u.unpack_int() # length of unit string
        if n: u.set_position(u.get_position()+4+(n+3)//4*4)
        n = u.unpack_int() # length of readback_name string
        if n: u.set_position(u.get_position()+4+(n+3)//4*4)
        n = u.unpack_int() # length of readback_desc string
        if n: u.set_position(u.get_position()+4+(n+3)//4*4)
        n = u.unpack_int() # length of readback_unit string
        if n: u.set_position(u.get_position()+4+(n+3)//4*4)

    file_loc_det = scanFile.tell() - (len(buf) - u.get_position())

    if (detToDat_offset == None) or (not useDetToDatOffset):
        for j in range(scan.nd):
            scan.d.append(scanDetector())
            scan.d[j].number = u.unpack_int()
            scan.d[j].fieldName = detName(scan.d[j].number)
            n = u.unpack_int() # length of name string
            if n: u.set_position(u.get_position()+4+(n+3)//4*4)
            n = u.unpack_int() # length of desc string
            if n: u.set_position(u.get_position()+4+(n+3)//4*4)
            n = u.unpack_int() # length of unit string
            if n: u.set_position(u.get_position()+4+(n+3)//4*4)

        for j in range(scan.nt):
            scan.t.append(scanTrigger())
            scan.t[j].number = u.unpack_int()
            n = u.unpack_int() # length of name string
            if n: u.set_position(u.get_position()+4+(n+3)//4*4)
            scan.t[j].command = u.unpack_float()

        ### read data
        # positioners

        file_loc = scanFile.tell() - (len(buf) - u.get_position())
        diff = file_loc - (file_loc_det + detToDat_offset)
        if diff != 0:
            print("oldSeek, newSeek, o-n=", file_loc, file_loc_det + detToDat_offset, diff)
        scanFile.seek(file_loc)
    else:
        for j in range(scan.nd):
            scan.d.append(scanDetector())
        scanFile.seek(file_loc_det + detToDat_offset)

    buf = scanFile.read(scan.npts * (scan.np * 8 + scan.nd *4))
    u.reset(buf)

    if have_fast_xdr:
        data = u.unpack_farray_double(scan.npts*scan.np)
    else:
        data = u.unpack_farray(scan.npts*scan.np, u.unpack_double)
    for j in range(scan.np):
        start = j*scan.npts
        scan.p[j].data = data[j*scan.npts : (j+1)*scan.npts]

    # detectors
    if have_fast_xdr:
        data = u.unpack_farray_float(scan.npts*scan.nd)
    else:
        data = u.unpack_farray(scan.npts*scan.nd, u.unpack_float)
    for j in range(scan.nd):
        scan.d[j].data = data[j*scan.npts : (j+1)*scan.npts]

    return scan

EPICS_types_dict = {
0: "DBR_STRING",
1: "DBR_SHORT",
2: "DBR_FLOAT",
3: "DBR_ENUM",
4: "DBR_CHAR",
5: "DBR_LONG",
6: "DBR_DOUBLE",
7: "DBR_STS_STRING",
8: "DBR_STS_SHORT",
9: "DBR_STS_FLOAT",
10: "DBR_STS_ENUM",
11: "DBR_STS_CHAR",
12: "DBR_STS_LONG",
13: "DBR_STS_DOUBLE",
14: "DBR_TIME_STRING",
15: "DBR_TIME_SHORT",
16: "DBR_TIME_FLOAT",
17: "DBR_TIME_ENUM",
18: "DBR_TIME_CHAR",
19: "DBR_TIME_LONG",
20: "DBR_TIME_DOUBLE",
21: "DBR_GR_STRING",
22: "DBR_GR_SHORT",
23: "DBR_GR_FLOAT",
24: "DBR_GR_ENUM",
25: "DBR_GR_CHAR",
26: "DBR_GR_LONG",
27: "DBR_GR_DOUBLE",
28: "DBR_CTRL_STRING",
29: "DBR_CTRL_SHORT",
30: "DBR_CTRL_FLOAT",
31: "DBR_CTRL_ENUM",
32: "DBR_CTRL_CHAR",
33: "DBR_CTRL_LONG",
34: "DBR_CTRL_DOUBLE"
}

def EPICS_types(n):
    if EPICS_types_dict.has_key(n):
        return EPICS_types_dict[n]
    else:
        return ("Unexpected type %d" % n)

def readMDA(fname=None, maxdim=4, verbose=0, showHelp=0, outFile=None, useNumpy=None, readQuick=False):
    """usage readMDA(fname=None, maxdim=4, verbose=0, showHelp=0, outFile=None, readQuick=False)"""


    dim = []
    if fname is None:
        if have_Tkinter:
            fname = tkFileDialog.Open().show()
        else:
            print("No file specified, and no file dialog could be opened")
            return None
    if (not os.path.isfile(fname)):
        if (not fname.endswith('.mda')):
            fname = fname + '.mda'
        if (not os.path.isfile(fname)):
            print(fname, "not found")
            return None

    if (outFile == None):
        out = sys.stdout
    else:
        out = open(outFile, 'w')

    scanFile = open(fname, 'rb')
    if verbose: out.write("verbose=%d output for MDA file '%s'\n" % (verbose, fname))
    buf = scanFile.read(100)        # to read header for scan of up to 5 dimensions
    u = xdr.Unpacker(buf)

    # read file header
    version = u.unpack_float()
    if verbose: out.write("MDA version = %.3f\n" % version)
    if abs(version - 1.3) > .01:
        print("I can't read MDA version %f.  Is this really an MDA file?" % version)
        return None

    scan_number = u.unpack_int()
    if verbose: out.write("scan_number = %d\n" % scan_number)
    rank = u.unpack_int()
    if verbose: out.write("rank = %d\n" % rank)
    dimensions = u.unpack_farray(rank, u.unpack_int)
    if verbose:
        out.write("dimensions = ")
        verboseData(dimensions, out)
    isRegular = u.unpack_int()
    if verbose: out.write("isRegular = %d\n" % isRegular)
    pExtra = u.unpack_int()
    if verbose: out.write("pExtra = %d (0x%x)\n" % (pExtra, pExtra))
    pmain_scan = scanFile.tell() - (len(buf) - u.get_position())

    # collect 1D data
    scanFile.seek(pmain_scan)
    (s,n) = readScan(scanFile, max(0,verbose-1), out, unpacker=u)
    dim.append(s)
    dim[0].dim = 1

    for p in dim[0].p:
        p.data = numpy.array(p.data)
    for d in dim[0].d:
        d.data = numpy.array(d.data)

    if ((rank > 1) and (maxdim > 1)):
        # collect 2D data
        for i in range(dim[0].curr_pt):
            scanFile.seek(dim[0].plower_scans[i])
            if (i==0):
                (s,detToDat) = readScan(scanFile, max(0,verbose-1), out, unpacker=u)
                dim.append(s)
                dim[1].dim = 2
                # replace data arrays [1,2,3] with [[1,2,3]]
                for j in range(dim[1].np):
                    dim[1].p[j].data = [dim[1].p[j].data]
                for j in range(dim[1].nd):
                    dim[1].d[j].data = [dim[1].d[j].data]
            else:
                if readQuick:
                    s = readScanQuick(scanFile, unpacker=u, detToDat_offset=detToDat)
                else:
                    (s,junk) = readScan(scanFile, max(0,verbose-1), out, unpacker=u)
                # append data arrays
                # [ [1,2,3], [2,3,4] ] -> [ [1,2,3], [2,3,4], [3,4,5] ]
                numP = min(s.np, len(dim[1].p))
                if (s.np > numP):
                    print("First scan had %d positioners; This one only has %d." % (s.np, numP))
                for j in range(numP):
                                        dim[1].p[j].data.append(s.p[j].data)
                numD = min(s.nd, len(dim[1].d))
                if (s.nd > numD):
                    print("First scan had %d detectors; This one only has %d." % (s.nd, numD))
                for j in range(numD): dim[1].d[j].data.append(s.d[j].data)

        for p in dim[1].p:
            p.data = numpy.array(p.data)
        for d in dim[1].d:
            d.data = numpy.array(d.data)

    if ((rank > 2) and (maxdim > 2)):
        # collect 3D data
        #print("dim[0].curr_pt=",dim[0].curr_pt)
        for i in range(dim[0].curr_pt):
            #print("i=%d of %d points" % (i, dim[0].curr_pt))
            scanFile.seek(dim[0].plower_scans[i])
            (s1,detToDat) = readScan(scanFile, max(0,verbose-1), out, unpacker=u)
            #print("s1.curr_pt=", s1.curr_pt)
            for j in range(s1.curr_pt):
                #print("j=%d of %d points" % (j, s1.curr_pt))
                scanFile.seek(s1.plower_scans[j])
                if (j==0) or not readQuick:
                    (s, detToDat) = readScan(scanFile, max(0,verbose-1), out, unpacker=u)
                else:
                    s = readScanQuick(scanFile, unpacker=u, detToDat_offset=detToDat)
                if ((i == 0) and (j == 0)):
                    dim.append(s)
                    dim[2].dim = 3
                    # replace data arrays [1,2,3] with [[[1,2,3]]]
                    for k in range(dim[2].np):
                        dim[2].p[k].data = [[dim[2].p[k].data]]
                    for k in range(dim[2].nd):
                        dim[2].d[k].data = [[dim[2].d[k].data]]
                else:
                    # append data arrays
                    numP = min(s.np, len(dim[2].p))
                    if (s.np > numP):
                        print("First scan had %d positioners; This one only has %d." % (s.np, numP))
                    for k in range(numP):
                        if j==0: dim[2].p[k].data.append([])
                        dim[2].p[k].data[i].append(s.p[k].data)
                    numD = min(s.nd, len(dim[2].d))
                    if (s.nd > numD):
                        print("First scan had %d detectors; This one only has %d." % (s.nd, numD))
                    for k in range(numD):
                        if j==0: dim[2].d[k].data.append([])
                        dim[2].d[k].data[i].append(s.d[k].data)

        for p in dim[2].p:
            p.data = numpy.array(p.data)
        for d in dim[2].d:
            d.data = numpy.array(d.data)

    if ((rank > 3) and (maxdim > 3)):
        # collect 4D data
        for i in range(dim[0].curr_pt):
            scanFile.seek(dim[0].plower_scans[i])
            (s1, detToDat) = readScan(scanFile, max(0,verbose-1), out, unpacker=u)
            for j in range(s1.curr_pt):
                scanFile.seek(s1.plower_scans[j])
                (s2, detToDat) = readScan(scanFile, max(0,verbose-1), out, unpacker=u)
                for k in range(s2.curr_pt):
                    scanFile.seek(s2.plower_scans[k])
                    if (k==0) or not readQuick:
                        (s, detToDat) = readScan(scanFile, max(0,verbose-1), out, unpacker=u)
                    else:
                        s = readScanQuick(scanFile, unpacker=u, detToDat_offset=detToDat)
                    if ((i == 0) and (j == 0) and (k == 0)):
                        dim.append(s)
                        dim[3].dim = 4
                        for m in range(dim[3].np):
                            dim[3].p[m].data = [[[dim[3].p[m].data]]]
                        for m in range(dim[3].nd):
                            dim[3].d[m].data = [[[dim[3].d[m].data]]]
                    else:
                        # append data arrays
                        if j==0 and k==0:
                            for m in range(dim[3].np):
                                dim[3].p[m].data.append([[]])
                                dim[3].p[m].data[i][0].append(s.p[m].data)
                            for m in range(dim[3].nd):
                                dim[3].d[m].data.append([[]])
                                dim[3].d[m].data[i][0].append(s.d[m].data)
                        else:
                            for m in range(dim[3].np):
                                if k==0: dim[3].p[m].data[i].append([])
                                dim[3].p[m].data[i][j].append(s.p[m].data)
                            for m in range(dim[3].nd):
                                if k==0: dim[3].d[m].data[i].append([])
                                dim[3].d[m].data[i][j].append(s.d[m].data)

        for p in dim[3].p:
            p.data = numpy.array(p.data)
        for d in dim[3].d:
            d.data = numpy.array(d.data)



    # Collect scan-environment variables into a dictionary
    dict = {}
    dict['sampleEntry'] = ("description", "unit string", "value", "EPICS_type", "count")
    dict['filename'] = fname
    dict['version'] = version
    dict['scan_number'] = scan_number
    dict['rank'] = rank
    dict['dimensions'] = dimensions
    acq_dimensions = []
    for d in dim:
        acq_dimensions.append(d.curr_pt)
    dict['acquired_dimensions'] = acq_dimensions
    dict['isRegular'] = isRegular
    dict['ourKeys'] = ['sampleEntry', 'filename', 'version', 'scan_number', 'rank', 'dimensions', 'acquired_dimensions', 'isRegular', 'ourKeys']
    if pExtra:
        scanFile.seek(pExtra)
        buf = scanFile.read()       # Read all scan-environment data
        u.reset(buf)
        numExtra = u.unpack_int()
        if verbose: out.write("\nnumber of 'Extra' PV's = %d\n" % numExtra)
        for i in range(numExtra):
            if verbose: out.write("env PV #%d -------\n" % (i))
            name = ''
            n = u.unpack_int()      # length of name string
            if n: name = u.unpack_string()
            if verbose: out.write("\tname = '%s'\n" % name)
            desc = ''
            n = u.unpack_int()      # length of desc string
            if n: desc = u.unpack_string()
            if verbose: out.write("\tdesc = '%s'\n" % desc)
            EPICS_type = u.unpack_int()
            if verbose: out.write("\tEPICS_type = %d (%s)\n" % (EPICS_type, EPICS_types(EPICS_type)))

            unit = ''
            value = ''
            count = 0
            if EPICS_type != 0:   # not DBR_STRING; array is permitted
                count = u.unpack_int()  #
                if verbose: out.write("\tcount = %d\n" % count)
                n = u.unpack_int()      # length of unit string
                if n: unit = u.unpack_string()
                if verbose: out.write("\tunit = '%s'\n" % unit)

            if EPICS_type == 0: # DBR_STRING
                n = u.unpack_int()      # length of value string
                if n: value = u.unpack_string()
            elif EPICS_type == 32: # DBR_CTRL_CHAR
                #value = u.unpack_fstring(count)
                vect = u.unpack_farray(count, u.unpack_int)
                value = ""
                for i in range(len(vect)):
                    # treat the byte array as a null-terminated string
                    if vect[i] == 0: break
                    value = value + chr(vect[i])
            elif EPICS_type == 29: # DBR_CTRL_SHORT
                value = u.unpack_farray(count, u.unpack_int)
            elif EPICS_type == 33: # DBR_CTRL_LONG
                value = u.unpack_farray(count, u.unpack_int)
            elif EPICS_type == 30: # DBR_CTRL_FLOAT
                value = u.unpack_farray(count, u.unpack_float)
            elif EPICS_type == 34: # DBR_CTRL_DOUBLE
                value = u.unpack_farray(count, u.unpack_double)
            if verbose:
                if (EPICS_type == 0):
                    out.write("\tvalue = '%s'\n" % (value))
                else:
                    out.write("\tvalue = ")
                    verboseData(value, out)

            dict[name] = (desc, unit, value, EPICS_type, count)
    scanFile.close()

    dim.reverse()
    dim.append(dict)
    dim.reverse()
    if verbose or showHelp:
        print("\n%s is a %d-D file; %d dimensions read in." % (fname, dim[0]['rank'], len(dim)-1))
        print("dim[0] = dictionary of %d scan-environment PVs" % (len(dim[0])))
        print("   usage: dim[0]['sampleEntry'] ->", dim[0]['sampleEntry'])
        for i in range(1,len(dim)):
            print("dim[%d] = %s" % (i, str(dim[i])))
        print("   usage: dim[1].p[2].data -> 1D array of positioner 2 data")
        print("   usage: dim[2].d[7].data -> 2D array of detector 7 data")

    if showHelp:
        print(" ")
        print("   each scan dimension (i.e., dim[1], dim[2], ...) has the following fields: ")
        print("      time      - date & time at which scan was started: %s" % (dim[1].time))
        print("      name - name of scan record that acquired this dimension: '%s'" % (dim[1].name))
        print("      curr_pt   - number of data points actually acquired: %d" % (dim[1].curr_pt))
        print("      npts      - number of data points requested: %d" % (dim[1].npts))
        print("      nd        - number of detectors for this scan dimension: %d" % (dim[1].nd))
        print("      d[]       - list of detector-data structures")
        print("      np        - number of positioners for this scan dimension: %d" % (dim[1].np))
        print("      p[]       - list of positioner-data structures")
        print("      nt        - number of detector triggers for this scan dimension: %d" % (dim[1].nt))
        print("      t[]       - list of trigger-info structures")

        print(" ")
        print("   each detector-data structure (e.g., dim[1].d[0]) has the following fields: ")
        print("      desc      - description of this detector")
        print("      data      - data list")
        print("      unit      - engineering units associated with this detector")
        print("      fieldName - scan-record field (e.g., 'D01')")

        print(" ")
        print("   each positioner-data structure (e.g., dim[1].p[0]) has the following fields: ")
        print("      desc          - description of this positioner")
        print("      data          - data list")
        print("      step_mode     - scan mode (e.g., Linear, Table, On-The-Fly)")
        print("      unit          - engineering units associated with this positioner")
        print("      fieldName     - scan-record field (e.g., 'P1')")
        print("      name          - name of EPICS PV (e.g., 'xxx:m1.VAL')")
        print("      readback_desc - description of this positioner")
        print("      readback_unit - engineering units associated with this positioner")
        print("      readback_name - name of EPICS PV (e.g., 'xxx:m1.VAL')")

    if (outFile):
        out.close()
    return dim

################################################################################
# skim MDA file to get dimensions (planned and actually acquired), and other info
def skimScan(dataFile):
    """usage: skimScan(dataFile)"""
    scan = scanDim()    # data structure to hold scan info and data
    buf = dataFile.read(10000) # enough to read scan header
    u = xdr.Unpacker(buf)
    scan.rank = u.unpack_int()
    if (scan.rank > 20) or (scan.rank < 0):
        print("* * * skimScan('%s'): rank > 20.  probably a corrupt file" % dataFile.name)
        return None
    scan.npts = u.unpack_int()
    scan.curr_pt = u.unpack_int()
    if (scan.curr_pt == 0):
        #print("mda:skimScan: curr_pt = 0")
        return None
    if (scan.rank > 1):
        if have_fast_xdr:
            scan.plower_scans = u.unpack_farray_int(scan.npts)
        else:
            scan.plower_scans = u.unpack_farray(scan.npts, u.unpack_int)
    namelength = u.unpack_int()
    scan.name = u.unpack_string()
    timelength = u.unpack_int()
    scan.time = u.unpack_string()
    scan.np = u.unpack_int()
    scan.nd = u.unpack_int()
    scan.nt = u.unpack_int()
    return scan

def skimMDA(fname=None, verbose=False):
    """usage skimMDA(fname=None)"""
    #print("skimMDA: filename=", fname)
    dim = []
    if (fname == None):
        print("No file specified")
        return None
    if (not os.path.isfile(fname)):
        if (not fname.endswith('.mda')):
            fname = fname + '.mda'
        if (not os.path.isfile(fname)):
            print(fname, "not found")
            return None

    try:
        dataFile = open(fname, 'rb')
    except:
        print("mda_f:skimMDA: failed to open file '%s'" % fname)
        return None

    buf = dataFile.read(100)        # to read header for scan of up to 5 dimensions
    u = xdr.Unpacker(buf)

    # read file header
    version = u.unpack_float()
#    if version < 1.299 or version > 1.301:
#        print(fname, " has file version", version)
#        return None
    scan_number = u.unpack_int()
    rank = u.unpack_int()
    dimensions = u.unpack_farray(rank, u.unpack_int)
    isRegular = u.unpack_int()
    pExtra = u.unpack_int()
    pmain_scan = dataFile.tell() - (len(buf) - u.get_position())

    # collect 1D data
    dataFile.seek(pmain_scan)
    scan = skimScan(dataFile)
    if (scan == None):
        if verbose: print(fname, "contains no data")
        return None

    dim.append(scan)
    dim[0].dim = 1

    if (rank > 1):
        dataFile.seek(dim[0].plower_scans[0])
        dim.append(skimScan(dataFile))
        if (dim[1]):
            dim[1].dim = 2
        else:
            if verbose: print("had a problem reading 2d from ", fname)
            return None

    if (rank > 2):
        dataFile.seek(dim[1].plower_scans[0])
        dim.append(skimScan(dataFile))
        if (dim[2]):
            dim[2].dim = 3
        else:
            if verbose: print("had a problem reading 3d from ", fname)
            return None

    if (rank > 3):
        dataFile.seek(dim[2].plower_scans[0])
        dim.append(skimScan(dataFile))
        if (dim[3]):
            dim[3].dim = 4
        else:
            if verbose: print("had a problem reading 4d from ", fname)
            return None

    dataFile.close()
    dict = {}
    dict['filename'] = fname
    dict['version'] = version
    dict['scan_number'] = scan_number
    dict['rank'] = rank
    dict['dimensions'] = dimensions
    dimensions = []
    for d in dim:
        dimensions.append(d.curr_pt)
    dict['acquired_dimensions'] = dimensions
    dict['isRegular'] = isRegular
    dim.reverse()
    dim.append(dict)
    dim.reverse()
    return dim

################################################################################
# Write MDA file
def packScanHead(scan):
    s = scanBuf()
    s.npts = scan.npts

    # preamble
    p = xdr.Packer()
    p.pack_int(scan.rank)
    p.pack_int(scan.npts)
    p.pack_int(scan.curr_pt)
    s.preamble = p.get_buffer()

    # file offsets to lower level scans (if any)
    p.reset()
    if (scan.rank > 1):
        # Pack zeros for now, so we'll know how much
        # space the real offsets will use.
        for j in range(scan.npts):
            p.pack_int(0)
    s.pLowerScansBuf = p.get_buffer()

    # postamble
    p.reset()
    n = len(scan.name); p.pack_int(n)
    if (n): p.pack_string(scan.name)
    n = len(scan.time); p.pack_int(n)
    if (n): p.pack_string(scan.time)
    p.pack_int(scan.np)
    p.pack_int(scan.nd)
    p.pack_int(scan.nt)

    for j in range(scan.np):
        p.pack_int(scan.p[j].number)

        n = len(scan.p[j].name); p.pack_int(n)
        if (n): p.pack_string(scan.p[j].name)

        n = len(scan.p[j].desc); p.pack_int(n)
        if (n): p.pack_string(scan.p[j].desc)

        n = len(scan.p[j].step_mode); p.pack_int(n)
        if (n): p.pack_string(scan.p[j].step_mode)

        n = len(scan.p[j].unit); p.pack_int(n)
        if (n): p.pack_string(scan.p[j].unit)

        n = len(scan.p[j].readback_name); p.pack_int(n)
        if (n): p.pack_string(scan.p[j].readback_name)

        n = len(scan.p[j].readback_desc); p.pack_int(n)
        if (n): p.pack_string(scan.p[j].readback_desc)

        n = len(scan.p[j].readback_unit); p.pack_int(n)
        if (n): p.pack_string(scan.p[j].readback_unit)

    for j in range(scan.nd):
        p.pack_int(scan.d[j].number)
        n = len(scan.d[j].name); p.pack_int(n)
        if (n): p.pack_string(scan.d[j].name)
        n = len(scan.d[j].desc); p.pack_int(n)
        if (n): p.pack_string(scan.d[j].desc)
        n = len(scan.d[j].unit); p.pack_int(n)
        if (n): p.pack_string(scan.d[j].unit)

    for j in range(scan.nt):
        p.pack_int(scan.t[j].number)
        n = len(scan.t[j].name); p.pack_int(n)
        if (n): p.pack_string(scan.t[j].name)
        p.pack_float(scan.t[j].command)

    s.postamble = p.get_buffer()
    s.bufLen = len(s.preamble) + len(s.pLowerScansBuf) + len(s.postamble)
    return s

def packScanData(scan, cpt):
    p = xdr.Packer()
    if (len(cpt) == 0): # 1D array
        for i in range(scan.np):
            p.pack_farray(scan.npts, scan.p[i].data, p.pack_double)
        for i in range(scan.nd):
            p.pack_farray(scan.npts, scan.d[i].data, p.pack_float)

    elif (len(cpt) == 1): # 2D array
        j = cpt[0]
        for i in range(scan.np):
            p.pack_farray(scan.npts, scan.p[i].data[j], p.pack_double)
        for i in range(scan.nd):
            p.pack_farray(scan.npts, scan.d[i].data[j], p.pack_float)

    elif (len(cpt) == 2): # 3D array
        j = cpt[0]
        k = cpt[1]
        for i in range(scan.np):
            p.pack_farray(scan.npts, scan.p[i].data[j][k], p.pack_double)
        for i in range(scan.nd):
            p.pack_farray(scan.npts, scan.d[i].data[j][k], p.pack_float)

    return(p.get_buffer())

def writeMDA(dim, fname=None):
    m = mdaBuf()
    p = xdr.Packer()

    p.reset()
    if (type(dim) != type([])): print("writeMDA: first arg must be a scan")
    if ((fname != None) and (type(fname) != type(""))):
        print("writeMDA: second arg must be a filename or None")
    rank = dim[0]['rank']    # rank of scan as a whole
    # write file header
    p.pack_float(dim[0]['version'])
    p.pack_int(dim[0]['scan_number'])
    p.pack_int(dim[0]['rank'])
    p.pack_farray(rank, dim[0]['dimensions'], p.pack_int)
    p.pack_int(dim[0]['isRegular'])
    m.header = p.get_buffer()

    p.reset()
    p.pack_int(0) # pExtra
    m.pExtra = p.get_buffer()

    m.scan = packScanHead(dim[1])
    m.scan.offset = len(m.header) + len(m.pExtra)
    m.scan.data = packScanData(dim[1], [])
    m.scan.bufLen = m.scan.bufLen + len(m.scan.data)
    prevScan = m.scan
    #print("\n m.scan=", m.scan)
    #print("\n type(m.scan.pLowerScans)=", type(m.scan.pLowerScans))

    if (rank > 1):
        for i in range(m.scan.npts):
            m.scan.inner.append(packScanHead(dim[2]))
            thisScan = m.scan.inner[i]
            thisScan.offset = prevScan.offset + prevScan.bufLen
            m.scan.pLowerScans.append(thisScan.offset)
            thisScan.data = packScanData(dim[2], [i])
            thisScan.bufLen = thisScan.bufLen + len(thisScan.data)
            prevScan = thisScan

            if (rank > 2):
                for j in range(m.scan.inner[i].npts):
                    m.scan.inner[i].inner.append(packScanHead(dim[3]))
                    thisScan = m.scan.inner[i].inner[j]
                    thisScan.offset = prevScan.offset + prevScan.bufLen
                    m.scan.inner[i].pLowerScans.append(thisScan.offset)
                    thisScan.data = packScanData(dim[3], [i,j])
                    thisScan.bufLen = thisScan.bufLen + len(thisScan.data)
                    prevScan = thisScan

                if (rank > 3):
                    for k in range(m.scan.inner[i].inner[j].npts):
                        m.scan.inner[i].inner[j].append(packScanHead(dim[4]))
                        thisScan = m.scan.inner[i].inner[j].inner[k]
                        thisScan.offset = prevScan.offset + prevScan.bufLen
                        m.scan.inner[i].inner[j].pLowerScans.append(thisScan.offset)
                        thisScan.data = packScanData(dim[4], [i,j,k])
                        thisScan.bufLen = thisScan.bufLen + len(thisScan.data)
                        prevScan = thisScan

    # Now we know where the extraPV section must go.
    p.reset()
    p.pack_int(prevScan.offset + prevScan.bufLen) # pExtra
    m.pExtra = p.get_buffer()

    # pack scan-environment variables from dictionary
    p.reset()

    numKeys = 0
    for name in dim[0].keys():
        if not (name in dim[0]['ourKeys']):
            numKeys = numKeys + 1
    p.pack_int(numKeys)

    for name in dim[0].keys():
        # Note we don't want to write the dict entries we made for our own
        # use in the scanDim object.
        if not (name in dim[0]['ourKeys']):
            desc = dim[0][name][0]
            unit = dim[0][name][1]
            value = dim[0][name][2]
            EPICS_type = dim[0][name][3]
            count = dim[0][name][4]
            n = len(name); p.pack_int(n)
            if (n): p.pack_string(name)
            n = len(desc); p.pack_int(n)
            if (n): p.pack_string(desc)
            p.pack_int(EPICS_type)
            if EPICS_type != 0:   # not DBR_STRING, so pack count and units
                p.pack_int(count)
                n = len(unit); p.pack_int(n)
                if (n): p.pack_string(unit)
            if EPICS_type == 0: # DBR_STRING
                n = len(value); p.pack_int(n)
                if (n): p.pack_string(value)
            elif EPICS_type == 32: # DBR_CTRL_CHAR
                # write null-terminated string
                v = []
                for i in range(len(value)): v.append(ord(value[i:i+1]))
                v.append(0)
                p.pack_farray(count, v, p.pack_int)
            elif EPICS_type == 29: # DBR_CTRL_SHORT
                p.pack_farray(count, value, p.pack_int)
            elif EPICS_type == 33: # DBR_CTRL_LONG
                p.pack_farray(count, value, p.pack_int)
            elif EPICS_type == 30: # DBR_CTRL_FLOAT
                p.pack_farray(count, value, p.pack_float)
            elif EPICS_type == 34: # DBR_CTRL_DOUBLE
                p.pack_farray(count, value, p.pack_double)

    m.extraPV = p.get_buffer()

    # Now we have to repack all the scan offsets
    if (rank > 1): # 2D scan
        #print("m.scan.pLowerScans", m.scan.pLowerScans)
        p.reset()
        p.pack_farray(m.scan.npts, m.scan.pLowerScans, p.pack_int)
        m.scan.pLowerScansBuf = p.get_buffer()
        if (rank > 2): # 3D scan
            for i in range(m.scan.npts):
                p.reset()
                p.pack_farray(m.scan.inner[i].npts, m.scan.inner[i].pLowerScans, p.pack_int)
                m.scan.inner[i].pLowerScansBuf = p.get_buffer()
                if (rank > 3): # 4D scan
                    for j in range(m.scan.inner[i].npts):
                        p.reset()
                        p.pack_farray(m.scan.inner[i].inner[j].npts, m.scan.inner[i].inner[j].pLowerScans, p.pack_int)
                        m.scan.inner[i].inner[j].pLowerScansBuf = p.get_buffer()

    # Write
    if (fname == None): fname = tkFileDialog.SaveAs().show()
    f = open(fname, 'wb')

    f.write(m.header)
    f.write(m.pExtra)
    s0 = m.scan
    f.write(s0.preamble)
    if len(s0.pLowerScansBuf): f.write(s0.pLowerScansBuf)
    f.write(s0.postamble)
    f.write(s0.data)
    for s1 in s0.inner:
        f.write(s1.preamble)
        if len(s1.pLowerScansBuf): f.write(s1.pLowerScansBuf)
        f.write(s1.postamble)
        f.write(s1.data)
        for s2 in s1.inner:
            f.write(s2.preamble)
            if len(s2.pLowerScansBuf): f.write(s2.pLowerScansBuf)
            f.write(s2.postamble)
            f.write(s2.data)
            for s3 in s2.inner:
                f.write(s3.preamble)
                if len(s3.pLowerScansBuf): f.write(s3.pLowerScansBuf)
                f.write(s3.postamble)
                f.write(s3.data)
    f.write(m.extraPV)
    f.close()
    return

################################################################################
# write Ascii file
def getFormat(d, rank):
    # number of positioners, detectors
    np = d[rank].np
    nd = d[rank].nd

    min_column_width = 15
    # make sure there's room for the names, etc.
    phead_fmt = []
    dhead_fmt = []
    pdata_fmt = []
    ddata_fmt = []
    columns = 1
    for i in range(np):
        cw = max(min_column_width, len(d[rank].p[i].name)+1)
        cw = max(cw, len(d[rank].p[i].desc)+1)
        cw = max(cw, len(d[rank].p[i].fieldName)+1)
        phead_fmt.append("%%-%2ds" % cw)
        pdata_fmt.append("%%- %2d.8f" % cw)
        columns = columns + cw
    for i in range(nd):
        cw = max(min_column_width, len(d[rank].d[i].name)+1)
        cw = max(cw, len(d[rank].d[i].desc)+1)
        cw = max(cw, len(d[rank].d[i].fieldName)+1)
        dhead_fmt.append("%%-%2ds" % cw)
        ddata_fmt.append("%%- %2d.8f" % cw)
        columns = columns + cw
    return (phead_fmt, dhead_fmt, pdata_fmt, ddata_fmt, columns)

def writeAscii(d, fname=None):
    if (type(d) != type([])):
        print("writeMDA: first arg must be a scan")
        return

    if (fname == None):
        f = sys.stdout
    else:
        f = open(fname, 'wb')

    (phead_fmt, dhead_fmt, pdata_fmt, ddata_fmt, columns) = getFormat(d, 1)
    # header
    f.write("### %s is a %d-dimensional file\n" % (d[0]['filename'], d[0]['rank']))
    f.write("### Number of data points      = [")
    for i in range(d[0]['rank'],1,-1): f.write("%-d," % d[i].curr_pt)
    f.write("%-d]\n" % d[1].curr_pt)

    f.write("### Number of detector signals = [")
    for i in range(d[0]['rank'],1,-1): f.write("%-d," % d[i].nd)
    f.write("%-d]\n" % d[1].nd)

    # scan-environment PV values
    f.write("#\n# Scan-environment PV values:\n")
    ourKeys = d[0]['ourKeys']
    maxKeyLen = 0
    for i in d[0].keys():
        if (i not in ourKeys):
            if len(i) > maxKeyLen: maxKeyLen = len(i)
    for i in d[0].keys():
        if (i not in ourKeys):
            f.write("#%s%s%s\n" % (i, (maxKeyLen-len(i))*' ', d[0][i]))

    f.write("\n#%s\n" % str(d[1]))
    f.write("#  scan date, time: %s\n" % d[1].time)
    sep = "#"*columns + "\n"
    f.write(sep)

    # 1D data table head
    f.write("#")
    for j in range(d[1].np):
        f.write(phead_fmt[j] % (d[1].p[j].fieldName))
    for j in range(d[1].nd):
        f.write(dhead_fmt[j] % (d[1].d[j].fieldName))
    f.write("\n")

    f.write("#")
    for j in range(d[1].np):
        f.write(phead_fmt[j] % (d[1].p[j].name))
    for j in range(d[1].nd):
        f.write(dhead_fmt[j] % (d[1].d[j].name))
    f.write("\n")

    f.write("#")
    for j in range(d[1].np):
        f.write(phead_fmt[j] % (d[1].p[j].desc))
    for j in range(d[1].nd):
        f.write(dhead_fmt[j] % (d[1].d[j].desc))
    f.write("\n")

    f.write(sep)

    # 1D data
    for i in range(d[1].curr_pt):
        f.write("")
        for j in range(d[1].np):
            f.write(pdata_fmt[j] % (d[1].p[j].data[i]))
        for j in range(d[1].nd):
            f.write(ddata_fmt[j] % (d[1].d[j].data[i]))
        f.write("\n")

    # 2D data
    if (len(d) > 2):
        f.write("\n# 2D data\n")
        for i in range(d[2].np):
            f.write("\n# Positioner %d (.%s) PV:'%s' desc:'%s'\n" % (i, d[2].p[i].fieldName, d[2].p[i].name, d[2].p[i].desc))
            for j in range(d[1].curr_pt):
                for k in range(d[2].curr_pt):
                    f.write("%f " % d[2].p[i].data[j][k])
                f.write("\n")

        for i in range(d[2].nd):
            f.write("\n# Detector %d (.%s) PV:'%s' desc:'%s'\n" % (i, d[2].d[i].fieldName, d[2].d[i].name, d[2].d[i].desc))
            for j in range(d[1].curr_pt):
                for k in range(d[2].curr_pt):
                    f.write("%f " % d[2].d[i].data[j][k])
                f.write("\n")

    if (len(d) > 3):
        f.write("\n# Can't write 3D (or higher) data\n")

    if (fname != None):
        f.close()


################################################################################
# misc
def showEnv(dict, all=0):
    if type(dict) == type([]) and type(dict[0]) == type({}):
        dict = dict[0]
    fieldLen = 0
    for k in dict.keys():
        if len(k) > fieldLen:
            fieldLen = len(k)
    format = "%%-%-ds %%s" % fieldLen
    for k in dict.keys():
        if not (k in dict['ourKeys']):
            if type(dict[k]) == type((1,2,3)):
                value = dict[k][2]
            else:
                value = dict[k]
            if type(value) == type([]) and len(value) == 1:
                value = value[0]
            if all:
                print(format % (k,dict[k]))
            else:
                print(format % (k,value))
    return

def fixMDA(d):
    """usage: d=fixMDA(d), where d is a list returned by readMDA()"""
    dimensions = []
    for i in range(1,len(d)):
        npts = d[i].curr_pt
        d[i].npts = npts
        dimensions.append(npts)
        for j in range(d[i].np):
            if (len(d[i].p[j].data) > npts):
                d[i].p[j].data = d[i].p[j].data[0:npts]
        for j in range(d[i].nd):
            if (len(d[i].d[j].data) > npts):
                d[i].d[j].data = d[i].d[j].data[0:npts]
    dimensions.reverse()
    d[0]['dimensions'] = dimensions
    return(d)

# translate mca-ROI PV's to mca-ROI description PV's, scaler signal PV'ss to scaler signal description PV's
descDict = {'R1':'R1NM', 'R2':'R2NM', 'R3':'R3NM', 'R4':'R4NM', 'R5':'R5NM',
 'R6':'R6NM', 'R7':'R7NM', 'R8':'R8NM', 'R9':'R9NM', 'R10':'R10NM',
 'R11':'R11NM', 'R12':'R12NM', 'R13':'R13NM', 'R14':'R14NM', 'R15':'R15NM',
 'R16':'R16NM', 'R17':'R17NM', 'R18':'R18NM', 'R19':'R19NM', 'R20':'R20NM',
 'R21':'R21NM', 'R22':'R22NM', 'R23':'R23NM', 'R24':'R24NM', 'R25':'R25NM',
 'R26':'R26NM', 'R27':'R27NM', 'R28':'R28NM', 'R29':'R29NM', 'R30':'R30NM',
 'R31':'R31NM', 'R32':'R32NM',
 'S1':'NM1', 'S2':'NM2', 'S3':'NM3', 'S4':'NM4', 'S5':'NM5', 'S6':'NM6', 'S7':'NM7', 'S8':'NM8', 'S9':'NM9', 'S10':'NM10',
 'S11':'NM11', 'S12':'NM12', 'S13':'NM13', 'S14':'NM14', 'S15':'NM15', 'S16':'NM16', 'S17':'NM17', 'S18':'NM18', 'S19':'NM19', 'S20':'NM20',
 'S21':'NM21', 'S22':'NM22', 'S23':'NM23', 'S24':'NM24', 'S25':'NM25', 'S26':'NM26', 'S27':'NM27', 'S28':'NM28', 'S29':'NM29', 'S30':'NM30',
 'S31':'NM31', 'S32':'NM32', 'S33':'NM33', 'S34':'NM34', 'S35':'NM35', 'S36':'NM36', 'S37':'NM37', 'S38':'NM38', 'S39':'NM39', 'S40':'NM40',
 'S41':'NM41', 'S42':'NM42', 'S43':'NM43', 'S44':'NM44', 'S45':'NM45', 'S46':'NM46', 'S47':'NM47', 'S48':'NM48', 'S49':'NM49', 'S50':'NM50',
 'S51':'NM51', 'S52':'NM52', 'S53':'NM53', 'S54':'NM54', 'S55':'NM55', 'S56':'NM56', 'S57':'NM57', 'S58':'NM58', 'S59':'NM59', 'S60':'NM60',
 'S61':'NM61', 'S62':'NM62', 'S63':'NM63', 'S64':'NM64'}

def findDescInEnv(name, env):
    try:
        (record, field) = name.split('.')
    except:
        return ""
    try:
        descField = descDict[field]
    except:
        return ""
    try:
        desc = env[record+'.'+descField]
    except:
        return ""
    if desc[2] == "" or desc[2].isspace():
        return ""
    return "{%s}" % desc[2]

def getDescFromEnv(data):
    if (data):
        for d in data[1:]:
            for p in d.p:
                if not p.desc:
                    p.desc = findDescInEnv(p.name, data[0])
            for d in d.d:
                if not d.desc:
                    d.desc = findDescInEnv(d.name, data[0])

########################
# opMDA and related code
########################
def isScan(d):
    if type(d) != type([]): return(0)
    if type(d[0]) != type({}): return(0)
    if 'rank' not in d[0].keys(): return(0)
    if len(d) < 2: return(0)
    if type(d[1]) != type(scanDim()): return(0)
    return(1)

def isScalar(d):
    if (type(d) == type(1)) or (type(d) == type(1.0)): return(1)
    return(0)

def add(a,b): return(a+b)
def sub(a,b): return(a-b)
def mul(a,b): return(a*b)
def div(a,b): return(a/b)

def setOp(op):
    if (op == '+') or (op == 'add'): return(add)
    if (op == '-') or (op == 'sub'): return(sub)
    if (op == '*') or (op == 'x') or (op == 'mul'): return(mul)
    if (op == '/') or (op == 'div'): return(div)
    if (op == '>') or (op == 'max'): return(max)
    if (op == '<') or (op == 'min'): return(min)
    print("opMDA: unrecognized op = ", op)
    return None

def opMDA_usage():
    print("opMDA() usage:")
    print("   result = opMDA(op, scan1, scan2)")
    print("        OR")
    print("   result = opMDA(op, scan1, scalar_value)")
    print("\nwhere:")
    print("   op is one of '+', '-', '*', '/', '>', '<'")
    print("   scan1, scan2 are scans, i.e., structures returned by mda.readMDA()")
    print("   result is a copy of scan1, modified by the operation\n")
    print("\n examples:")
    print("   r = opMDA('+', scan1, scan2) -- adds all detector data from scan1 and scan2")
    print("   r = opMDA('-', scan1, 2.0)   -- subtracts 2 from all detector data from scan1")
    print("   r = opMDA('>', r, 0)         -- 'r' data or 0, whichever is greater")

def opMDA_scalar(op, d1, scalar):
    op = setOp(op)
    if (op == None):
        opMDA_usage()
        return None

    s = copy.deepcopy(d1)

    # 1D op
    for i in range(s[1].nd):
        for j in range(s[1].npts):
            s[1].d[i].data[j] = op(s[1].d[i].data[j], scalar)

    if (len(s) == 2): return s
    # 2D op
    for i in range(s[2].nd):
        for j in range(s[1].npts):
            for k in range(s[2].npts):
                s[2].d[i].data[j][k] = op(s[2].d[i].data[j][k], scalar)

    if (len(s) == 3): return s
    # 3D op
    for i in range(s[3].nd):
        for j in range(s[1].npts):
            for k in range(s[2].npts):
                for l in range(s[3].npts):
                    s[3].d[i].data[j][k][l] = op(s[3].d[i].data[j][k][l], scalar)

    if (len(s) == 4): return s
    # 4D op
    for i in range(s[4].nd):
        for j in range(s[1].npts):
            for k in range(s[2].npts):
                for l in range(s[3].npts):
                    for m in range(s[4].npts):
                        s[4].d[i].data[j][k][l][m] = op(s[4].d[i].data[j][k][l][m], scalar)

    if (len(s) > 4):
        print("opMDA supports up to 4D scans")
    return s

def opMDA(op, d1, d2):
    """opMDA() is a function for performing arithmetic operations on MDA files,
    or on an MDA file and a scalar value.

    For examples, type 'opMDA_usage()'.
    """
    if isScan(d1) and isScalar(d2): return(opMDA_scalar(op,d1,d2))
    if (not isScan(d1)) :
        print("opMDA: first operand is not a scan")
        opMDA_usage()
        return None

    if (not isScan(d2)):
        print("opMDA: second operand is neither a scan nor a scalar")
        opMDA_usage()
        return None

    if len(d1) != len(d2):
        print("scans do not have same dimension")
        return None

    op = setOp(op)
    if (op == None):
        opMDA_usage()
        return None

    s = copy.deepcopy(d1)

    # 1D op
    if s[1].nd != d2[1].nd:
        print("scans do not have same number of 1D detectors")
        return None
    if s[1].npts != d2[1].npts:
        print("scans do not have same number of data points")
        return None
    for i in range(s[1].nd):
        s[1].d[i].data = map(op, s[1].d[i].data, d2[1].d[i].data)

    if (len(s) == 2): return s
    # 2D op
    if s[2].nd != d2[2].nd:
        print("scans do not have same number of 2D detectors")
        return None
    if s[2].npts != d2[2].npts:
        print("scans do not have same number of data points")
        return None
    for i in range(s[2].nd):
        for j in range(s[1].npts):
            s[2].d[i].data[j] = map(op, s[2].d[i].data[j], d2[2].d[i].data[j])

    if (len(s) == 3): return s
    # 3D op
    if s[3].nd != d2[3].nd:
        print("scans do not have same number of 3D detectors")
        return None
    if s[3].npts != d2[3].npts:
        print("scans do not have same number of data points")
        return None
    for i in range(s[3].nd):
        for j in range(s[1].npts):
            for k in range(s[2].npts):
                s[3].d[i].data[j][k] = map(op, s[3].d[i].data[j][k], d2[3].d[i].data[j][k])

    if (len(s) == 4): return s
    # 3D op
    if s[4].nd != d2[4].nd:
        print("scans do not have same number of 4D detectors")
        return None
    if s[4].npts != d2[4].npts:
        print("scans do not have same number of data points")
        return None
    for i in range(s[4].nd):
        for j in range(s[1].npts):
            for k in range(s[2].npts):
                for l in range(s[3].npts):
                    s[4].d[i].data[j][k][l] = map(op, s[4].d[i].data[j][k][l], d2[4].d[i].data[j][k][l])

    if (len(s) > 5):
        print("opMDA supports up to 4D scans")
    return s


def read_mda(fname, maxdim=3, verbose=False, _larch=None):
    """read an MDA file from the Epics Scan Record

    Arguments
    ---------
    filname (str)     name of file
    maxdim (integer)  max number of dimensions [default=3]

    Returns
    -------
    group containing `scan1` and possibly `scan2`, etc objects

    Notes
    -----
    not very well tested for scans of dimension > 2

    """
    out = readMDA(fname, maxdim=maxdim, verbose=verbose)
    if _larch is None:
        return out
    group = _larch.symtable.create_group(name='MDA_file %s' % fname)
    group.extra_pvs = out[0]
    group.scan1 = out[1]
    group.dimension = dim = len(out) - 1

    if dim > 1:
        group.scan2 = out[2]
    if dim > 2:
        group.scan3 = out[3]
    if dim > 3:
        group.scan4 = out[4]

    if dim == 1:
        data, array_labels, field_names, pv_names  = [], [], [], []
        for x in group.scan1.p + group.scan1.d:
            data.append(x.data)
            pv_names.append(x.name)
            field_names.append(x.fieldName)
            label = x.desc
            if label in (None, 'None', ''):
                label = x.fieldName
            array_labels.append(label)

        group.data = numpy.array(data)
        group.pv_names = pv_names
        group.field_names = field_names
        group.array_labels = array_labels
    return group
