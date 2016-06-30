#!/usr/bin/env python
__date__    = '20-June-2016'
__version__ = '0.9.29'

import sys
import numpy
import scipy
import matplotlib

try:
    import wx
    wxversion = wx.__version__
except:
    wxversion = 'not available'

def make_banner(extra=None):
    lines = ('=' * 72)
    fmt = """Larch %s (%s) M. Newville and Larch Development Team
Using Python %s,
Numpy %s, scipy %s, matplotlib %s, and wxpython %s"""

    banner = fmt % (__version__, __date__, sys.version,
                    numpy.__version__, scipy.__version__,
                    matplotlib.__version__, wxversion)
    if extra is not None:
        banner = "%s\n%s" % (banner, extra)
    return "%s\n%s\n%s\n" % (lines, banner, lines)
