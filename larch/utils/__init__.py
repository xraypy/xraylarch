#!/usr/bin/env python
import time
from datetime import datetime
from collections import OrderedDict

from .paths import uname, nativepath, get_homedir
from .debugtime import debugtime, debugtimer

from .strutils import (fixName, isValidName, isNumber, bytes2str,
                       fix_varname, isLiteralStr, strip_comments,
                       find_delims, version_ge)

from .shellutils import (_copy, _deepcopy, _more, _parent,
                         _ls, _cd, _cwd, _mkdir)

def group2dict(group, _larch=None):
    "return dictionary of group members"
    return group.__dict__

def dict2group(d, _larch=None):
    "return group created from a dictionary"
    return Group(**d)

def isotime(t=None, with_tzone=False):
    if t is None:
        t = time.time()
    sout = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    if with_tzone:
        sout = "%s-%2.2i:00" % (sout, time.timezone/3600)
    return sout

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
                       dict2group=dict2group, debugtimer=debugtimer,
                       isotime=isotime)
