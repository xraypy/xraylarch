#!/usr/bin/env python
"""
Code to write and read CVS files

"""
import sys
import os
import time
import json
import platform

from collections import OrderedDict

import numpy as np
from larch import Group
from larch.utils.mathutils import interp
from larch.utils.strutils import bytes2str, fix_varname

if sys.version[0] == '2':
    from string import maketrans
else:
    maketrans = str.maketrans

def groups2csv(grouplist, filename,
               x='energy', y='norm', _larch=None):
    """save data from a list of groups to a CSV file

    Arguments
    ---------
    grouplist  list of groups to save arrays from
    filname    name of output file
    x          name of group member to use for `x`
    y          name of group member to use for `y`

    """
    def get_label(grp):
        'get label for group'
        for attr in ('filename', 'label', 'name', 'file', '__name__'):
            o = getattr(grp, attr, None)
            if o is not None:
                return o
        return repr(o)

    ngroups = len(grouplist)
    x0 = getattr(grouplist[0], x)
    npts = len(x0)
    columns = [x0, getattr(grouplist[0], y)]
    labels = [x, get_label(grouplist[0]) ]

    for g in grouplist[1:]:

        labels.append(get_label(g))
        _x = getattr(g, x)
        _y = getattr(g, y)

        if ((len(_x) != npts) or (abs(_x -x0)).sum() > 1.0):
            columns.append(interp(_x, _y, x0))
        else:
            columns.append(_y)

    buff = ["# %s" % ', '.join(labels)]
    for i in range(npts):
        buff.append(', '.join(["%.6f" % s[i] for s in columns]))

    buff.append('')
    with open(filename, 'w') as fh:
        fh.write("\n".join(buff))

    print("Wrote %i groups to %s" % (len(columns)-1, filename))

def registerLarchPlugin():
    return ('_io', {'groups2csv': groups2csv})
