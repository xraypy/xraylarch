#!/usr/bin/env python
"""
Read/Write XAS Data Interchange Format for Python
"""
import os
from ctypes import c_long, c_double, c_char_p, c_void_p, pointer, Structure
import six

__version__ = '1.2.0larch'

from numpy import array, exp, log, sin, arcsin

from larch import ValidateLarchPlugin
from larch.larchlib import get_dll
from larch_plugins.xray import RAD2DEG, PLANCK_HC

class XDIFileStruct(Structure):
    "emulate XDI File"
    _fields_ = [('nmetadata',     c_long),
                ('narrays',       c_long),
                ('npts',          c_long),
                ('narray_labels', c_long),
                ('nouter',        c_long),
                ('error_lineno',  c_long),
                ('dspacing',      c_double),
                ('xdi_libversion',c_char_p),
                ('xdi_version',   c_char_p),
                ('extra_version', c_char_p),
                ('filename',      c_char_p),
                ('element',       c_char_p),
                ('edge',          c_char_p),
                ('comments',      c_char_p),
                ('error_line',    c_char_p),
                ('error_message', c_char_p),
                ('array_labels',  c_void_p),
                ('outer_label',   c_char_p),
                ('array_units',   c_void_p),
                ('meta_families', c_void_p),
                ('meta_keywords', c_void_p),
                ('meta_values',   c_void_p),
                ('array',         c_void_p),
                ('outer_array',   c_void_p),
                ('outer_breakpts', c_void_p)]

string_attrs = ('comments', 'edge', 'element', 'error_line',
                'error_message', 'extra_version', 'filename',
                'outer_label', 'xdi_libversion', 'xdi_pyversion',
                'xdi_version')

def Py2tostr(val):
    return str(val)

def Py2tostrlist(address, nitems):
    return [str(i) for i in (nitems*c_char_p).from_address(address)]

def Py3tostr(val):
    if isinstance(val, str):
        return val
    if isinstance(val, bytes):
        return str(val, 'latin_1')
    return str(val)

def Py3tostrlist(address, nitems):
    return [str(i, 'ASCII') for i in (nitems*c_char_p).from_address(address)]

tostr  = Py2tostr
tostrlist = Py2tostrlist
if six.PY3:
    tostr = Py3tostr
    tostrlist = Py3tostrlist

def add_dot2path():
    """add this folder to begninng of PATH environmental variable"""
    sep = ':'
    if os.name == 'nt': sep = ';'
    paths = os.environ.get('PATH','').split(sep)
    paths.insert(0, os.path.abspath(os.curdir))
    os.environ['PATH'] = sep.join(paths)


XDILIB = None
def get_xdilib():
    """make initial connection to XDI dll"""
    global XDILIB
    if XDILIB is None:
        XDILIB = get_dll('xdifile')
        XDILIB.XDI_errorstring.restype   = c_char_p
    return XDILIB

class XDIFileException(Exception):
    """XDI File Exception: General Errors"""
    def __init__(self, msg, **kws):
        Exception.__init__(self)
        self.msg = msg
    def __str__(self):
        return self.msg

class XDIFile(object):
    """ XAS Data Interchange Format:

    See https://github.com/XraySpectrscopy/XAS-Data-Interchange

    for further details

    >>> xdi_file = XDFIile(filename)

    Principle methods:
      read():     read XDI data file, set column data and attributes
      write(filename):  write xdi_file data to an XDI file.
    """
    _invalid_msg = "invalid data for '%s':  was expecting %s, got '%s'"

    def __init__(self, filename=None):
        self.filename = filename
        self.xdi_pyversion =  __version__
        self.xdilib = get_xdilib()
        self.comments = []
        self.rawdata = []
        self.attrs = {}
        self.status = None
        if self.filename:
            self.read(self.filename)

    def write(self, filename):
        "write out an XDI File"
        print( 'Writing XDI file not currently supported')

    def read(self, filename=None):
        """read validate and parse an XDI datafile into python structures
        """
        if filename is None and self.filename is not None:
            filename = self.filename
        filename = six.b(filename)
        pxdi = pointer(XDIFileStruct())
        self.status = out = self.xdilib.XDI_readfile(filename, pxdi)
        if out < 0:
            msg =  self.xdilib.XDI_errorstring(out)
            self.xdilib.XDI_cleanup(pxdi, out)
            msg = 'Error reading XDIFile %s\n%s' % (filename, msg)
            raise XDIFileException(msg)

        xdi = pxdi.contents
        for attr in dict(xdi._fields_):
            setattr(self, attr, getattr(xdi, attr))
        self.array_labels = tostrlist(xdi.array_labels, self.narrays)
        arr_units         = tostrlist(xdi.array_units, self.narrays)
        self.array_units  = []
        self.array_addrs  = []
        for unit in arr_units:
            addr = ''
            if '||' in unit:
                unit, addr = [x.strip() for x in unit.split('||', 1)]
            self.array_units.append(unit)
            self.array_addrs.append(addr)

        mfams = tostrlist(xdi.meta_families, self.nmetadata)
        mkeys = tostrlist(xdi.meta_keywords, self.nmetadata)
        mvals = tostrlist(xdi.meta_values,   self.nmetadata)
        self.attrs = {}
        for fam, key, val in zip(mfams, mkeys, mvals):
            fam = fam.lower()
            key = key.lower()
            if fam not in self.attrs:
                self.attrs[fam] = {}
            self.attrs[fam][key] = val

        parrays = (xdi.narrays*c_void_p).from_address(xdi.array)[:]
        rawdata = [(xdi.npts*c_double).from_address(p)[:] for p in parrays]

        nout = xdi.nouter
        outer, breaks = [], []
        if nout > 1:
            outer  = (nout*c_double).from_address(xdi.outer_array)[:]
            breaks = (nout*c_long).from_address(xdi.outer_breakpts)[:]
        for attr in ('outer_array', 'outer_breakpts', 'nouter'):
            delattr(self, attr)
        self.outer_array    = array(outer)
        self.outer_breakpts = array(breaks)


        rawdata = array(rawdata)
        rawdata.shape = (self.narrays, self.npts)
        self.rawdata = rawdata
        self._assign_arrays()
        for attr in ('nmetadata', 'narray_labels', 'meta_families',
                     'meta_keywords', 'meta_values', 'array'):
            delattr(self, attr)
        self.xdilib.XDI_cleanup(pxdi, 0)

    def _assign_arrays(self):
        """assign data arrays for principle data attributes:
           energy, angle, i0, itrans, ifluor, irefer,
           mutrans, mufluor, murefer, etc.  """

        xunits = 'eV'
        xname = None
        ix = -1
        self.rawdata = array(self.rawdata)

        for idx, name in enumerate(self.array_labels):
            dat = self.rawdata[idx,:]
            setattr(self, name, dat)
            if name in ('energy', 'angle'):
                ix = idx
                xname = name
                units = self.array_units[idx]
                if units is not None:
                    xunits = units

        # convert energy to angle, or vice versa
        monodat = {}
        if 'mono' in  self.attrs:
            monodat = self.attrs['mono']
        elif 'monochromator' in  self.attrs:
            monodat = self.attrs['monochromator']

        if ix >= 0 and 'd_spacing' in monodat:
            dspace = float(monodat['d_spacing'])
            if dspace < 0: dspace = 0.001
            omega = PLANCK_HC/(2*dspace)
            if xname == 'energy' and not hasattr(self, 'angle'):
                energy_ev = self.energy
                if xunits.lower() == 'kev':
                    energy_ev = 1000. * energy_ev
                self.angle = RAD2DEG * arcsin(omega/energy_ev)
            elif xname == 'angle' and not hasattr(self, 'energy'):
                angle_rad = self.angle
                if xunits.lower() in ('deg', 'degrees'):
                    angle_rad = angle_rad / RAD2DEG
                self.energy = omega/sin(angle_rad)

        if hasattr(self, 'i0'):
            if hasattr(self, 'itrans') and not hasattr(self, 'mutrans'):
                self.mutrans = -log(self.itrans / (self.i0+1.e-12))
            elif hasattr(self, 'mutrans') and not hasattr(self, 'itrans'):
                self.itrans  =  self.i0 * exp(-self.mutrans)
            if hasattr(self, 'ifluor') and not hasattr(self, 'mufluor'):
                self.mufluor = self.ifluor/(self.i0+1.e-12)

            elif hasattr(self, 'mufluor') and not hasattr(self, 'ifluor'):
                self.ifluor =  self.i0 * self.mufluor

        if hasattr(self, 'itrans'):
            if hasattr(self, 'irefer') and not hasattr(self, 'murefer'):
                self.murefer = -log(self.irefer / (self.itrans+1.e-12))

            elif hasattr(self, 'murefer') and not hasattr(self, 'irefer'):
                self.irefer = self.itrans * exp(-self.murefer)

@ValidateLarchPlugin
def read_xdi(fname, _larch=None):
    """simple mapping of XDI file to larch groups"""
    x = XDIFile(fname)
    group = _larch.symtable.create_group()
    for key, val in x.__dict__.items():
        if not key.startswith('_'):
            if six.PY3 and key in string_attrs:
                val = tostr(val)
            setattr(group, key, val)
    group.__name__ ='XDI file %s' % fname
    doc = ['%i arrays, %i npts' % (x.narrays, x.npts)]
    arr_labels = getattr(x, 'array_labels', None)
    if arr_labels is not None:
        doc.append("Array Labels: %s" % repr(arr_labels))
    group.__doc__ = '\n'.join(doc)
    return group

def registerLarchPlugin():
    return ('_io', {'read_xdi': read_xdi})
