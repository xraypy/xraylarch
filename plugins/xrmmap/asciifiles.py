"""
utilities for reading files from raw scan folder
"""
import os
import sys
import numpy

if sys.version[0] == '2':
    from ConfigParser import  ConfigParser
elif sys.version[0] == '3':
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
    h, d = readASCII(fname, nskip=0, isnumeric=True)

    ## header info
    splfl = None
    xpix,ypix = None,None
    poni1,poni2 = None,None
    dist = None
    rot1,rot2,rot3 = None,None,None
    wavelength = None
    plr = None
    nrm = None
    units = None

    for line in h:
        import re
        line = re.sub(',','',line)

        if 'SplineFile' in line:
            splfl = line.split()[-1]
        if 'PixelSize' in line:
            xpix,ypix = float(line.split()[2]),float(line.split()[3])
        if 'PONI' in line:
            poni1,poni2 = float(line.split()[2]),float(line.split()[3])
        if 'Detector' in line:
            dist = float(line.split()[-2])
        if 'Rotations' in line:
            rot1,rot2,rot3 = float(line.split()[2]),float(line.split()[3]),float(line.split()[4])

        if 'Wavelength' in line:
            wavelength = float(line.split()[-1])
        if 'Polarization' in line:
            if line.split()[-1] != 'None': plr = float(line.split()[-1])
        if 'Normalization' in line:
            nrm = float(line.split()[-1])

        if 'q_' in line or '2th_' in line:
            units = line.split()[1]


    print 'splfl',splfl
    print 'xpix,ypix',xpix,ypix
    print 'poni1,poni2',poni1,poni2
    print 'dist',dist
    print 'rot1,rot2,rot3',rot1,rot2,rot3
    print 'wavelength',wavelength
    print 'plr',plr
    print 'nrm',nrm
    print 'units',units



    ## data
    x,y = numpy.split(numpy.array(d),2,axis=1)
    
    return x,y,units,wavelength

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

def readROIFile(hfile):
    cp =  ConfigParser()
    cp.read(hfile)
    output = []
    for a in cp.options('rois'):
        if a.lower().startswith('roi'):
            iroi = int(a[3:])
            name, dat = cp.get('rois',a).split('|')
            lims = [int(i) for i in dat.split()]
            ndet = len(lims)/2
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
