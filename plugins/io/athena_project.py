#!/usr/bin/env python
"""
Code to read (and write) Athena Project files

"""
import sys
import os
import time
import json
import platform
from fnmatch import fnmatch
from  gzip import GzipFile
from glob import glob

from collections import OrderedDict

import numpy as np
from numpy.random import randint
from larch import Group
from larch import __version__ as larch_version
from larch.utils.strutils import bytes2str, str2bytes, fix_varname

if sys.version[0] == '2':
    from string import maketrans
else:
    maketrans = str.maketrans

alist2json = maketrans("();'\n", "[] \" ")
def perl2json(text):
    return json.loads(text.split('=')[1].strip().translate(alist2json))


ERR_MSG = "Error reading Athena Project File"

def is_athena_project(filename):
    """tests whether file is a valid Athena Project file"""
    result = False
    if os.path.exists(filename):
        try:
            fh = GzipFile(filename)
            line1 = bytes2str(fh.readline())
            result = "Athena project file -- Demeter version" in line1
        except:
            pass
        finally:
            fh.close()
    return result


def make_hashkey():
    """generate an 'athena hash key': 5 random lower-case letters
    """
    a = []
    for i in range(5):
        a.append(chr(randint(97, 122)))
    return ''.join(a)


def make_athena_args(group, hashkey=None):
    """make athena args line from a group"""
    # start with default args:
    from larch_plugins.xafs.xafsutils import etok

    if hashkey is None:
        hashkey = make_hashkey()
    args = {}
    for k, v in (('annotation', ''), ('beamline', ''),
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
                 ('xdifile', ''), ('xmu_string', '')):
        args[k] = v


    args['datagroup'] = args['tag'] = hashkey
    args['source'] = args['file'] = getattr(group, 'filename', 'unknown')
    args['label'] = getattr(group, 'filename', hashkey)
    # args['titles'] = []


    en = getattr(group, 'energy', [])
    args['npts'] = len(en)
    if len(en) > 0:
        args['xmin'] = '%.1f' % min(en)
        args['xmax'] = '%.1f' % max(en)

    args['bkg_e0'] = group.e0
    args['bkg_step'] = args['bkg_fitted_step'] = group.edge_step

    args['bkg_nnorm'] = int(group.pre_edge_details.nnorm)
    args['bkg_nor1'] = group.pre_edge_details.norm1
    args['bkg_nor2'] = group.pre_edge_details.norm2
    args['bkg_pre1'] = group.pre_edge_details.pre1
    args['bkg_pre2'] = group.pre_edge_details.pre2

    emax = max(group.energy) - group.e0
    args['bkg_spl1e'] = '0'
    args['bkg_spl2e'] = '%.5f' % emax
    args['bkg_spl1'] = '0'
    args['bkg_spl2'] = '%.5f' % etok(emax)

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


class AthenaProject(object):
    """emulate an Athena Project file, especially for writing
    Note that read_athena() is currently separate and able to read
    from Athena Project to Python/Larch arrays just fine.
    """

    def __init__(self, filename='athena_larch.prj', _larch=None):
        self.groups = OrderedDict()
        self.filename = filename
        self._larch = _larch

    def add_group(self, group, label=None, signal=None):
        """add Larch group (presumably XAFS data) to Athena project"""

        from larch_plugins.xafs import pre_edge
        from larch_plugins.xray.xraydb_plugin import guess_edge

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

        hashkey = make_hashkey()
        while hashkey in self.groups:
            hashkey = make_hashkey()

        # fill in data from pre-edge subtraction
        if not (hasattr(group, 'e0') and hasattr(group, 'edge_step')):
            pre_edge(group, _larch=self._larch)
        args = make_athena_args(group, hashkey)
        _elem, _edge = guess_edge(group.e0, _larch=self._larch)
        args['bkg_z'] = _elem
        self.groups[hashkey] = Group(args=args, x=x, y=y, i0=i0, signal=signal)


    def save(self, filename=None, use_gzip=True):
        if filename is not None:
            self.filename = filename
        # print(" Writing Athena Project ", self.filename)
        iso_now = time.strftime('%Y-%m-%dT%H:%M:%S')
        pyosversion = "Python %s on %s"  % (platform.python_version(),
                                            platform.platform())

        buff = ["# Athena project file -- Demeter version 0.9.24",
                "# This file created at %s" % iso_now,
                "# Using Larch version %s, %s" % (larch_version, pyosversion)]

        for key, dat in self.groups.items():
            buff.append("")
            buff.append("$old_group = '%s';" % key)
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

def create_athena(filename=None, _larch=None):
    """create athena project file"""
    return AthenaProject(filename=filename, _larch=_larch)

def read_athena(filename, match=None, do_preedge=True, do_bkg=True,
                do_fft=True, use_hashkey=False, with_journal=True, _larch=None):
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
        with_journal (bool): whether to read Athena's journal, and
                       save it to `_athena_journal` [True]

    Returns:
        group of groups each named according the label used by Athena.

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
    from larch_plugins.xafs import pre_edge, autobk, xftf

    if not os.path.exists(filename):
        raise IOError("%s '%s': cannot find file" % (ERR_MSG, filename))

    try:
        fh = GzipFile(filename)
        lines = [bytes2str(t) for t in fh.readlines()]
        fh.close()
    except:
        raise ValueError("%s '%s': invalid gzip file" % (ERR_MSG, filename))

    athenagroups = []
    dat = {'name':''}
    Athena_version  = None
    vline = lines.pop(0)
    if  "Athena project file -- Demeter version" not in vline:
        raise ValueError("%s '%s': invalid Athena File" % (ERR_MSG, filename))

    major, minor, fix = '0', '0', '0'
    try:
        vs = vline.split("Athena project file -- Demeter version")[1]
        major, minor, fix = vs.split('.')
    except:
        raise ValueError("%s '%s': cannot read version" % (ERR_MSG, filename))
    if int(minor) < 9 or int(fix[:2]) < 21:
        raise ValueError("%s '%s': file is too old to read" % (ERR_MSG, filename))
    journal = {}
    for t in lines:
        if t.startswith('#') or len(t) < 2 or 'undef' in t:
            continue
        key = t.split(' ')[0].strip()
        key = key.replace('$', '').replace('@', '')
        # print(" group ", dat['name'], key, dat.keys())
        if key == 'old_group':
            dat['name'] = perl2json(t)
        elif key == '[record]':
            athenagroups.append(dat)
            dat = {'name':''}
        elif key == 'journal':
            journal = perl2json(t)
        elif key == 'args':
            dat['args'] = perl2json(t)
        elif key in ('x', 'y', 'i0', 'signal', 'stddev'):
            dat[key] = np.array([float(x) for x in perl2json(t)])
        elif key == '1;': # end of list
            pass
        else:
            print(" do not know what to do with key ", key, dat['name'])
    if match is not None:
        match = match.lower()

    out = Group()
    out.__doc__ = """XAFS Data from Athena Project File %s""" % (filename)
    if with_journal:
        out._athena_journal = journal

    for dat in athenagroups:
        label = dat.get('name', 'unknown')
        this = Group(athena_id=label, energy=dat['x'], mu=dat['y'],
                     bkg_params=Group(), fft_params = Group(),
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
                    setattr(this.bkg_params, key[4:], val)
                elif key.startswith('fft_'):
                    setattr(this.fft_params, key[4:], val)
                elif key == 'label':
                    this.label = val
                    if not use_hashkey:
                        label = this.label
                else:
                    setattr(this.athena_params, key, val)
        this.__doc__ = """Athena Group Name %s (key='%s')""" % (label, dat['name'])
        olabel = fix_varname(label)
        if match is not None:
            if not fnmatch(olabel.lower(), match):
                continue

        if do_preedge or do_bkg:
            pars = this.bkg_params
            pre_edge(this, _larch=_larch, e0=float(pars.e0),
                     pre1=float(pars.pre1), pre2=float(pars.pre2),
                     norm1=float(pars.nor1), norm2=float(pars.nor2),
                     nnorm=float(pars.nnorm)-1,
                     make_flat=bool(pars.flatten))

            if do_bkg and hasattr(pars, 'rbkg'):
                autobk(this, _larch=_larch, e0=float(pars.e0),
                       rbkg=float(pars.rbkg), kmin=float(pars.spl1),
                       kmax=float(pars.spl2), kweight=float(pars.kw),
                       dk=float(pars.dk), clamp_lo=float(pars.clamp1),
                       clamp_hi=float(pars.clamp2))

        if do_fft:
            pars = this.fft_params
            kweight=2
            if hasattr(pars, 'kw'):
                kweight = float(pars.kw)
            xftf(this, _larch=_larch, kmin=float(pars.kmin),
                 kmax=float(pars.kmax), kweight=kweight,
                 window=pars.kwindow, dk=float(pars.dk))

        setattr(out, olabel, this)
    return out

def registerLarchPlugin():
    return ('_io', {'read_athena': read_athena,
                    'create_athena': create_athena,
                    })
