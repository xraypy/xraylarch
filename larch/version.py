#!/usr/bin/env python
__date__    = '2019-March-6'
__version__ = '0.9.43a'

import sys
import numpy
import scipy
import matplotlib
import lmfit

try:
    import wx
except:
    wx = None

def make_banner():
    authors = "M. Newville, M. Koker, B. Ravel, and others"
    sysvers = sys.version
    if '\n' in sysvers:
        sysvers = sysvers.split('\n')[0]


    lines = ["Larch %s (%s) %s" % (__version__, __date__, authors),
             "Python: %s" % (sysvers)]

    reqs = []
    for mod in (numpy, scipy, matplotlib, lmfit, wx):
        if mod is not None:
            try:
                vers = "%s %s" % (mod.__name__, mod.__version__)
            except:
                vers = "%s not available" % (mod.__name__)
            reqs.append(vers)
    lines.append(', '.join(reqs))

    linelen = max([len(line) for line in lines])
    border = '='*min(linelen, 75)
    lines.insert(0, border)
    lines.append(border)

    return '\n'.join(lines)
