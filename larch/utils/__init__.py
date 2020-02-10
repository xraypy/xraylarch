#!/usr/bin/env python
import time
from datetime import datetime
from collections import OrderedDict
import numpy as np
import copy
import json

from .paths import uname, bindir, nativepath, get_homedir
from .debugtime import debugtime, debugtimer

from .strutils import (fixName, isValidName, isNumber, bytes2str,
                       fix_varname, isLiteralStr, strip_comments,
                       find_delims, version_ge, unique_name)

from .shellutils import (_copy, _deepcopy, _more, _parent,
                         _ls, _cd, _cwd, _mkdir)


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
   

def isotime(t=None, with_tzone=False):
    if t is None:
        t = time.time()
    sout = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    if with_tzone:
        sout = "%s-%2.2i:00" % (sout, time.timezone/3600)
    return sout

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
    with open(filename, 'r') as fh:
        data = fh.read()
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
