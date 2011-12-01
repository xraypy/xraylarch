#!/usr/bin/env python
"""
Read/Write XAS Data Interchange Format for Python
"""
import re
import math
import time
import warnings
from string import printable as PRINTABLE

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

RAD2DEG  = 180.0/math.pi
# from NIST.GOV CODATA:
# Planck constant over 2 pi times c: 197.3269718 (0.0000044) MeV fm
PLANCK_hc = 1973.269718 * 2 * math.pi # hc in eV * Ang = 12398.4193

##
## Dictionary of XDI terms -- Python Version
## Most data is actually given as json strings

ENERGY_UNITS = ('eV', 'keV', 'GeV')
ANGLE_UNITS = ('deg', 'rad')
COLUMN_NAMES = ('energy', 'angle', 'k', 'chi', 'i0', 'time',
		'itrans', 'ifluor', 'irefer',
		'mutrans', 'mufluor', 'murefer',
		'normtrans', 'normfluor', 'normrefer')

XRAY_EDGES = ('K', 'L3', 'L2', 'L1', 'M4,5', 'M3', 'N', 'O')

ATOM_SYMS = ('H ', 'He', 'Li', 'Be', 'B ', 'C ', 'N ', 'O ', 'F ', 'Ne',
             'Na', 'Mg', 'Al', 'Si', 'P ', 'S ', 'Cl', 'Ar', 'K ', 'Ca',
             'Sc', 'Ti', 'V ', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
             'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y ', 'Zr',
             'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
             'Sb', 'Te', 'I ', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
             'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
             'Lu', 'Hf', 'Ta', 'W ', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
             'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
             'Pa', 'U ', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm',
             'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds',
             'Rg', 'Cn', 'Uut', 'Uuq', 'Uup', 'Uuh', 'Uus', 'Uuo')

######
##  Classes are broken here into a 2-level heierarchy:  Family.Member
##    Families have a name and a dictionary of Members
##    Members have a name and a pair of values:
##        type information
##        description
##   The member type information is of the form <TYPE> or <TYPE(UNITS)>
##   where TYPE is one of
##        str, int, float, datetime, atom_sym, xray_edge
##   str:       general string
##   int:       integer, unitless
##   float:     floating point number, with implied units as specified
##   datetime:  an ISO-structured datetime string
##   atom_sym:  two character symbol for element
##   xray_edge: standard symbol for absorption edge

CLASSES = {"facility": {"name":  ["<str>", "name of facility / storage ring"],
                        "energy": ["<float>", "stored beam energy, GeV"],
                        "current": ["<float>", "stored beam current, mA"],
                        "xray_source": ["<str>", "description of x-ray source"],
                        "critical_energy": ["<float>", "critical x-ray energy of source, keV"],
                        },
	   "beamline": {"name":  ["<str>", "name of beamline"],
                        "focussing": ["<str>", "describe focussing"],
                        "collimation": ["<str>", "describe x-ray beam collimation"],
                        "harmonic_rejection": ["<str>", "describe harmonic rejection scheme"],
                        },
	   "mono":     {"name":  ["<str>", "name of monochromator"],
                        "dspacing": ["<float>", "d spacing, Angstroms"],
                        "cooling": ["<str>", "describe cooling scheme"],
                        },
	   "scan":    {"mode": ["<str>", "describe scan mode"],
                       "element": ["<atom_sym>", "atomic symbol of element being scanned"],
                       "edge": ["<xray_edge>",   "edge being scanned"],
                       "start_time": ["<datetime>", "scan start time"],
                       "stop_time": ["<datetime>", "scan stop time"],
                       "n_regiions": ["<int>", "number of scan regions for segmented step scan"],
                       },
	   "detectors": {"i0": ["<str>", "describe I0 detector"],
                         "itrans": ["<str>", "describe transmission detector"],
                         "ifluor": ["<str>", "describe fluorescence detector"],
                         "irefer": ["<str>", "describe reference sample detector and scheme"],
                         },
	   "sample":  {"name": ["<str>", "describe sample"],
                       "formula": ["<str>", "sample formula"],
                       "preparation": ["<str>", "describe sample prepation"],
                       "reference": ["<str>", "describe reference sample"]},
           }


DATETIME = r'(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{1,2}):(\d{1,2})$'


MATCH = {'word': re.compile(r'[a-zA-Z0-9_]+$').match,
         'properword': re.compile(r'[a-zA-Z_][a-zA-Z0-9_-]*$').match,
         'datetime': re.compile(DATETIME).match
         }

def validate_datetime(txt):
    "validate allowed datetimes"
    return MATCH['datetime'](txt)

def validate_int(txt):
    "validate for int"
    try:
        int(txt)
        return True
    except ValueError:
        return False

def validate_float_or_nan(txt):
    "validate for float, with nan, inf"
    try:
        return (txt.lower() == 'nan' or
                txt.lower() == 'inf' or
                float(txt))
    except ValueError:
        return False

def validate_float(txt):
    "validate for float"
    try:
        float(txt)
        return True
    except ValueError:
        return False

def validate_xrayedge(txt):
    "validate x-ray edge"
    return txt.upper() in XRAY_EDGES

def validate_atomsym(txt):
    "validate for atomic symbols"
    return txt.title() in ATOM_SYMS

def validate_properword(txt):
    "validate for words"
    return  MATCH['properword'](txt)

def validate_printable(txt):
    "validate for printable string"
    return all([c in PRINTABLE for c in txt])

def validate_columnname(txt):
    "validate for string"
    return txt.lower() in COLUMN_NAMES


VALIDATORS = {'str': validate_printable,
              'int': validate_int,
              'float': validate_float,
              'column_name': validate_columnname,
              'xray_edge': validate_xrayedge,
              'atom_sym': validate_atomsym,
              'datetime': validate_datetime,
              'float_or_nan': validate_float_or_nan,
              'word': validate_properword,
              }

def validate(value, dtype):
    if dtype.startswith('<') and dtype.endswith('>'):
        dtype = dtype[1:-1]
    return VALIDATORS[dtype](value)
              

def strip_comment(txt):
    """remove leading comment character
    returns IsCommentLine, stripped comment-removed text
    """
    isComment = False
    if txt[0] in '#;*%C!$*/':
        isComment = True
        txt = txt[1:]
    return isComment, txt.strip()

class XDIFileException(Exception):
    """XDI File Exception: General Errors"""
    def __init__(self, msg, **kws):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg

class XDIFileWarning(Warning):
    """XDI File Warning: Non-fatal non-conforming formatting"""
    def __init__(self, msg, **kws):
        Warning.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg

class XDIFile(object):
    """ XAS Data Interchange Format:

    See https://github.com/XraySpectrscopy/XAS-Data-Interchange

    for further details

    >>> xdi_file = XDFIile(filename)

    Principle data members:
      columns:  dict of column indices, with keys
                       'energy', 'i0', 'itrans', 'ifluor', 'irefer'
                       'mutrans', 'mufluor', 'murefer'
                 some of which may be None.
      column_data: dict of data for arrays -- same keys as
                 for columns.
    Principle methods:
      read():     read XDI data file, set column data and attributes
      write(filename):  write xdi_file data to an XDI file.

    """
    _invalid_msg = "invalid data for '%s':  was expecting %s, got '%s'"

    def __init__(self, filename=None):
        self.filename = filename
        self.app_info =  {'pylib': '1.0.0'}
        self.comments = []
        self.rawdata = []
        self.column_labels = {}
        self.column_attrs = {}
        self.file_version = None
        self._lineno  = 0
        self._text = ''
        self.labels = []
        self.attrs = {}

        if self.filename:
            self.read(self.filename)

    def _error(self, msg, with_line=True):
        "wrapper for raising an XDIFile Exception"
        msg = '%s: %s' % (self.filename, msg)
        if with_line:
            msg = "%s (line %i)\n   %s" % (msg, self._lineno+1,
                                           self._text[self._lineno])
        raise XDIFileException(msg)

    def _warn(self, msg, with_line=True):
        "wrapper for raising an XDIFile Exception"
        msg = '%s: %s' % (self.filename, msg)
        if with_line:
            msg = "%s (line %i)\n   %s" % (msg, self._lineno+1,
                                           self._text[self._lineno])
        print msg

    def write(self, filename):
        "write out an XDI File"

#         if self.columns['energy'] is None:
#             self._error("cannot write datafile '%s': No data to write" % filename)
# 
#         print self.app_attrs['pylib'].keys()
# 
#         topline = "# XDI/1.0"
#         if self.app_info is not None:
#             app_strings = []
#             for app, version in self.app_info.items():
#                 app_strings.append("%s/%s" % (app.upper(), version))
# 
#             topline = "%s %s" % (topline, ' '.join(app_strings))
#         buff = [topline]
#         labels = []
#         icol = 0
#         for attrib in COLUMN_NAMES:
#             if self.column_data[attrib] is not None:
#                 icol = icol + 1
#                 buff.append('# Column_%s: %i' % (attrib, icol))
#                 labels.append(attrib)
# 
#         buff.append('# Abscissa: $1')
#         for attrib in sorted(DEFINED_FIELDS):
#             if attrib.startswith('abscissa'):
#                 continue
#             if self.attrs.get(attrib, None) is not None:
#                 buff.append("# %s: %s" % (attrib.title(),
#                                           str(self.attrs[attrib])))
# 
#         for app in sorted(self.app_attrs):
#             for key in sorted(self.app_attrs[app]):
#                 value = str(self.app_attrs[app][key])
#                 label = '%s_%s' % (app, key)
#                 buff.append("# %s: %s" % (label.title(), value))
# 
#         buff.append('# ///')
#         for cline in self.comments:
#             buff.append("# %s" % cline)
# 
#         buff.append('#----')
#         buff.append('# %s' % ' '.join(labels))
#         for idx in range(len(self.column_data['energy'])):
#             dat = []
#             for lab in labels:
#                 dat.append(str(self.column_data[lab][idx]))
#             buff.append("  %s" % '  '.join(dat))
# 
#         fout = open(filename, 'w')
#         fout.writelines(('%s\n' % l for l in buff))
#         fout.close()
# 
    def read(self, filename=None):
        """read validate and parse an XDI datafile into python structures
        """
        if filename is None and self.filename is not None:
            filename = self.filename

        text  = self._text = open(filename, 'r').readlines()
        iscomm, line0 = strip_comment(text[0])
        if not (iscomm and line0.startswith('XDI/')):
            self._error('is not a valid XDI File.', with_line=False)

        self.file_version, other = line0[4:].split(' ', 1)
        self.app_info.update(dict([o.split('/') for o in other.split()]))

        ncols = -1
        state = 'HEADER'
        self._lineno = 0     

        for line in text[1:]:
            iscomm, line = strip_comment(line)
            self._lineno += 1
            if len(line) < 1:
                continue

            # determine state: HEADER, COMMENT, LABELS, DATA
            if line.startswith('//'):
                state = 'COMMENTS'
                continue
            elif line.startswith('----'):
                state = 'LABELS'
                continue
            elif not iscomm:
                state = 'DATA'
            elif not state in ('COMMENTS', 'LABELS'):
                state = 'HEADER'

            # act on STATE
            if state == 'COMMENTS':
                if not validate(line, 'str'):
                    self._error('invalid comment')
                self.comments.append(line)
            elif state == 'LABELS':
                self.labels = line.split()
                for lab in self.labels:
                    if not validate(lab, 'word'):
                        self._error("invalid column label")
                state = 'DATA'
            elif state == 'DATA':
                dat = line.split()
                if len(self.rawdata) == 0:
                    ncols = len(dat)
                elif len(dat) != ncols:
                    self._error("inconsistent number of data points")
                try:
                    [validate(i, 'float_or_nan') for i in dat]
                    self.rawdata.append([float(d) for d in dat])
                except ValueError:
                    self._warn("non-numeric data in uncommented line")
                    continue
            elif state == 'HEADER':
                try:
                    field, value = [i.strip() for i in line.split(':', 1)]
                except ValueError:
                    self._warn("unknown header line")                
                field = field.lower().replace('-','_')
                try:
                    family, member = field.split('.', 1)
                except ValueError:
                    family, member = field, '_'
                    
                if family == 'column':
                    words = value.split(' ', 1)
                    if not (validate(member, 'int') and
                            validate(words[0], 'column_name')):
                        msg = self._invalid_msg % ('%s.%s' % (family,member),
                                                   'column_name', words[0])
                        self._error(msg)
                    self.column_labels[int(member)] = words[0]
                    if len(words) > 1:
                        self.column_attrs[int(member)] = words[1]
                else:
                    validator, desc = 'str', ''
                    if family in CLASSES:
                        if member in CLASSES[family]:
                            validator, desc = CLASSES[family][member]
                    if family not in self.attrs:
                        self.attrs[family] = {}
                    words = value.split(' ', 1)
                    if not validate(words[0], validator):
                        msg = self._invalid_msg % ('%s.%s' % (family,member),
                                                   validator, words[0])
                        self._error(msg)
                    if member in self.attrs[family]:
                        value = "%s %s" % (self.attrs[family][member],value)
                    self.attrs[family][member] = value

        self._assign_arrays()
        self._text = None

    def _assign_arrays(self):
        """assign data arrays for principle data attributes:
           energy, angle, i0, itrans, ifluor, irefer,
           mutrans, mufluor, murefer, etc.
        """
        xunits = 'eV'
        xname = None
        ix = -1
        if HAS_NUMPY:
            self.rawdata = np.array(self.rawdata)
            exp = np.exp
            log = np.log
            sin = np.log
            asin = np.arcsin

        for idx, name in self.column_labels.items():
            if HAS_NUMPY:
                dat = self.rawdata[:,int(idx)-1]
            else:
                dat = [d[idx-1] for d in self.rawdata]
            setattr(self, name, dat)                
            if name in ('energy', 'angle'):
                ix = idx
                xname = name
                units = self.column_attrs.get(idx, None)
                if units is not None:
                    xunits = units

        if not HAS_NUMPY:
            self._warn('not calculating derived values -- install numpy!',
                       with_line=False)
            return
        
        # convert energy to angle, or vice versa
        if ix > 0 and 'd_spacing' in self.attrs['mono']:
            dspace = float(self.attrs['mono']['d_spacing'])
            omega = PLANCK_hc/(2*dspace)
            if xname == 'energy' and not hasattr(self, 'angle'):
                energy_ev = self.energy
                if xunits.lower() == 'kev':
                    energy_ev = 1000. * energy_ev
                self.angle = RAD2DEG * asin(omega/energy_ev)
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


def xdigroup(fname, larch=None):
    """simple mapping of XDI file to larch groups"""
    x = XDIFile(fname)
    if larch is None:
        raise Warning("cannot read xdigroup -- larch broken?")
        
    group = larch.symtable.new_group(name='XDI file %s' % fname)
    for key, val in x.__dict__.items():
        setattr(group, key, val)
    return group

def registerLarchPlugin():
    return ('_io', {'xdigroup': xdigroup})
