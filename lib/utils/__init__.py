#!/usr/bin/env python
try:
    from collections import OrderedDict
except ImportError:
    try:
        from .ordereddict import OrderedDict
    except:
        pass
from .paths import nativepath, get_homedir
from .closure import Closure
from .debugtime import debugtime
from .strutils import (fixName, isValidName, isNumber,
                      isLiteralStr, strip_comments, find_delims)
