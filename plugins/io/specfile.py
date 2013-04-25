#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SpecfileData object to work with SPEC files from Certified Scientific
Software (http://www.certif.com/)

Authors
-------
- Mauro Rovezzi <mauro.rovezzi@gmail.com>

Requirements
------------
- specfilewrapper from PyMca distribution (http://pymca.sourceforge.net/)
- griddata from  Matplotlib distribution

TODO
----
- get_mrg() : register the Larch method and put a test/example
- _pymca_average() : find faster routine
- correct wrong normalization for get_map!!!
- implement the case of dichroic measurements (two consecutive scans with flipped helicity)

"""

import os, sys, warnings
import numpy as np

HAS_PYMCA = False
HAS_SIMPLEMATH = False
try:
    from PyMca import specfilewrapper as specfile
    HAS_PYMCA = True
except ImportError:
    print "Warning: cannot load specfile -- PyMca not installed?"

try:
    from PyMca import SimpleMath
    HAS_SIMPLEMATH = True
except ImportError:
    print "Warning: cannot load SimpleMath -- PyMca not installed?"


### UTILITIES (the class is below!)

def _str2rng(rngstr):
    """ simple utility to convert a generic string representing a
    compact list of scans to a sorted list of integers

    Example
    -------
    > _str2rng('100, 7:9, 130:140:5, 14, 16:18:1')
    > [7, 8, 9, 14, 16, 17, 18, 100, 130, 135, 140]

    """
    _rng = []
    for _r in rngstr.split(', '): #the space is important!
        if (len(_r.split(',')) > 1):
            raise NameError('The space after comma(s) is mandatory in {0}'.format(_r))
        _rsplit2 = _r.split(':')
        if (len(_rsplit2) == 1):
            _rng.append(_r)
        elif (len(_rsplit2) == 2 or len(_rsplit2) == 3):
            if len(_rsplit2) == 2 :
                _rsplit2.append('1')
            if (_rsplit2[0] == _rsplit2[1]):
                raise NameError("Wrong range '{0}' in string '{1}'".format(_r, rngstr))
            if (int(_rsplit2[0]) > int(_rsplit2[1])):
                raise NameError("Wrong range '{0}' in string '{1}'".format(_r, rngstr))
            _rng.extend(range(int(_rsplit2[0]), int(_rsplit2[1])+1, int(_rsplit2[2])))
        else:
            raise NameError('Too many colon in {0}'.format(_r))

    #create the sorted list and return it (removing the duplicates)
    _rngout = [int(x) for x in _rng]
    _rngout.sort()
    return list(set(_rngout))

def _mot2array(motor, acopy):
    """simple utility to generate a copy of an array containing a constant value (e.g. motor position)"""
    a = np.ones_like(acopy)
    return np.multiply(a, motor)


def _pymca_average(xdats, zdats):
    """this is a call to SimpleMath.average() method from PyMca/SimpleMath.py

    Parameters
    ----------
    - xdats, ydats : lists of arrays contaning the data to merge

    Returns
    -------
    - xmrg, zmrg : 1D arrays containing the merged data
    """
    if HAS_SIMPLEMATH:
        sm = SimpleMath.SimpleMath()
        print "Merging data (can take a while due to interpolation)..."
        return sm.average(xdats, zdats)
    else:
        raise NameError("SimpleMath is not available -- this operation cannot be performed!")

### MAIN CLASS
class SpecfileData(object):
    "SpecFile object"
    def __init__(self, fname=None, cntx=1, cnty=None, csig=None, cmon=None, csec=None, norm=None):
        """reads the given specfile"""
        if fname is None:
            raise NameError("Provide a SPEC data file to load with full path")
        elif not os.path.isfile(fname):
            raise OSError("File not found: '%s'" % fname)
        else:
            self.fname = fname
            if hasattr(self, 'sf'):
                pass
            else:
                self.sf = specfile.Specfile(fname) #sf = specfile file
                print "Loaded SPEC file: {0}".format(fname)
                #print "The total number of scans is: {0}".format(self.sf.scanno())
        #set common attributes
        self.cntx = cntx
        self.cnty = cnty
        self.csig = csig
        self.cmon = cmon
        self.csec = csec
        self.norm = norm

    def get_scan(self, scan=None, scnt=None, **kws):
        """ get a single scan

        Parameters
        ----------
        scan : scan number to get [integer]
        cntx : counter for x axis, motor 1 scanned [string]
        cnty : counter for y axis, motor 2 steps [string] - used by get_map()
        csig : counter for signal [string]
        cmon : counter for monitor/normalization [string]
        csec : counter for time in seconds [string]
        scnt : scan type [string]
        norm : normalization [string]
               'area' -> scan_datz = scan_datz/np.trapz(scan_datz)
               'max-min' -> scan_datz = scan_datz/(np.max(scan_datz)-np.min(scan_datz))
               'sum' -> scan_datz = scan_datz/np.sum(z)

        Returns
        -------
        scan_datx : 1D array with x data (scanned axis)
        scan_datz : 1D array with z data (intensity axis)
        scan_mots : dictionary with all motors positions for the given scan
                    NOTE: if cnty is given, it will return only scan_mots[cnty]
        scan_info : dictionary with information on the scan -> NOT YET IMPLEMENTED!
        """
        #get keywords arguments
        cntx = kws.get('cntx', self.cntx)
        cnty = kws.get('cnty', self.cnty)
        csig = kws.get('csig', self.csig)
        cmon = kws.get('cmon', self.cmon)
        csec = kws.get('csec', self.csec)
        norm = kws.get('norm', self.norm)
        #input checks
        if scan is None:
            raise NameError('Provide the scan number to get [integer]: between 1 and {0}'.format(self.sf.scanno()))
        if cntx is None:
            raise NameError('Provide the counter for x, the abscissa [string]')
        if cnty is not None and not (cnty in self.sf.allmotors()):
            raise NameError("'{0}' is not in the list of motors".format(cnty))
        if csig is None:
            raise NameError('Provide the counter for signal [string]')
        if cmon is None:
            raise NameError('Provide the counter for monitor/normalization [string]')
        if csec is None:
            _iscps = False
            warnings.warn('No counter for time in seconds [string]: the signal will not be expressed in cps')
        else:
            _iscps = True

        #select the given scan number
        self.sd = self.sf.select(str(scan)) #sd = specfile data

        #the case cntx is not given it is taken as the first counter by default
        if cntx == 1:
            _cntx = self.sd.alllabels()[0]
        else:
            _cntx = cntx

        ## x-axis
        if scnt is None:
            #try to guess the scan type if it is not given
            #this condition should work in case of an energy scan
            if ('ene' in _cntx.lower()):
                #this condition should detect if the energy scale is KeV
                if (self.sd.datacol(cntx).max() - self.sd.datacol(cntx).min()) < 3.0:
                    scan_datx = self.sd.datacol(cntx)*1000
                    _xscale = 1000.0
                    _xlabel = "energy, eV"
            else:
                scan_datx = self.sd.datacol(cntx)
                _xscale = 1.0
                _xlabel = "energy, KeV"
        else:
            raise NameError("Wrong scan type string")

        ## z-axis
        if _iscps:
            scan_datz = self.sd.datacol(csig)/self.sd.datacol(cmon)*np.mean(self.sd.datacol(cmon))/self.sd.datacol(csec)
            _zlabel = "signal/monitor, per seconds"
        else:
            scan_datz = self.sd.datacol(csig)/self.sd.datacol(cmon)
            _zlabel = "signal/monitor"

        ### z-axis normalization, if required
        if norm is not None:
            _zlabel = "{0} norm by {1}".format(_zlabel, norm)
            if norm == "area":
                scan_datz = scan_datz/np.trapz(scan_datz)
            elif norm == "max-min":
                scan_datz = scan_datz/(np.max(scan_datz)-np.min(scan_datz))
            elif norm == "sum":
                scan_datz = scan_datz/np.sum(scan_datz)
            else:
                raise NameError("Provide a correct normalization type string")

        ## the motors dictionary
        scan_mots = dict(zip(self.sf.allmotors(), self.sd.allmotorpos()))

        ## y-axis
        if cnty is not None:
            _ylabel = "motor {0} at {1}".format(cnty, scan_mots[cnty])
        else:
            _ylabel = _zlabel

        ## collect information on the scan
        scan_info = {'xlabel' : _xlabel,
                     'ylabel' : _ylabel,
                     'zlabel' : _zlabel}

        if cnty is not None:
            return scan_datx, scan_datz, scan_mots[cnty]*_xscale
        else:
            return scan_datx, scan_datz, scan_mots, scan_info

    def get_map(self, scans=None, **kws):
        """ get a map composed of many scans repeated at different position of a given motor

        Parameters
        ----------
        scans : scans to load in the map [string]
                the format of the string is intended to be parsed by '_str2rng()'
        **kws : see get_scan() method

        Returns
        -------
        xcol, ycol, zcol : 1D arrays representing the map
        """
        #get keywords arguments
        cntx = kws.get('cntx', self.cntx)
        cnty = kws.get('cnty', self.cnty)
        csig = kws.get('csig', self.csig)
        cmon = kws.get('cmon', self.cmon)
        csec = kws.get('csec', self.csec)
        norm = kws.get('norm', self.norm)
        #check inputs - some already checked in get_scan()
        if scans is None:
            raise NameError("Provide a string representing the scans to load in the map - e.g. '100, 7:15, 50:90:3'")
        if cnty is None:
            raise NameError("Provide the name of an existing motor")

        _counter = 0
        for scan in _str2rng(scans):
            x, z, moty = self.get_scan(scan=scan, cntx=cntx, cnty=cnty, csig=csig, cmon=cmon, csec=csec, scnt=None, norm=norm)
            y = _mot2array(moty, x)
            print "Loading scan {0} into the map...".format(scan)
            if _counter == 0:
                xcol = x
                ycol = y
                zcol = z
            else:
                xcol = np.append(xcol, x)
                ycol = np.append(ycol, y)
                zcol = np.append(zcol, z)
            _counter += 1

        return xcol, ycol, zcol

    def grid_map(self, xcol, ycol, zcol, xystep=None):
        """ grid (X, Y, Z) 1D data on a 2D regular mesh

        Parameters
        ----------
        xcol, ycol, zcol : 1D arrays repesenting the map (z is the intensity)
        xystep : the step size of the XY grid

        Returns
        -------
        xgrid, ygrid : 1D arrays giving abscissa and ordinate of the map
        zz : 2D array with the gridded intensity map

        See also
        --------
        - MultipleScanToMeshPlugin in PyMca
        """
        try:
            from matplotlib.mlab import griddata
        except ImportError:
            print "Error: cannot load griddata -- Matplotlib broken?"
        if xystep is None:
            xystep = 0.05
            warnings.warn("'xystep' not given: using a default value of {0}".format(xystep))
        #create the XY meshgrid and interpolate the Z on the grid
        print "Gridding data..."
        xgrid = np.linspace(xcol.min(), xcol.max(), (xcol.max()-xcol.min())/xystep)
        ygrid = np.linspace(ycol.min(), ycol.max(), (ycol.max()-ycol.min())/xystep)
        xx, yy = np.meshgrid(xgrid, ygrid)
        zz = griddata(xcol, ycol, zcol, xx, yy)

        return xgrid, ygrid, zz

    def get_mrg(self, scans=None, **kws):
        """ get a merged scan (average of many scans)

        Parameters
        ----------
        scans : scans to load in the merge [string]
                the format of the string is intended to be parsed by '_str2rng()'
        **kws : see get_scan() method

        Returns
        -------
        xmrg, zmrg : 1D arrays
        """
        #get keywords arguments
        cntx = kws.get('cntx', self.cntx)
        cnty = kws.get('cnty', self.cnty)
        csig = kws.get('csig', self.csig)
        cmon = kws.get('cmon', self.cmon)
        csec = kws.get('csec', self.csec)
        norm = kws.get('norm', self.norm)
        #check inputs - some already checked in get_scan()
        if scans is None:
            raise NameError("Provide a string representing the scans to merge - e.g. '100, 7:15, 50:90:3'")

        _ct = 0
        xdats = []
        zdats = []
        #mdats = []
        #idats = []
        for scan in _str2rng(scans):
            _x, _z, _m, _i = self.get_scan(scan=scan, cntx=cntx, cnty=None, csig=csig, cmon=cmon, csec=csec, scnt=None, norm=norm)
            xdats.append(_x)
            zdats.append(_z)
            #mdats.append(_m)
            #idats.append(_i)
            print "Loading scan {0}...".format(scan)
            _ct += 1

        return _pymca_average(xdats, zdats)

### LARCH ###
def spec_getscan2group(fname, scan=None, cntx=None, csig=None, cmon=None, csec=None, scnt=None, norm=None, _larch=None):
    """simple mapping of SpecfileData.get_scan() to larch groups"""
    if _larch is None:
        raise Warning("larch broken?")

    s = SpecfileData(fname)
    group = _larch.symtable.create_group()
    group.__name__ = 'SPEC data file %s' % fname
    x, y, motors, infos = s.get_scan(scan=scan, cntx=cntx, csig=csig, cmon=cmon, csec=csec, scnt=scnt, norm=norm)
    setattr(group, 'x', x)
    setattr(group, 'y', y)
    setattr(group, 'motors', motors)
    setattr(group, 'infos', infos)

    return group

def spec_getmap2group(fname, scans=None, cntx=None, cnty=None, csig=None, cmon=None, csec=None, xystep=None, norm=None, _larch=None):
    """simple mapping of SpecfileData.get_map() to larch groups"""
    if _larch is None:
        raise Warning("larch broken?")

    s = SpecfileData(fname)
    group = _larch.symtable.create_group()
    group.__name__ = 'SPEC data file %s' % fname
    xcol, ycol, zcol = s.get_map(scans=scans, cntx=cntx, cnty=cnty, csig=csig, cmon=cmon, csec=csec, norm=norm)
    x, y, zz = s.grid_map(xcol, ycol, zcol, xystep=xystep)
    setattr(group, 'x', x)
    setattr(group, 'y', y)
    setattr(group, 'zz', zz)

    return group

def spec_getmrg2group(fname, scans=None, cntx=None, csig=None, cmon=None, csec=None, norm=None, _larch=None):
    """simple mapping of SpecfileData.get_mrg() to larch groups"""
    if _larch is None:
        raise Warning("larch broken?")

    s = SpecfileData(fname)
    group = _larch.symtable.create_group()
    group.__name__ = 'SPEC data file {0}; Merged scans {1}'.format(fname, scans)
    xmrg, ymrg = s.get_mrg(scans=scans, cntx=cntx, csig=csig, cmon=cmon, csec=csec, norm=norm)
    setattr(group, 'xmrg', xmrg)
    setattr(group, 'ymrg', ymrg)

    return group

def str2rng(rngstr, _larch=None):
    """larch equivalent of _str2rng()"""
    if _larch is None:
        raise Warning("larch broken?")
    return _str2rng(rngstr)

def registerLarchPlugin():
    return ('_io', {'read_specfile_scan': spec_getscan2group,
                    'read_specfile_map' : spec_getmap2group,
                    'read_specfile_mrg' : spec_getmrg2group,
                    'str2rng' : str2rng
                    })

### TESTS ###
def test01():
    """ test get_scan method """
    fname = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'specfile_test.dat')
    signal = 'zap_det_dtc'
    monitor = 'arr_I02sum'
    seconds = 'arr_seconds'
    counter = 'arr_hdh_ene'
    motor = 'Spec.Energy'
    motor_counter = 'arr_xes_en'
    scan = 3
    t = SpecfileData(fname)
    for norm in [None, "area", "max-min", "sum"]:
        x, y, motors, infos = t.get_scan(scan, cntx=counter, csig=signal, cmon=monitor, csec=seconds, norm=norm)
        print "Read scan {0} with normalization {1}".format(scan, norm)
        import matplotlib.pyplot as plt
        plt.ion()
        plt.figure(num=test01.__doc__)
        plt.plot(x, y)
        plt.xlabel(infos["xlabel"])
        plt.ylabel(infos["ylabel"])
        plt.show()
        raw_input("Press Enter to close the plot window and continue...")
        plt.close()

def test02(nlevels, norm):
    """ test get_map method """
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    fname = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'specfile_test.dat')
    rngstr = '5:70'
    counter = 'arr_hdh_ene'
    motor = 'Spec.Energy'
    motor_counter = 'arr_xes_en'
    signal = 'zap_det_dtc'
    monitor = 'arr_I02sum'
    seconds = 'arr_seconds'
    xystep = 0.05
    t = SpecfileData(fname)
    xcol, ycol, zcol = t.get_map(scans=rngstr, cntx=counter, cnty=motor, csig=signal, cmon=monitor, csec=seconds, norm=norm)
    etcol = xcol-ycol
    x, y, zz = t.grid_map(xcol, ycol, zcol, xystep=xystep)
    ex, et, ezz = t.grid_map(xcol, etcol, zcol, xystep=xystep)
    fig = plt.figure(num=test02.__doc__)
    ax = fig.add_subplot(121)
    ax.set_title('gridded data')
    cax = ax.contourf(x, y, zz, nlevels, cmap=cm.Paired_r)
    ax = fig.add_subplot(122)
    ax.set_title('energy transfer')
    cax = ax.contourf(ex, et, ezz, nlevels, cmap=cm.Paired_r)
    cbar = fig.colorbar(cax)
    plt.show()
    raw_input("Press Enter to close the plot and continue...")
    plt.close()

def test03():
    """ test get_mrg method """
    fname = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'specfile_test.dat')
    signal = 'zap_det_dtc'
    monitor = 'arr_I02sum'
    seconds = 'arr_seconds'
    counter = 'arr_hdh_ene'
    motor = 'Spec.Energy'
    motor_counter = 'arr_xes_en'
    scans = '72, 74'
    t = SpecfileData(fname)
    for norm in [None, "area", "max-min", "sum"]:
        x, y = t.get_mrg(scans, cntx=counter, csig=signal, cmon=monitor, csec=seconds, norm=norm)
        print "Merged scans '{0}' with normalization {1}".format(scans, norm)
        import matplotlib.pyplot as plt
        plt.ion()
        plt.figure(num=test03.__doc__)
        plt.plot(x, y)
        plt.xlabel(counter)
        plt.ylabel("merged with norm {0}".format(norm))
        plt.show()
        raw_input("Press Enter to continue...")
        plt.close()

if __name__ == '__main__':
    """ to run some tests/examples on this class, uncomment the following """
    #test01()
    #test02(100, 'area')
    #test03
    pass


