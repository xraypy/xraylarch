#!/usr/bin/env python
# adopted with few changes from Tim Mooney's mda.py
#
# version 1 Tim Mooney 5/30/2006
# derived from readMDA.py
# - supports reading, writing, and arithmetic operations for up to 4D MDA files

import xdrlib
import numpy as np
import sys
import os
import string
import copy

class scanDim:
    def __init__(self):
        self.rank = 0
        self.dim = 0
        self.npts = 0
        self.curr_pt = 0
        self.plower_scans = 0
        self.name = ""
        self.time = ""
        self.np = 0
        self.p = []                # list of scanPositioner instances
        self.nd = 0
        self.d = []                # list of scanDetector instances
        self.nt = 0
        self.t = []                # list of scanTrigger instances

    def __str__(self):
        if self.name != '':
            s = "%dD data from \"%s\": %d/%d pts; %d positioners, %d detectors" % (
                self.dim, self.name, self.curr_pt, self.npts, self.np, self.nd)
        else:
            s = "%dD data (not read in)" % (self.dim)

        return s

class scanPositioner:
    def __init__(self):
        self.number = 0
        self.fieldName = ""
        self.name = ""
        self.desc = ""
        self.step_mode = ""
        self.unit = ""
        self.readback_name = ""
        self.readback_desc = ""
        self.readback_unit = ""
        self.data = []

    def __str__(self):
        s = "positioner %d (%s), desc:%s, unit:%s\n" % (self.number, self.name,
            self.desc, self.unit)
        s = s + "   step mode: %s, readback:\"%s\"\n" % (self.step_mode,
            self.readback_name)
        s = s + "data:%s" % (str(self.data))
        return s

class scanDetector:
    def __init__(self):
        self.number = 0
        self.fieldName = ""
        self.name = ""
        self.desc = ""
        self.unit = ""
        self.data = []

    def __str__(self):
        s = "detector %d (%s), desc:%s, unit:%s, data:%s\n" % (self.number,
            self.name, self.desc, self.unit, str(self.data))
        return s

class scanTrigger:
    def __init__(self):
        self.number = 0
        self.name = ""
        self.command = 0.0

    def __str__(self):
        s = "trigger %d (%s), command=%f\n" % (self.number,
            self.name, self.command)
        return s

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

class mdaBuf:
    def __init__(self):
        self.header = None
        self.pExtra = None    # file offset to extraPV section
        self.scan = None
        self.extraPV = None    # extraPV section

def detName(i):
    if i < 100:
        return "D%02d"%(i+1)
    else:
        return "?"

def oldDetName(i):
    if i < 15:
        return string.upper("D%s"%(hex(i+1)[2]))
    elif i < 85:
        return "D%02d"%(i-14)
    else:
        return "?"

def posName(i):
    if i < 4:
        return "P%d" % (i+1)
    else:
        return "?"

def readScan(file, v):
    scan = scanDim()
    buf = file.read(10000) # enough to read scan header
    u = xdrlib.Unpacker(buf)
    scan.rank = u.unpack_int()
    if v: print("scan.rank = ", repr(scan.rank))
    scan.npts = u.unpack_int()
    if v: print("scan.npts = ", repr(scan.npts))
    scan.curr_pt = u.unpack_int()
    if v: print("scan.curr_pt = ", repr(scan.curr_pt))
    if (scan.rank > 1):
        # if curr_pt < npts, plower_scans will have garbage for pointers to
        # scans that were planned for but not written
        scan.plower_scans = u.unpack_farray(scan.npts, u.unpack_int)
        if v: print("scan.plower_scans = ", repr(scan.plower_scans))
    namelength = u.unpack_int()
    scan.name = u.unpack_string()
    if v: print("scan.name = ", repr(scan.name))
    timelength = u.unpack_int()
    scan.time = u.unpack_string()
    if v: print("scan.time = ", repr(scan.time))
    scan.np = u.unpack_int()
    if v: print("scan.np = ", repr(scan.np))
    scan.nd = u.unpack_int()
    if v: print("scan.nd = ", repr(scan.nd))
    scan.nt = u.unpack_int()
    if v: print("scan.nt = ", repr(scan.nt))
    for j in range(scan.np):
        scan.p.append(scanPositioner())
        scan.p[j].number = u.unpack_int()
        scan.p[j].fieldName = posName(scan.p[j].number)
        if v: print("positioner ", j)
        length = u.unpack_int() # length of name string
        if length: scan.p[j].name = u.unpack_string()
        if v: print("scan.p[%d].name = %s" % (j, repr(scan.p[j].name)))
        length = u.unpack_int() # length of desc string
        if length: scan.p[j].desc = u.unpack_string()
        if v: print("scan.p[%d].desc = %s" % (j, repr(scan.p[j].desc)))
        length = u.unpack_int() # length of step_mode string
        if length: scan.p[j].step_mode = u.unpack_string()
        if v: print("scan.p[%d].step_mode = %s" % (j, repr(scan.p[j].step_mode)))
        length = u.unpack_int() # length of unit string
        if length: scan.p[j].unit = u.unpack_string()
        if v: print("scan.p[%d].unit = %s" % (j, repr(scan.p[j].unit)))
        length = u.unpack_int() # length of readback_name string
        if length: scan.p[j].readback_name = u.unpack_string()
        if v: print("scan.p[%d].readback_name = %s" % (j, repr(scan.p[j].readback_name)))
        length = u.unpack_int() # length of readback_desc string
        if length: scan.p[j].readback_desc = u.unpack_string()
        if v: print("scan.p[%d].readback_desc = %s" % (j, repr(scan.p[j].readback_desc)))
        length = u.unpack_int() # length of readback_unit string
        if length: scan.p[j].readback_unit = u.unpack_string()
        if v: print("scan.p[%d].readback_unit = %s" % (j, repr(scan.p[j].readback_unit)))

    for j in range(scan.nd):
        scan.d.append(scanDetector())
        scan.d[j].number = u.unpack_int()
        scan.d[j].fieldName = detName(scan.d[j].number)
        if v: print("detector ", j)
        length = u.unpack_int() # length of name string
        if length: scan.d[j].name = u.unpack_string()
        if v: print("scan.d[%d].name = %s" % (j, repr(scan.d[j].name)))
        length = u.unpack_int() # length of desc string
        if length: scan.d[j].desc = u.unpack_string()
        if v: print("scan.d[%d].desc = %s" % (j, repr(scan.d[j].desc)))
        length = u.unpack_int() # length of unit string
        if length: scan.d[j].unit = u.unpack_string()
        if v: print("scan.d[%d].unit = %s" % (j, repr(scan.d[j].unit)))

    for j in range(scan.nt):
        scan.t.append(scanTrigger())
        scan.t[j].number = u.unpack_int()
        if v: print("trigger ", j)
        length = u.unpack_int() # length of name string
        if length: scan.t[j].name = u.unpack_string()
        if v: print("scan.t[%d].name = %s" % (j, repr(scan.t[j].name)))
        scan.t[j].command = u.unpack_float()
        if v: print("scan.t[%d].command = %s" % (j, repr(scan.t[j].command)))

    ### read data
    # positioners
    file_loc = file.tell() - (len(buf) - u.get_position())
    file.seek(file_loc)
    buf = file.read(scan.np * scan.npts * 8)
    u = xdrlib.Unpacker(buf)
    for j in range(scan.np):
        if v: print("read %d pts for pos. %d at file loc %x" % (scan.npts,
            j, file_loc))
        scan.p[j].data = np.array(u.unpack_farray(scan.npts, u.unpack_double))
        if v: print("scan.p[%d].data = %s" % (j, repr(scan.p[j].data)))

    # detectors
    file.seek(file.tell() - (len(buf) - u.get_position()))
    buf = file.read(scan.nd * scan.npts * 4)
    u = xdrlib.Unpacker(buf)
    for j in range(scan.nd):
        scan.d[j].data = np.array(u.unpack_farray(scan.npts, u.unpack_float))
        if v: print("scan.d[%d].data = %s" % (j, repr(scan.d[j].data)))

    return scan

def readMDA(fname, maxdim=4, verbose=0, help=0):
    dim = []

    if (not os.path.isfile(fname)):
        fname = fname + '.mda'
    if (not os.path.isfile(fname)):
        print(fname," is not a file")
        return dim

    file = open(fname, 'rb')
    # to read header for scan of up to 5 dimensions
    buf = file.read(100)
    u = xdrlib.Unpacker(buf)

    # read file header
    version = u.unpack_float()
    scan_number = u.unpack_int()
    rank = u.unpack_int()
    dimensions = u.unpack_farray(rank, u.unpack_int)
    isRegular = u.unpack_int()
    pExtra = u.unpack_int()
    pmain_scan = file.tell() - (len(buf) - u.get_position())

    # collect 1D data
    file.seek(pmain_scan)
    dim.append(readScan(file, max(0,verbose-1)))
    dim[0].dim = 1

    if ((rank > 1) and (maxdim > 1)):
        # collect 2D data
        for i in range(dim[0].curr_pt):
            file.seek(dim[0].plower_scans[i])
            if (i==0):
                dim.append(readScan(file, max(0,verbose-1)))
                dim[1].dim = 2
                # replace data arrays [1,2,3] with [[1,2,3]]
                for j in range(dim[1].np):
                    data = dim[1].p[j].data
                    dim[1].p[j].data = []
                    dim[1].p[j].data.append(data)
                for j in range(dim[1].nd):
                    data = dim[1].d[j].data
                    dim[1].d[j].data = []
                    dim[1].d[j].data.append(data)
            else:
                s = readScan(file, max(0,verbose-1))
                # append data arrays
                # [ [1,2,3], [2,3,4] ] -> [ [1,2,3], [2,3,4], [3,4,5] ]
                for j in range(s.np): dim[1].p[j].data.append(s.p[j].data)
                for j in range(s.nd): dim[1].d[j].data.append(s.d[j].data)

    if ((rank > 2) and (maxdim > 2)):
        # collect 3D data
        for i in range(dim[0].curr_pt):
            file.seek(dim[0].plower_scans[i])
            s1 = readScan(file, max(0,verbose-1))
            for j in range(s1.curr_pt):
                file.seek(s1.plower_scans[j])
                if ((i == 0) and (j == 0)):
                    dim.append(readScan(file, max(0,verbose-1)))
                    dim[2].dim = 3
                    # replace data arrays [1,2,3] with [[[1,2,3]]]
                    for k in range(dim[2].np):
                        data = dim[2].p[k].data
                        dim[2].p[k].data = [[]]
                        dim[2].p[k].data[0].append(data)
                    for k in range(dim[2].nd):
                        data = dim[2].d[k].data
                        dim[2].d[k].data = [[]]
                        dim[2].d[k].data[0].append(data)
                else:
                    s = readScan(file, max(0,verbose-1))
                    # append data arrays
                    # if j==0: [[[1,2,3], [2,3,4]]] -> [[[1,2,3], [2,3,4]], [[3,4,5]]]
                    # else: [[[1,2,3], [2,3,4]]] -> [[[1,2,3], [2,3,4]], [[3,4,5]]]
                    for k in range(s.np):
                        if j==0: dim[2].p[k].data.append([])
                        dim[2].p[k].data[i].append(s.p[k].data)
                    for k in range(s.nd):
                        if j==0: dim[2].d[k].data.append([])
                        dim[2].d[k].data[i].append(s.d[k].data)

    if ((rank > 3) and (maxdim > 3)):
        # collect 4D data
        for i in range(dim[0].curr_pt):
            file.seek(dim[0].plower_scans[i])
            s1 = readScan(file, max(0,verbose-1))
            for j in range(s1.curr_pt):
                file.seek(s1.plower_scans[j])
                s2 = readScan(file, max(0,verbose-1))
                for k in range(s2.curr_pt):
                    file.seek(s2.plower_scans[k])
                    if ((i == 0) and (j == 0) and (k == 0)):
                        dim.append(readScan(file, max(0,verbose-1)))
                        dim[3].dim = 4
                        for m in range(dim[3].np):
                            data = dim[3].p[m].data
                            dim[3].p[m].data = [[[]]]
                            dim[3].p[m].data[0][0].append(data)
                        for m in range(dim[3].nd):
                            data = dim[3].d[m].data
                            dim[3].d[m].data = [[[]]]
                            dim[3].d[m].data[0][0].append(data)
                    else:
                        s = readScan(file, max(0,verbose-1))
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



    # Collect scan-environment variables into a dictionary
    dict = {}
    dict['sampleEntry'] = ("description", "unit string", "value", "EPICS_type")
    dict['filename'] = fname
    dict['version'] = version
    dict['scan_number'] = scan_number
    dict['rank'] = rank
    dict['dimensions'] = dimensions
    dict['isRegular'] = isRegular
    dict['ourKeys'] = ['sampleEntry', 'filename', 'version', 'scan_number', 'rank', 'dimensions', 'isRegular', 'ourKeys']
    if pExtra:
        file.seek(pExtra)
        buf = file.read()       # Read all scan-environment data
        u = xdrlib.Unpacker(buf)
        numExtra = u.unpack_int()
        for i in range(numExtra):
            name = ''
            n = u.unpack_int()      # length of name string
            if n: name = u.unpack_string()
            desc = ''
            n = u.unpack_int()      # length of desc string
            if n: desc = u.unpack_string()
            EPICS_type = u.unpack_int()

            unit = ''
            value = ''
            count = 0
            if EPICS_type != 0:   # not DBR_STRING
                count = u.unpack_int()  #
                n = u.unpack_int()      # length of unit string
                if n: unit = u.unpack_string()

            if EPICS_type == 0: # DBR_STRING
                n = u.unpack_int()      # length of value string
                if n: value = u.unpack_string()
            elif EPICS_type == 32: # DBR_CTRL_CHAR
                #value = u.unpack_fstring(count)
                v = u.unpack_farray(count, u.unpack_int)
                value = ""
                for i in range(len(v)):
                    # treat the byte array as a null-terminated string
                    if v[i] == 0: break
                    value = value + chr(v[i])

            elif EPICS_type == 29: # DBR_CTRL_SHORT
                value = u.unpack_farray(count, u.unpack_int)
            elif EPICS_type == 33: # DBR_CTRL_LONG
                value = u.unpack_farray(count, u.unpack_int)
            elif EPICS_type == 30: # DBR_CTRL_FLOAT
                value = u.unpack_farray(count, u.unpack_float)
            elif EPICS_type == 34: # DBR_CTRL_DOUBLE
                value = u.unpack_farray(count, u.unpack_double)

            dict[name] = (desc, unit, value, EPICS_type, count)
    file.close()

    dim.reverse()
    dim.append(dict)
    dim.reverse()
    if verbose:
        print("%s is a %d-D file; %d dimensions read in." % (fname, dim[0]['rank'], len(dim)-1))
        print("dim[0] = dictionary of %d scan-environment PVs" % (len(dim[0])))
        print("   usage: dim[0]['sampleEntry'] ->", dim[0]['sampleEntry'])
        for i in range(1,len(dim)):
            print("dim[%d] = %s" % (i, str(dim[i])))
        print("   usage: dim[1].p[2].data -> 1D array of positioner 2 data")
        print("   usage: dim[2].d[7].data -> 2D array of detector 7 data")

    if help:
        print(" ")
        print("   each dimension (e.g., dim[1]) has the following fields: ")
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

    if help:
        print(" ")
        print("   each detector-data structure (e.g., dim[1].d[0]) has the following fields: ")
        print("      desc      - description of this detector")
        print("      data      - data list")
        print("      unit      - engineering units associated with this detector")
        print("      fieldName - scan-record field (e.g., 'D01')")


    if help:
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

    return dim

def packScanHead(scan):
    s = scanBuf()
    s.npts = scan.npts

    # preamble
    p = xdrlib.Packer()
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
    p = xdrlib.Packer()
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

def writeMDA(dim, fname):
    m = mdaBuf()
    p = xdrlib.Packer()

    p.reset()
    if (type(dim) != type([])):
	    print("writeMDA: first arg must be a scan")
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
    for name in list(dim[0].keys()):
        if not (name in dim[0]['ourKeys']):
            numKeys = numKeys + 1
    p.pack_int(numKeys)

    for name in list(dim[0].keys()):
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
        print("m.scan.pLowerScans", m.scan.pLowerScans)
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


########################
# opMDA and related code
########################
def isScan(d):
    if type(d) != type([]): return(0)
    if type(d[0]) != type({}): return(0)
    if 'rank' not in list(d[0].keys()): return(0)
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
    """opMDA() is a function for performing arithmetic operations on MDA files, or on an MDA file and a scalar value.

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
        s[1].d[i].data = list(map(op, s[1].d[i].data, d2[1].d[i].data))

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
            s[2].d[i].data[j] = list(map(op, s[2].d[i].data[j], d2[2].d[i].data[j]))

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
                s[3].d[i].data[j][k] = list(map(op, s[3].d[i].data[j][k], d2[3].d[i].data[j][k]))

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
                    s[4].d[i].data[j][k][l] = list(map(op, s[4].d[i].data[j][k][l], d2[4].d[i].data[j][k][l]))

    if (len(s) > 5):
        print("opMDA supports up to 4D scans")
    return s

def read_mda(fname, maxdim=4, verbose=False, _larch=None, **kws):
    """read an MDA file from the Epics Scan Record

    Warning: not very well tested for scans of high dimension
    """
    out = readMDA(fname, maxdim=maxdim, verbose=verbose)
    if _larch is None:
        return out
    group = _larch.symtable.create_group(name='MDA_file %s' % fname)
    group.extra_pvs = out[0]
    group.scan1 = out[1]
    if len(out) > 2:
        group.scan2 = out[2]
    if len(out) > 3:
        group.scan3 = out[3]
    if len(out) > 4:
        group.scan4 = out[4]
    return group


def registerLarchPlugin():
    return ('_io', {'read_mda': read_mda})
