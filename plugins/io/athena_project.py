#!/usr/bin/env python
"""
Code to read (and write) Athena Project files

"""
import sys
import os
import json
from fnmatch import fnmatch
from  gzip import GzipFile
from glob import glob

import numpy as np
from larch import Group
from larch.utils.strutils import bytes2str
from larch_plugins.io import fix_varname

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

def read_athena(filename, match=None, do_preedge=True,
                do_bkg=True, do_fft=True, use_hashkey=False, _larch=None):
    """read athena project file
    returns a Group of Groups, one for each Athena Group in the project file

    Arguments:
        filename (string): name of Athena Project file
        match (sring): pattern to use to limit imported groups (see Note 1)
        do_preedge (bool): whether to do pre-edge subtraction [True]
        do_bkg (bool): whether to do XAFS background subtraction [True]
        do_fft (bool): whether to do XAFS Fast Fourier transform [True]
        use_hashkey (bool): whether to use Athena's hash key as the
                       group name instead of the Athena label [False]

    Returns:
        group of groups each named according the label used by Athena.

    Notes:
        1. To limit the imported groups, use the pattern in `match`,
           using '*' to match 'all' '?' to match any single character,
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

    for t in lines:
        if t.startswith('#') or len(t) < 2:
            continue
        key = t.split(' ')[0].strip()
        key = key.replace('$', '').replace('@', '')
        if key == 'old_group':
            dat['name'] = perl2json(t)
        elif key == '[record]':
            athenagroups.append(dat)
            dat = {'name':''}
        elif key == 'args':
            dat['args'] = perl2json(t)
        elif key in ('x', 'y', 'i0'):
            dat[key] = np.array([float(x) for x in perl2json(t)])

    if match is not None:
        match = match.lower()

    out = Group()
    out.__doc__ = """XAFS Data from Athena Project File %s""" % (filename)
    for dat in athenagroups:
        label = dat['name']
        this = Group(athena_id=label, energy=dat['x'], mu=dat['y'],
                     bkg_params=Group(), fft_params = Group(),
                     athena_params=Group())
        if 'i0' in dat:
            this.i0 = dat['i0']
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
    return ('_io', {'read_athena': read_athena})
