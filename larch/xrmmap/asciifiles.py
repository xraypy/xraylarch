"""
utilities for reading files from raw scan folder
"""
import os
import sys
import numpy
from configparser import  ConfigParser

def readASCII(fname, nskip=0, isnumeric=True):
    dat, header = [], []
    with open(fname,'r') as fh:
        lines = fh.readlines()
    for line in lines:
        if line.startswith('#') or line.startswith(';'):
            header.append(line[:-1])
            continue
        if nskip > 0:
            nskip -= 1
            header.append(line[:-1])
            continue
        if isnumeric:
            dat.append([float(x) for x in line[:-1].split()])
        else:
            dat.append(line[:-1].split())
    if isnumeric:
        dat = numpy.array(dat)
    return header, dat

def readMasterFile(fname):
    return readASCII(fname, nskip=0, isnumeric=False)

def readEnvironFile(fname):
    h, d = readASCII(fname, nskip=0, isnumeric=False)
    return h

def read1DXRDFile(fname,metadata=True):
    return readASCII(fname, nskip=0, isnumeric=True)

def parseEnviron(text):
    """ split Environ data into desc, addr, val arrays """
    env_desc, env_addr, env_vals = [], [], []
    for eline in text:
        eline = eline.replace('\t',' ').strip()
        desc, val = [i.strip() for i in eline[1:].split('=')]
        addr = ''
        if '(' in desc:
            n = desc.rfind('(')
            addr = desc[n+1:-1]
            if addr.endswith(')'):
                addr = addr[:-1]
            desc = desc[:n].rstrip()
        env_vals.append(val)
        env_desc.append(desc)
        env_addr.append(addr)
    return env_desc, env_addr, env_vals

def readScanConfig(folder):
    sfile = os.path.join(folder, 'Scan.ini')
    if not os.path.exists(sfile):
        raise IOError('No configuration file found')

    cp = ConfigParser()
    cp.read(sfile)
    timestamp = os.stat(sfile).st_mtime
    scan = {'timestamp': timestamp}
    for key in cp.sections():
        scan[key] = {}
        for attr in cp.options(key):
            scan[key][attr]  = cp.get(key, attr)

    # return scan, general, timestamp
    return scan

def readROIFile(hfile,xrd=False):

    cp =  ConfigParser()
    cp.read(hfile)
    output = []

    if xrd:
        for a in cp.options('xrd1d'):
            if a.lower().startswith('roi'):
                iroi = int(a[3:])
                name,unit,dat = cp.get('xrd1d',a).split('|')
                lims = [float(i) for i in dat.split()]
                dat = [lims[0], lims[1]]
                output.append((iroi, name.strip(), unit.strip(), dat))
        return sorted(output)

    else:
        for a in cp.options('rois'):
            if a.lower().startswith('roi'):
                iroi = int(a[3:])
                name, dat = cp.get('rois',a).split('|')
                lims = [int(i) for i in dat.split()]
                ndet = int(len(lims)/2)
                dat = []
                for i in range(ndet):
                    dat.append((lims[i*2], lims[i*2+1]))
                output.append((iroi, name.strip(), dat))
        roidata = sorted(output)

        calib = {}

        caldat = cp.options('calibration')
        for attr in ('offset', 'slope', 'quad'):
            calib[attr] = [float(x) for x in cp.get('calibration', attr).split()]
        extra = {}
        ndet = len(calib['offset'])
        file_sections = cp.sections()
        for section in ('dxp', 'extra'):
            if section not in file_sections:
                continue
            for attr in cp.options(section):
                tmpdat = [x for x in cp.get(section, attr).split()]
                if len(tmpdat) == 2*ndet:
                    tmpdat = ['%s %s' % (i, j) for i, j in zip(tmpdat[::2], tmpdat[1::2])]
                try:
                    extra[attr] = [int(x) for x in tmpdat]
                except ValueError:
                    try:
                        extra[attr] = [float(x) for x in tmpdat]
                    except ValueError:
                        extra[attr] = tmpdat


        return roidata, calib, extra
