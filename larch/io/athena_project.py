#!/usr/bin/env python
"""
Code to read and write Athena Project files

"""

import os
import io
import sys
import time
import json
import platform
from fnmatch import fnmatch
from gzip import GzipFile
from collections import OrderedDict
from copy import deepcopy
import numpy as np
from numpy.random import randint

from larch import Group
from larch import __version__ as larch_version
from larch.utils.strutils import bytes2str, str2bytes, fix_varname
from xraydb import guess_edge
import asteval

hexopen = '\\x{'
hexclose = '}'

alist2json = str.maketrans("();'\n", "[] \" ")

def plarray2json(text):
    return json.loads(text.split('=', 1)[1].strip().translate(alist2json))

def parse_arglist(text):
    txt = text.split('=', 1)[1].strip()
    if txt.endswith(';'):
        txt = txt[:-1]
    return json.loads(txt.translate(alist2json))


def asfloat(x):
    """try to convert value to float, or fail gracefully"""
    try:
        return float(x)
    except (ValueError, TypeError):
        return x


ERR_MSG = "Error reading Athena Project File"


def _read_raw_athena(filename):
    """try to read athena project file as plain text,
    to determine validity
    """
    # try gzip
    text = None
    try:
        fh = GzipFile(filename)
        text = bytes2str(fh.read())
    except Exception:
        errtype, errval, errtb = sys.exc_info()
        text = None

    if text is None:
        # try plain text file
        try:
            fh = open(filename, 'r')
            text = bytes2str(fh.read())
        except Exception:
            errtype, errval, errtb = sys.exc_info()
            text = None

    return text


def _test_athena_text(text):
    return "Athena project file -- " in text[:500]


def is_athena_project(filename):
    """tests whether file is a valid Athena Project file"""
    text = _read_raw_athena(filename)
    if text is None:
        return False
    return _test_athena_text(text)


def make_hashkey(length=5):
    """generate an 'athena hash key': 5 random lower-case letters
    """
    return ''.join([chr(randint(97, 122)) for i in range(length)])

def make_athena_args(group, hashkey=None, **kws):
    """make athena args line from a group"""
    # start with default args:
    from larch.xafs.xafsutils import etok

    if hashkey is None:
        hashkey = make_hashkey()
    args = {}
    for k, v in (('annotation', ''),
                 ('beamline', ''),
                 ('beamline_identified', '0'), ('bft_dr', '0.0'),
                 ('bft_rmax', '3'), ('bft_rmin', '1'),
                 ('bft_rwindow', 'hanning'), ('bkg_algorithm', 'autobk'),
                 ('bkg_cl', '0'), ('bkg_clamp1', '0'), ('bkg_clamp2', '24'),
                 ('bkg_delta_eshift', '0'), ('bkg_dk', '1'),
                 ('bkg_e0_fraction', '0.5'), ('bkg_eshift', '0'),
                 ('bkg_fixstep', '0'), ('bkg_flatten', '1'),
                 ('bkg_former_e0', '0'), ('bkg_funnorm', '0'),
                 ('bkg_int', '7.'), ('bkg_kw', '1'),
                 ('bkg_kwindow', 'hanning'), ('bkg_nclamp', '5'),
                 ('bkg_rbkg', '1.0'), ('bkg_slope', '-0.0'),
                 ('bkg_stan', 'None'), ('bkg_tie_e0', '0'),
                 ('bkg_nc0', '0'), ('bkg_nc1', '0'),
                 ('bkg_nc2', '0'),  ('bkg_nc3', '0'),
                 ('bkg_rbkg', '1.0'), ('bkg_slope', '0'),
                 ('bkg_pre1', '-150'), ('bkg_pre2', '-30'),
                 ('bkg_nor1', '150'), ('bkg_nor2', '800'),
                 ('bkg_nnorm', '1'),
                 ('prjrecord', 'athena.prj, 1'),  ('chi_column', ''),
                 ('chi_string', ''), ('collided', '0'), ('columns', ''),
                 ('daq', ''), ('denominator', '1'), ('display', '0'),
                 ('energy', ''), ('energy_string', ''), ('epsk', ''),
                 ('epsr', ''), ('fft_dk', '4'), ('fft_edge', 'k'),
                 ('fft_kmax', '15.'), ('fft_kmin', '2.00'),
                 ('fft_kwindow', 'kaiser-bessel'), ('fft_pc', '0'),
                 ('fft_pcpathgroup', ''), ('fft_pctype', 'central'),
                 ('forcekey', '0'), ('from_athena', '1'),
                 ('from_yaml', '0'), ('frozen', '0'), ('generated', '0'),
                 ('i0_scale', '1'), ('i0_string', '1'),
                 ('importance', '1'), ('inv', '0'), ('is_col', '1'),
                 ('is_fit', '0'), ('is_kev', '0'), ('is_merge', ''),
                 ('is_nor', '0'), ('is_pixel', '0'), ('is_special', '0'),
                 ('is_xmu', '1'), ('ln', '0'), ('mark', '0'),
                 ('marked', '0'), ('maxk', '15'), ('merge_weight', '1'),
                 ('multiplier', '1'), ('nidp', '5'), ('nknots', '4'),
                 ('numerator', ''), ('plot_scale', '1'),
                 ('plot_yoffset', '0'), ('plotkey', ''),
                 ('plotspaces', 'any'), ('provenance', ''),
                 ('quenched', '0'), ('quickmerge', '0'),
                 ('read_as_raw', '0'), ('rebinned', '0'),
                 ('recommended_kmax', '1'), ('recordtype', 'mu(E)'),
                 ('referencegroup', ''), ('rmax_out', '10'),
                 ('signal_scale', '1'), ('signal_string', '-1'),
                 ('trouble', ''), ('tying', '0'),
                 ('unreadable', '0'), ('update_bft', '1'),
                 ('update_bkg', '1'), ('update_columns', '0'),
                 ('update_data', '0'), ('update_fft', '1'),
                 ('update_norm', '1'), ('xdi_will_be_cloned', '0'),
                 ('xdifile', ''), ('xmu_string', ''),
                 ('valence', ''), ('lasso_yvalue', ''),
                 ('atsym', ''), ('edge', '') ):
        args[k] = v

    args['datagroup'] = args['tag'] = args['label'] = hashkey
    en = getattr(group, 'energy', [])
    args['npts'] = len(en)
    if len(en) > 0:
        args['xmin'] = '%.1f' % min(en)
        args['xmax'] = '%.1f' % max(en)

    main_map = dict(source='filename', file='filename', label='filename',
                    bkg_e0='e0', bkg_step='edge_step',
                    bkg_fitted_step='edge_step', valence='valence',
                    lasso_yvalue='lasso_yvalue', atsym='atsym',
                    edge='edge')

    for aname, lname in main_map.items():
        val = getattr(group, lname, None)
        if val is not None:
            args[aname] = val

    bkg_map = dict(nnorm='nnorm', nor1='norm1', nor2='norm2', pre1='pre1',
                   pre2='pre2')

    if hasattr(group, 'pre_edge_details'):
        for aname, lname in bkg_map.items():
            val = getattr(group.pre_edge_details, lname, None)
            if val is not None:
                args['bkg_%s' % aname] = val

    emax = max(group.energy) - group.e0
    args['bkg_spl1e'] = '0'
    args['bkg_spl2e'] = '%.5f' % emax
    args['bkg_spl1'] = '0'
    args['bkg_spl2'] = '%.5f' % etok(emax)

    autobk_details = getattr(group, 'autobk_details', None)
    autobk_args = getattr(autobk_details, 'call_args', None)
    if autobk_args is not None:
        args['bkg_rbkg'] = autobk_args['rbkg']
        args['bkg_spl1'] = autobk_args['kmin']
        args['bkg_spl2'] = autobk_args['kmax']
        args['bkg_kw'] = autobk_args['kweight']
        args['bkg_dk'] = autobk_args['dk']
        args['bkg_kwindow'] = autobk_args['win']
        args['bkg_nclamp'] = autobk_args['nclamp']
        args['bkg_clamp1'] = autobk_args['clamp_lo']
        args['bkg_clamp2'] = autobk_args['clamp_hi']

    xftf_details = getattr(group, 'xftf_details', None)
    xftf_args = getattr(xftf_details, 'call_args', None)
    if xftf_args is not None:
        args['fft_kmin'] = xftf_args['kmin']
        args['fft_kmax'] = xftf_args['kmax']
        args['fft_kw'] = xftf_args['kweight']
        args['fft_dk'] = xftf_args['dk']
        args['fft_kwindow'] = xftf_args['window']
    args.update(kws)
    return args


def athena_array(group, arrname):
    """convert ndarray to athena representation"""
    arr = getattr(group, arrname, None)
    if arr is None:
        return None
    return arr # json.dumps([repr(i) for i in arr])
    # return "(%s)" % ','.join(["'%s'" % i for i in arr])


def format_dict(d):
    """ format dictionary for Athena Project file"""
    o = []
    for key in sorted(d.keys()):
        o.append("'%s'" % key)
        val = d[key]
        if val is None: val = ''
        o.append("'%s'" % val)
    return ','.join(o)

def format_array(arr):
    """ format dictionary for Athena Project file"""
    o = ["'%s'" % v for v in arr]
    return ','.join(o)

def clean_bkg_params(grp):
    grp.nnorm = getattr(grp, 'nnorm', 2)
    grp.e0   = getattr(grp, 'e0', -1)
    grp.rbkg = getattr(grp, 'rbkg', 1)
    grp.pre1 = getattr(grp, 'pre1', -150)
    grp.pre2 = getattr(grp, 'pre2',  -25)
    grp.nor1 = getattr(grp, 'nor1', 100)
    grp.nor2 = getattr(grp, 'nor2', 1200)
    grp.spl1 = getattr(grp, 'spl1', 0)
    grp.spl2 = getattr(grp, 'spl2', 30)
    grp.kw   = getattr(grp, 'kw', 1)
    grp.dk   = getattr(grp, 'dk', 3)
    grp.flatten  = getattr(grp, 'flatten', 0)
    if getattr(grp, 'kwindow', None) is None:
        grp.kwindow = getattr(grp, 'win', 'hanning')

    try:
        grp.clamp1 = float(grp.clamp1)
    except Exception:
        grp.clamp1 = 1
    try:
        grp.clamp2 = float(grp.clamp2)
    except Exception:
        grp.clamp2 = 1

    return grp


def clean_fft_params(grp):
    grp.kmin = getattr(grp, 'kmin', 0)
    grp.kmax = getattr(grp, 'kmax',  25)
    grp.kweight = getattr(grp, 'kweight',  2)
    grp.dk = getattr(grp, 'dk',  3)
    grp.kwindow = getattr(grp, 'kwindow',  'hanning')
    return grp


def text2list(text):
    key, txt = [a.strip() for a in text.split('=', 1)]
    if txt.endswith('\n'):
        txt = txt[:-1]
    if txt.endswith(';'):
        txt = txt[:-1]
    txt = txt.replace('=>', ':').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    # re-cast unicode stored by perl (\x{e34} -> 0xe4)
    if hexopen in txt:
        w = []
        k = 0
        for i in range(len(txt)-3):
            if txt[i:i+3] == hexopen:
                j = txt[i:i+8].find(hexclose)
                if j > 0:
                    w.extend((txt[k:i], chr(int('0x' + txt[i+3:i+j], base=16))))
                    k = i+j+1
        w.append(txt[k:])
        txt = ''.join(w)
    return txt


def parse_perlathena(text, filename):
    """
    parse old athena file format to Group of Groups
    """
    aout = io.StringIO()
    aeval = asteval.Interpreter(minimal=True, writer=aout, err_writer=aout)

    lines = text.split('\n')
    athenagroups = []
    raw = {'name':''}
    vline = lines.pop(0)
    if  "Athena project file -- " not in vline:
        raise ValueError("%s '%s': invalid Athena File" % (ERR_MSG, filename))
    major, minor, fix = '0', '0', '0'
    if 'Demeter' in vline:
        try:
            vs = vline.split("Athena project file -- Demeter version")[1]
            major, minor, fix = vs.split('.')
        except:
            raise ValueError("%s '%s': cannot read version" % (ERR_MSG, filename))
    else:
        try:
            vs = vline.split("Athena project file -- Athena version")[1]
            major, minor, fix = vs.split('.')
        except:
            raise ValueError("%s '%s': cannot read version" % (ERR_MSG, filename))

    header = [vline]
    journal = ['']
    is_header = True
    ix = 0
    for t in lines:
        ix += 1
        if t.startswith('#') or len(t) < 2 or 'undef' in t:
            if is_header:
                header.append(t)
            continue
        is_header = False
        key = t.split(' ')[0].strip()
        key = key.replace('$', '').replace('@', '').replace('%', '').strip()
        if key == 'old_group':
            raw['name'] = aeval(text2list(t))
        elif key == '[record]':
            athenagroups.append(raw)
            raw = {'name':''}
        elif key == 'journal':
            journal = aeval(text2list(t))
            if len(aeval.error) > 0:
                print(f" warning: could not read journal from '{filename:s}'")
                journal = ['']
        elif key == 'args':
            raw['args'] = aeval(text2list(t))
        elif key == 'xdi':
            raw['xdi'] = t
        elif key in ('x', 'y', 'i0', 'signal', 'stddev'):
            raw[key] = np.array([float(x) for x in aeval(text2list(t))])
        elif key in ('1;', 'indicator', 'lcf_data', 'plot_features'):
            pass
        else:
            print(" do not know what to do with key '%s' at '%s'" % (key, raw['name']))

    out = Group()
    out.__doc__ = """XAFS Data from Athena Project File %s""" % (filename)
    out.journal = '\n'.join(journal)
    out.group_names = []
    out.header = '\n'.join(header)
    for dat in athenagroups:
        label = dat.get('name', 'unknown')
        this = Group(athena_id=label, energy=dat['x'], mu=dat['y'],
                     bkg_params=Group(),
                     fft_params=Group(),
                     athena_params=Group())
        if 'i0' in dat:
            this.i0 = dat['i0']
        if 'signal' in dat:
            this.signal = dat['signal']
        if 'stddev' in dat:
            this.stddev = dat['stddev']
        if 'args' in dat:
            for i in range(len(dat['args'])//2):
                key = dat['args'][2*i]
                val = dat['args'][2*i+1]
                if key.startswith('bkg_'):
                    setattr(this.bkg_params, key[4:], asfloat(val))
                elif key.startswith('fft_'):
                    setattr(this.fft_params, key[4:], asfloat(val))
                elif key == 'label':
                    label = this.label = val
                elif key in ('valence', 'lasso_yvalue',
                             'epsk', 'epsr', 'importance'):
                    setattr(this, key, asfloat(val))
                elif key in ('atsym', 'edge', 'provenance'):
                    setattr(this, key, val)
                else:
                    setattr(this.athena_params, key, asfloat(val))
        this.__doc__ = """Athena Group Name %s (key='%s')""" % (label, dat['name'])
        name = fix_varname(label)
        if name.startswith('_'):
            name = 'd' + name
        setattr(out, name, this)
        out.group_names.append(name)
    return out


def parse_perlathena_old(text, filename):
    """
    parse old athena file format to Group of Groups
    """
    lines = text.split('\n')
    athenagroups = []
    raw = {'name':''}
    vline = lines.pop(0)
    if  "Athena project file -- " not in vline:
        raise ValueError("%s '%s': invalid Athena File" % (ERR_MSG, filename))
    major, minor, fix = '0', '0', '0'
    if 'Demeter' in vline:
        try:
            vs = vline.split("Athena project file -- Demeter version")[1]
            major, minor, fix = vs.split('.')
        except:
            raise ValueError("%s '%s': cannot read version" % (ERR_MSG, filename))
    else:
        try:
            vs = vline.split("Athena project file -- Athena version")[1]
            major, minor, fix = vs.split('.')
        except:
            raise ValueError("%s '%s': cannot read version" % (ERR_MSG, filename))

    header = [vline]
    journal = ['']
    is_header = True
    for t in lines:
        if t.startswith('#') or len(t) < 2 or 'undef' in t:
            if is_header:
                header.append(t)
            continue
        is_header = False
        key = t.split(' ')[0].strip()
        key = key.replace('$', '').replace('@', '').replace('%', '').strip()
        if key == 'old_group':
            raw['name'] = plarray2json(t)
        elif key == '[record]':
            athenagroups.append(raw)
            raw = {'name':''}
        elif key == 'journal':
            journal = parse_arglist(t)
        elif key == 'args':
            raw['args'] = parse_arglist(t)
        elif key == 'xdi':
            raw['xdi'] = t
        elif key in ('x', 'y', 'i0', 'signal', 'stddev'):
            raw[key] = np.array([float(x) for x in plarray2json(t)])
        elif key in ('1;', 'indicator', 'lcf_data', 'plot_features'):
            pass
        else:
            print(" do not know what to do with key '%s' at '%s'" % (key, raw['name']))

    out = Group()
    out.__doc__ = """XAFS Data from Athena Project File %s""" % (filename)
    out.journal = '\n'.join(journal)
    out.group_names = []
    out.header = '\n'.join(header)
    for dat in athenagroups:
        label = dat.get('name', 'unknown')
        this = Group(athena_id=label, energy=dat['x'], mu=dat['y'],
                     bkg_params=Group(),
                     fft_params=Group(),
                     athena_params=Group())
        if 'i0' in dat:
            this.i0 = dat['i0']
        if 'signal' in dat:
            this.signal = dat['signal']
        if 'stddev' in dat:
            this.stddev = dat['stddev']
        if 'args' in dat:
            for i in range(len(dat['args'])//2):
                key = dat['args'][2*i]
                val = dat['args'][2*i+1]
                if key.startswith('bkg_'):
                    setattr(this.bkg_params, key[4:], asfloat(val))
                elif key.startswith('fft_'):
                    setattr(this.fft_params, key[4:], asfloat(val))
                elif key == 'label':
                    label = this.label = val
                elif key in ('valence', 'lasso_yvalue',
                             'epsk', 'epsr', 'importance'):
                    setattr(this, key, asfloat(val))
                elif key in ('atsym', 'edge', 'provenance'):
                    setattr(this, key, val)
                else:
                    setattr(this.athena_params, key, asfloat(val))
        this.__doc__ = """Athena Group Name %s (key='%s')""" % (label, dat['name'])
        name = fix_varname(label)
        if name.startswith('_'):
            name = 'd' + name
        setattr(out, name, this)
        out.group_names.append(name)

    return out


def parse_jsonathena(text, filename):
    """parse a JSON-style athena file"""
    jsdict = json.loads(text)

    out = Group()
    out.__doc__ = """XAFS Data from Athena Project File %s""" % (filename)

    header = []
    athena_names = []
    for key, val in jsdict.items():
        if key.startswith('_____head'):
            header.append(val)
        elif key.startswith('_____journ'):
            journal = val
        elif key.startswith('_____order'):
            athena_names = val

    out.journal = journal
    out.header = '\n'.join(header)
    out.group_names  = []
    for name in athena_names:
        label = name
        dat = jsdict[name]
        x = np.array(dat['x'], dtype='float64')
        y = np.array(dat['y'], dtype='float64')
        this = Group(athena_id=name, energy=x, mu=y,
                     bkg_params=Group(),
                     fft_params=Group(),
                     athena_params=Group())
        if 'i0' in dat:
            this.i0 = np.array(dat['i0'], dtype='float64')
        if 'signal' in dat:
            this.signal = np.array(dat['signal'], dtype='float64')
        if 'stddev' in dat:
            this.stddev = np.array(dat['stddev'], dtype='float64')
        if 'args' in dat:
            for key, val in dat['args'].items():
                if key.startswith('bkg_'):
                    setattr(this.bkg_params, key[4:], asfloat(val))
                elif key.startswith('fft_'):
                    setattr(this.fft_params, key[4:], asfloat(val))
                elif key == 'label':
                    label = this.label = val
                else:
                    setattr(this.athena_params, key, asfloat(val))
        this.__doc__ = """Athena Group Name %s (key='%s')""" % (label, name)
        name = fix_varname(label)
        if name.startswith('_'):
            name = 'd' + name
        setattr(out, name, this)
        out.group_names.append(name)
    return out


class AthenaGroup(Group):
    """A special Group for handling datasets loaded from Athena project files"""

    def __init__(self, show_sel=False):
        """Constructor

        Parameters
        ----------

        show_sel : boolean, False
            if True, it shows the selection flag in HTML representation
        """
        super().__init__()
        self.show_sel = show_sel

    def _repr_html_(self):
        """HTML representation for Jupyter notebook"""

        _has_sel = any([hasattr(g, 'sel') for g in self.groups.values()])
        html = ["<table>"]
        html.append("<tr>")
        html.append("<td><b>Group</b></td>")
        if self.show_sel and _has_sel:
            html.append("<td><b>Sel</b></td>")
        html.append("</tr>")
        for name, grp in self.groups.items():
            try:
                if grp.sel == 1:
                    sel = "\u2714"
                else:
                    sel = ""
            except AttributeError:
                sel = ""
            html.append("<tr>")
            html.append(f"<td>{name}</td>")
            if self.show_sel and _has_sel:
                html.append(f"<td>{sel}</td>")
            html.append("</tr>")
        html.append("</table>")
        return ''.join(html)

    @property
    def groups(self):
        return self._athena_groups

    @groups.setter
    def groups(self, groups):
        self._athena_groups = groups


class AthenaProject(object):
    """read and write Athena Project files, mapping to Larch group
    containing sub-groups for each spectra / record

    note that two generations of Project files are supported for reading:

       1. Perl save file (custom format?)
       2. JSON format

    In addition, project files may be Gzipped or not.

    By default, files are saved in Gzipped JSON format
    """

    def __init__(self, filename=None, _larch=None):
        self._larch = _larch
        self.groups = OrderedDict()
        self.header = None
        self.journal = None
        self.filename = filename
        if filename is not None:
            if os.path.exists(filename) and is_athena_project(filename):
                self.read(filename)

    def add_group(self, group, signal=None):
        """add Larch group (presumably XAFS data) to Athena project"""
        from larch.xafs import pre_edge

        x = athena_array(group, 'energy')
        yname = None
        for _name in ('mu', 'mutrans', 'mufluor'):
            if hasattr(group, _name):
                yname = _name
                break
        if x is None or yname is None:
            raise ValueError("can only add XAFS data to Athena project")

        y  = athena_array(group, yname)
        i0 = athena_array(group, 'i0')
        if signal is not None:
            signal = athena_array(group, signal)
        elif yname in ('mu', 'mutrans'):
            sname = None
            for _name in ('i1', 'itrans'):
                if hasattr(group, _name):
                    sname = _name
                    break
            if sname is not None:
                signal = athena_array(group, sname)

        hashkey = getattr(group, 'athena_id', None)
        if hashkey is None or hashkey in self.groups:
            hashkey = make_hashkey()
            while hashkey in self.groups:
                hashkey = make_hashkey()

        # fill in data from pre-edge subtraction
        if not (hasattr(group, 'e0') and hasattr(group, 'edge_step')):
            pre_edge(group, _larch=self._larch)
        group.args = make_athena_args(group, hashkey)

        # fix parameters that are incompatible with athena
        group.args['bkg_nnorm'] = max(1, min(3, int(group.args['bkg_nnorm'])))

        _elem, _edge = guess_edge(group.e0)
        group.args['bkg_z'] = _elem
        group.x = x
        group.y = y
        group.i0 = i0
        group.signal = signal

        # add a selection flag
        group.sel = 1

        self.groups[hashkey] = group

    def save(self, filename=None, use_gzip=True):
        if filename is not None:
            self.filename = filename
        iso_now = time.strftime('%Y-%m-%dT%H:%M:%S')
        pyosversion = "Python %s on %s"  % (platform.python_version(),
                                            platform.platform())

        buff = ["# Athena project file -- Demeter version 0.9.24",
                "# This file created at %s" % iso_now,
                "# Using Larch version %s, %s" % (larch_version, pyosversion)]

        for key, dat in self.groups.items():
            if not hasattr(dat, 'args'):
                continue
            buff.append("")
            groupname = getattr(dat, 'groupname', key)

            buff.append("$old_group = '%s';" % groupname)
            buff.append("@args = (%s);" % format_dict(dat.args))
            buff.append("@x = (%s);" % format_array(dat.x))
            buff.append("@y = (%s);" % format_array(dat.y))
            if getattr(dat, 'i0', None) is not None:
                buff.append("@i0 = (%s);" % format_array(dat.i0))
            if getattr(dat, 'signal', None) is not None:
                buff.append("@signal = (%s);" % format_array(dat.signal))
            if getattr(dat, 'stddev', None) is not None:
                buff.append("@stddev = (%s);" % format_array(dat.stddev))
            buff.append("[record] # ")

        buff.extend(["", "@journal = {};", "", "1;", "", "",
                     "# Local Variables:", "# truncate-lines: t",
                     "# End:", ""])
        fopen =open
        if use_gzip:
            fopen = GzipFile
        fh = fopen(self.filename, 'w')
        fh.write(str2bytes("\n".join([bytes2str(t) for t in buff])))
        fh.close()

    def read(self, filename=None, match=None, do_preedge=True, do_bkg=True,
             do_fft=True, use_hashkey=False):
        """
        read Athena project to group of groups, one for each Athena dataset
        in the project file.  This supports both gzipped and unzipped files
        and old-style perl-like project files and new-style JSON project files

        Arguments:
            filename (string): name of Athena Project file
            match (string): pattern to use to limit imported groups (see Note 1)
            do_preedge (bool): whether to do pre-edge subtraction [True]
            do_bkg (bool): whether to do XAFS background subtraction [True]
            do_fft (bool): whether to do XAFS Fast Fourier transform [True]
            use_hashkey (bool): whether to use Athena's hash key as the
                           group name instead of the Athena label [False]
        Returns:
            None, fills in attributes `header`, `journal`, `filename`, `groups`

        Notes:
            1. To limit the imported groups, use the pattern in `match`,
               using '*' to match 'all', '?' to match any single character,
               or [sequence] to match any of a sequence of letters.  The match
               will always be insensitive to case.
            3. do_preedge,  do_bkg, and do_fft will attempt to reproduce the
               pre-edge, background subtraction, and FFT from Athena by using
               the parameters saved in the project file.
            2. use_hashkey=True will name groups from the internal 5 character
               string used by Athena, instead of the group label.

        Example:
            1. read in all groups from a project file:
               cr_data = read_athena('My Cr Project.prj')

            2. read in only the "merged" data from a Project, and don't do FFT:
               zn_data = read_athena('Zn on Stuff.prj', match='*merge*', do_fft=False)
        """
        if filename is not None:
            self.filename = filename
        if not os.path.exists(self.filename):
            raise IOError("%s '%s': cannot find file" % (ERR_MSG, self.filename))

        from larch.xafs import pre_edge, autobk, xftf

        if not os.path.exists(filename):
            raise IOError("file '%s' not found" % filename)

        text = _read_raw_athena(filename)
        # failed to read:
        if text is None:
            raise OSError("failed to read '%s'" % filename)
        if not _test_athena_text(text):
            raise ValueError("%s '%s': invalid Athena File" % (ERR_MSG, filename))

        # decode JSON or Perl format
        data = None
        if  '____header' in text[:500]:
            try:
                data = parse_jsonathena(text, self.filename)
            except Exception:
                pass

        if data is None:
            data = parse_perlathena(text, self.filename)

        if data is None:
            raise ValueError("cannot read file '%s' as Athena Project File" % (self.filename))

        self.header = data.header
        self.journal = data.journal
        self.group_names = data.group_names

        for gname in data.group_names:
            oname = gname
            if match is not None:
                if not fnmatch(gname.lower(), match):
                    continue
            this = getattr(data, gname)

            if use_hashkey:
                oname = this.athena_id
            is_xmu = bool(int(getattr(this.athena_params, 'is_xmu', 1.0)))
            is_chi = bool(int(getattr(this.athena_params, 'is_chi', 0.0)))
            is_xmu = is_xmu and not is_chi
            for aname in ('is_xmudat', 'is_bkg', 'is_diff',
                          'is_proj', 'is_pixel', 'is_rsp'):
                val = bool(int(getattr(this.athena_params, aname, 0.0)))
                is_xmu = is_xmu and not val

            if is_xmu and (do_preedge or do_bkg) and (self._larch is not None):
                pars = clean_bkg_params(this.bkg_params)
                pre_edge(this,  e0=float(pars.e0),
                         pre1=float(pars.pre1), pre2=float(pars.pre2),
                         norm1=float(pars.nor1), norm2=float(pars.nor2),
                         nnorm=float(pars.nnorm),
                         make_flat=bool(pars.flatten), _larch=self._larch)
                if do_bkg and hasattr(pars, 'rbkg'):
                    autobk(this, _larch=self._larch, e0=float(pars.e0),
                           rbkg=float(pars.rbkg), kmin=float(pars.spl1),
                           kmax=float(pars.spl2), kweight=float(pars.kw),
                           dk=float(pars.dk), clamp_lo=float(pars.clamp1),
                           clamp_hi=float(pars.clamp2))
                    if do_fft:
                        pars = clean_fft_params(this.fft_params)
                        kweight=2
                        if hasattr(pars, 'kw'):
                            kweight = float(pars.kw)
                        xftf(this, _larch=self._larch, kmin=float(pars.kmin),
                             kmax=float(pars.kmax), kweight=kweight,
                             window=pars.kwindow, dk=float(pars.dk))
            if is_chi:
                this.k = this.energy*1.0
                this.chi = this.mu*1.0
                del this.energy
                del this.mu

            # add a selection flag
            this.sel = 1

            self.groups[oname] = this

    def as_group(self):
        """convert AthenaProject to Larch group"""
        out = AthenaGroup()
        out.__doc__ = """XAFS Data from Athena Project File %s""" % (self.filename)
        out._athena_journal = self.journal
        out._athena_header = self.header
        out._athena_groups = self.groups

        for name, group in self.groups.items():
            setattr(out, name, group)
        return out

    def as_dict(self):
        """convert AthenaProject to a nested dictionary"""
        out = dict()
        out["_doc"] = """XAFS Data from Athena Project File %s""" % (self.filename)
        out["_journal"] = self.journal  # str
        out["_header"] = self.header  # str
        out["groups"] = dict()

        for name, group in self.groups.items():
            gdict = group.__dict__
            _ = gdict.pop("__name__")
            par_key = "_params"
            gout = deepcopy(gdict)
            gout[par_key] = dict()
            for subname, subgroup in gdict.items():
                if isinstance(subgroup, Group):
                    subdict = gout.pop(subname).__dict__
                    _ = subdict.pop("__name__")
                    par_name = subname.split(par_key)[0]  # group all paramters in common dictionary
                    gout[par_key][par_name] = subdict
            out["groups"][name] = gout

        return out


def read_athena(filename, match=None, do_preedge=True, do_bkg=True, do_fft=True,
                use_hashkey=False,  _larch=None):
    """read athena project file
    returns a Group of Groups, one for each Athena Group in the project file

    Arguments:
        filename (string): name of Athena Project file
        match (string): pattern to use to limit imported groups (see Note 1)
        do_preedge (bool): whether to do pre-edge subtraction [True]
        do_bkg (bool): whether to do XAFS background subtraction [True]
        do_fft (bool): whether to do XAFS Fast Fourier transform [True]
        use_hashkey (bool): whether to use Athena's hash key as the
                       group name instead of the Athena label [False]

    Returns:
        group of groups each named according the label used by Athena.

    Notes:
        1. To limit the imported groups, use the pattern in `match`,
           using '*' to match 'all', '?' to match any single character,
           or [sequence] to match any of a sequence of letters.  The match
           will always be insensitive to case.
        2. do_preedge,  do_bkg, and do_fft will attempt to reproduce the
           pre-edge, background subtraction, and FFT from Athena by using
           the parameters saved in the project file.
        3. use_hashkey=True will name groups from the internal 5 character
           string used by Athena, instead of the group label.

    Example:
        1. read in all groups from a project file:
           cr_data = read_athena('My Cr Project.prj')

        2. read in only the "merged" data from a Project, and don't do FFT:
           zn_data = read_athena('Zn on Stuff.prj', match='*merge*', do_fft=False)

    """
    if not os.path.exists(filename):
        raise IOError("%s '%s': cannot find file" % (ERR_MSG, filename))

    aprj = AthenaProject(_larch=_larch)
    aprj.read(filename, match=match, do_preedge=do_preedge, do_bkg=do_bkg,
              do_fft=do_fft, use_hashkey=use_hashkey)
    return aprj.as_group()


def create_athena(filename=None, _larch=None):
    """create athena project file"""
    return AthenaProject(filename=filename, _larch=_larch)


def extract_athenagroup(dgroup, _larch=None):
    '''extract xas group from athena group'''
    g = dgroup
    g.datatype = 'xas'
    g.filename = getattr(g, 'label', 'unknown')
    g.xdat = 1.0*g.energy
    g.ydat = 1.0*g.mu
    g.yerr = 1.0
    g.plot_xlabel = 'energy'
    g.plot_ylabel = 'mu'
    return g
#enddef
