#!/usr/bin/env python
__date__    = '2019-Jun-30'
__version__ = '0.9.45'
__authors__ = "M. Newville, M. Koker, B. Ravel, and others"

import sys
import numpy
import scipy
import matplotlib
import lmfit
from collections import OrderedDict

def version_data(mods=None):
    sysvers = sys.version
    if '\n' in sysvers:
        sysvers = sysvers.split('\n')[0]

    vdat = OrderedDict()
    vdat['larch'] = "%s (%s) %s" % (__version__, __date__, __authors__)
    vdat['python'] = "%s" % (sysvers)

    allmods = [numpy, scipy, matplotlib, lmfit]
    if mods is not None:
        for m in mods:
            if m not in allmods:
                allmods.append(m)

    for mod in allmods:
        if mod is not None:
            mname = mod.__name__
            try:
                vers = mod.__version__
            except:
                vers = "unavailable"
            vdat[mname] = vers
    return vdat

def make_banner(mods=None):
    vdat = version_data(mods=mods)

    lines = ['Larch %s' % vdat.pop('larch'),
             'Python %s' % vdat.pop('python')]

    reqs = []
    for name, vstr in vdat.items():
        reqs.append('%s %s' % (name, vstr))
    lines.append(', '.join(reqs))

    linelen = max([len(line) for line in lines])
    border = '='*max(linelen, 75)
    lines.insert(0, border)
    lines.append(border)

    return '\n'.join(lines)
