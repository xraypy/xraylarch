#!/usr/bin/env python
__date__    = '2017-Apr-3'
__version__ = '0.9.33'

import sys
import numpy
import scipy
import matplotlib

try:
    import wx
    wxversion = wx.__version__
except:
    wxversion = 'not available'

def make_banner():
    lines = '=' * 78
    banner = """%s
Larch %s (%s) M. Newville, M. Koker, B. Ravel, and others
Python %s,
numpy %s, scipy %s, matplotlib %s, wxpython %s
%s
"""

    return banner % (lines, __version__, __date__, sys.version,
                    numpy.__version__, scipy.__version__,
                    matplotlib.__version__, wxversion, lines)
