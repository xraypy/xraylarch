
import json
import time
import numpy as np

from collections import OrderedDict

from larch import Group
from ..fitting import Parameter, isParameter
from ..utils.jsonutils import encode4js, decode4js
from . import fix_varname


def save(fname,  *args, **kws):
    """save groups and data into a portable json file

    save(fname, arg1, arg2, ....)

    Parameters
    ----------
       fname   name of output save file.
       args    list of groups, data items to be saved.

    See Also:  restore()
    """
    _larch = kws.get('_larch', None)
    isgroup =  _larch.symtable.isgroup

    expr = getattr(_larch, 'this_expr', 'save(foo)')
    expr = expr.replace('\n', ' ').replace('\r', ' ')

    grouplist = _larch.symtable._sys.saverestore_groups[:]

    buff = ["#Larch Save File: 1.0",
            "#save.date: %s" % time.strftime('%Y-%m-%d %H:%M:%S'),
            "#save.command: %s" % expr,
            "#save.nitems:  %i" % len(args)]

    names = []
    if expr.startswith('save('):
        names = [a.strip() for a in expr[5:-1].split(',')]
    try:
        names.pop(0)
    except:
        pass
    if len(names) < len(args):
        names.extend(["_unknown_"]*(len(args) - len(names)))

    for name, arg in zip(names, args):
        buff.append("#=> %s" % name)
        buff.append(json.dumps(encode4js(arg, grouplist=grouplist)))
    buff.append("")
    with open(fname, "w") as fh:
        fh.write("\n".join(buff))



def restore(fname, top_level=True, _larch=None):
    """restore data from a json Larch save file

    Arguments
    ---------
    top_level  bool  whether to restore to _main [True]


    Returns
    -------
    None   with `top_level=True` or group with `top_level=False`

    Notes
    -----
    1.  With top_level=False, a new group containing the
        recovered data will be returned.
    """

    grouplist = _larch.symtable._sys.saverestore_groups

    datalines = open(fname, 'r').readlines()
    line1 = datalines.pop(0)
    if not line1.startswith("#Larch Save File:"):
        raise ValueError("%s is not a valid Larch save file" % fname)
    version_string = line1.split(':')[1].strip()
    version_info = [s for s in version_string.split('.')]

    ivar = 0
    header = {'version': version_info}
    varnames = []
    gname = fix_varname('restore_%s' % fname)
    out = Group(name=gname)
    for line in datalines:
        line = line[:-1]
        if line.startswith('#save.'):
            key, value = line[6:].split(':', 1)
            value = value.strip()
            if key == 'nitems': value = int(value)
            header[key] = value
        elif line.startswith('#=>'):
            name = fix_varname(line[4:].strip())
            ivar += 1
            if name in (None, 'None', '__unknown__') or name in varnames:
                name = 'var_%5.5i' % (ivar)
            varnames.append(name)
        else:
            val = decode4js(json.loads(line), grouplist)
            setattr(out, varnames[-1], val)
    setattr(out, '_restore_metadata_', header)

    if top_level:
        _main = _larch.symtable
        for objname in dir(out):
            setattr(_main, objname, getattr(out, objname))
        return
    return out
