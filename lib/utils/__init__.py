#!/usr/bin/env python
from collections import OrderedDict
from .paths import nativepath, get_homedir
from .closure import Closure
from .debugtime import debugtime
from .strutils import (fixName, isValidName, isNumber, bytes2str,
                      isLiteralStr, strip_comments, find_delims)
