#!/usr/bin/env python
import time
from datetime import datetime
from collections import OrderedDict
from gzip import GzipFile
import io
import copy
import json
import cchardet
import numpy as np

from .paths import uname, bindir, nativepath, unixpath, get_homedir, get_cwd
from .debugtime import debugtime, debugtimer

from .strutils import (fixName, isValidName, isNumber, bytes2str, str2bytes,
                       fix_varname, isLiteralStr, strip_comments, asfloat,
                       find_delims, version_ge, unique_name, get_sessionid)

from .shellutils import (_copy, _deepcopy, _more, _parent,
                         _ls, _cd, _cwd, _mkdir)

def is_gzip(filename):
    "is a file gzipped?"
    with open(filename, 'rb') as fh:
        return fh.read(3) == b'\x1f\x8b\x08'
    return False

def read_textfile(filename, size=None):
    """read text from a file as string

    Argument
    --------
    filename  (str or file): name of file to read or file-like object
    size  (int or None): number of bytes to read

    Returns
    -------
    text of file as string.

    Notes
    ------
    1. unicode encoding is detected with chardet and then
       used to decode bytes read from file.
    2. line endings are normalized to be '\n', so that
       splitting on '\n' will give a list of lines.
    3. if filename is given, it can be a gzip-compressed file
    """

    def decode(bdat):
        info = cchardet.detect(bdat)
        return bdat.decode(info.get('encoding', 'utf-8'))

    text = ''
    if isinstance(filename, io.IOBase):
        if filename.mode == 'r':
            text = filename.read(size)
        elif filename.mode == 'rb':
            text = decode(filename.read(size))
    else:
        fopen = GzipFile if is_gzip(filename) else open
        with fopen(filename, 'rb') as fh:
            text = decode(fh.read(size))

    return text.replace('\r\n', '\n').replace('\r', '\n')


def group2dict(group, _larch=None):
    "return dictionary of group members"
    return group.__dict__

def dict2group(d, _larch=None):
    "return group created from a dictionary"
    from larch import Group
    return Group(**d)

def copy_group(group, _larch=None):
    from larch import Group
    out = Group(datatype=getattr(group, 'datatype', 'unknown'),
                copied_from=getattr(group, 'groupname', repr(group)))

    class NoCopy:
        c = 'no copy'

    for attr in dir(group):
        val = NoCopy
        try:
            val = copy.deepcopy(getattr(group, attr))
        except ValueError:
            try:
                val = copy.copy(getattr(group, attr))
            except:
                val = NoCopy

        if val != NoCopy:
            setattr(out, attr, val)
    return out

def copy_xafs_group(group, _larch=None):
    """specialized group copy for XAFS data groups"""
    from larch import Group
    out = Group(datatype=getattr(group, 'datatype', 'unknown'),
                copied_from=getattr(group, 'groupname', repr(group)))

    for attr in dir(group):
        do_copy = True
        if attr in ('xdat', 'ydat', 'i0', 'data' 'yerr',
                    'energy', 'mu'):
            val = getattr(group, attr)*1.0
        elif attr in ('norm', 'flat', 'deriv', 'deconv',
                      'post_edge', 'pre_edge', 'norm_mback',
                      'norm_vict', 'norm_poly'):
            do_copy = False
        else:
            try:
                val = copy.deepcopy(getattr(group, attr))
            except ValueError:
                do_copy = False
        if do_copy:
            setattr(out, attr, val)
    return out


def isotime(t=None, with_tzone=False, filename=False):
    if t is None:
        t = time.time()
    sout = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    if with_tzone:
        sout = "%s-%2.2i:00" % (sout, time.timezone/3600)
    if filename:
        sout = sout.replace(' ', '_').replace(':', '')
    return sout

def time_ago(timestamp, precision=2):
    """
    give a human-readable 'time ago' from the timestamp.

    The output gives day, hours, minutes, seconds:
       52 days, 1 hour

    the `precision` field gives the number of significant time units to
    show.  This defaults to 2:
       'N days, H hours',
       'N hours, M minutes'
    """
    def format(x, unit):
        return "%d %s%s" % (x, unit, "s" if x > 1 else "")

    tdiff = datetime.now() - datetime.fromtimestamp(timestamp)
    days = tdiff.days
    hours = tdiff.seconds//3600
    minutes = tdiff.seconds%3600//60
    seconds = tdiff.seconds%3600%60

    out = []
    if days > 0:
        out.append(format(days, "day"))
    if hours > 0:
        out.append(format(hours, "hour"))
    if minutes > 0:
        out.append(format(minutes, "minute"))
    out.append(format(seconds, "second"))
    return ", ".join(out[:precision])

def json_dump(data, filename):
    """
    dump object or group to file using json
    """
    from .jsonutils import encode4js
    with open(filename, 'w') as fh:
        fh.write(json.dumps(encode4js(data)))
        fh.write('\n')

def json_load(filename):
    """
    load object from json dump file
    """
    from .jsonutils import decode4js
    with open(filename, 'rb') as fh:
        data = fh.read().decode('utf-8')
    return decode4js(json.loads(data))

def _larch_init(_larch):
    """initialize xrf"""
    from ..symboltable import Group
    _larch.symtable._sys.display = Group(use_color=True,
                                         colors=dict(text={'color': 'black'},
                                                     text2={'color': 'blue'},
                                                     error={'color': 'red'}))

_larch_builtins = dict(copy=_copy, deepcopy=_deepcopy, more= _more,
                       parent=_parent, ls=_ls, mkdir=_mkdir, cd=_cd,
                       cwd=_cwd, group2dict=group2dict,
                       copy_group=copy_group, copy_xafs_group=copy_xafs_group,
                       dict2group=dict2group, debugtimer=debugtimer,
                       isotime=isotime, json_dump=json_dump,
                       json_load=json_load)
