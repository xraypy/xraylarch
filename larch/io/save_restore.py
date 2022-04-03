import json
import time
import numpy as np
import uuid, socket, platform

from gzip import GzipFile

from collections import OrderedDict

from larch import Group, __date__, __version__, __release_version__
from ..fitting import Parameter, isParameter
from ..utils.jsonutils import encode4js, decode4js
from ..utils.strutils import bytes2str, str2bytes, fix_varname

def get_machineid():
    "machine id / MAC address, independent of hostname"
    return hex(uuid.getnode())[2:]

def save_session(fname=None, _larch=None):
    """save all groups and data into a Larch Save File (.larix)
    A portable json file, that can be loaded with

    load_session(fname)

    Parameters
    ----------
    fname   name of output save file.

    See Also:  restore_session()
    """
    if fname is None:
        fname = time.strftime('%Y_%m_%d_%H%M')
    if not fname.endswith('.larix'):
        fname = fname + '.larix'

    if _larch is None:
        raise ValueError('_larch not defined')
    symtab = _larch.symtable
    buff = ["##LARIX: 1.0      Larch Session File",
            "##Date Saved: %s"   % time.strftime('%Y-%m-%d %H:%M:%S'),
            "##Larch Release Version: %s" % __release_version__,
            "##Larch Release Date: %s" % __date__,
            "##Larch Working Version: %s" % __version__,
            "##Python Version: %s" % platform.python_version(),
            "##Python Compiler: %s" % platform.python_compiler(),
            "##Python Implementation: %s" % platform.python_implementation(),
            "##Machine Platform: %s" % platform.system(),
            "##Machine Name: %s" % socket.gethostname(),
            "##Machine MACID: %s" % get_machineid(),
            "##Machine Version: %s"   % platform.version(),
            "##Machine Processor: %s" % platform.machine(),
            "##Machine Architecture: %s" % ':'.join(platform.architecture()),
            ]

    core_groups = symtab._sys.core_groups
    buff.append('##Config.core_groups: %s' % (repr(core_groups)))

    config = symtab._sys.config
    for attr in dir(config):
        buff.append('##Config.%s: %s' % (attr, repr(getattr(config, attr, None))))
    buff.append("##----------")
    syms = []
    for attr in dir(symtab):
        if attr in core_groups:
            continue
        syms.append(attr)

    buff.append("##Symbols.Save_Count: %d " % len(syms))
    buff.append("##----------")

    for attr in dir(symtab):
        if attr in core_groups:
            continue
        buff.append('<<::%s::>>' % attr)
        buff.append('%s' % encode4js(getattr(symtab, attr)))

    buff.append("##----------")
    buff.append("")
    print("Save fname ", fname)
    fh = GzipFile(fname, "w")
    fh.write(str2bytes("\n".join(buff)))
    fh.close()


def load_session(fname, _larch=None):
    """load all data from a Larch Save File

    Arguments
    ---------
    fname    name of save file

    Returns
    -------
    None

    """

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
