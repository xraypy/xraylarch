#!/usr/bin/env python
import time
from datetime import datetime
from collections import OrderedDict
from .paths import uname, nativepath, get_homedir
from .debugtime import debugtime, debugtimer
from .closure import Closure

from .strutils import (fixName, isValidName, isNumber, bytes2str,
                       fix_varname, isLiteralStr, strip_comments,
                       find_delims, version_ge)

from .shellutils import (_copy, _deepcopy, _more, _parent,
                         _ls, _cd, cwd, _mkdir)

from .show import (show, show_tree, get, get_termcolor_opts,
                   group2dict, dict2group)

def isotime(t=None, with_tzone=False):
    if t is None:
        t = time.time()
    sout = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    if with_tzone:
        sout = "%s-%2.2i:00" % (sout, time.timezone/3600)
    return sout
