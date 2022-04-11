import json
import time
import numpy as np
import uuid, socket, platform

from gzip import GzipFile

from collections import OrderedDict

from lmfit import Parameter, Parameters
from lmfit.model import Model, ModelResult
from lmfit.minimizer import Minimizer, MinimizerResult

from larch import Group, isgroup
from ..fitting import isParameter
from ..utils.jsonutils import encode4js, decode4js
from ..utils.strutils import bytes2str, str2bytes, fix_varname

def is_gzip(filename):
    "is a file gzipped?"
    with open(filename, 'rb') as fh:
        return fh.read(3) == b'\x1f\x8b\x08'
    return False


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
        fname = time.strftime('%Y%b%d_%H%M')
    if not fname.endswith('.larix'):
        fname = fname + '.larix'

    if _larch is None:
        raise ValueError('_larch not defined')
    symtab = _larch.symtable


    buff = ["##LARIX: 1.0      Larch Session File",
            "##Date Saved: %s"   % time.strftime('%Y-%m-%d %H:%M:%S'),
            "##<CONFIG>",
            "##Machine Platform: %s" % platform.system(),
            "##Machine Name: %s" % socket.gethostname(),
            "##Machine MACID: %s" % get_machineid(),
            "##Machine Version: %s"   % platform.version(),
            "##Machine Processor: %s" % platform.machine(),
            "##Machine Architecture: %s" % ':'.join(platform.architecture()),
            "##Python Version: %s" % platform.python_version(),
            "##Python Compiler: %s" % platform.python_compiler(),
            "##Python Implementation: %s" % platform.python_implementation(),
            "##Larch Release Version: %s" % __release_version__,
            "##Larch Release Date: %s" % __date__,
            "##Larch Working Version: %s" % __version__,
            ]

    core_groups = symtab._sys.core_groups
    buff.append('##Larch Core Groups: %s' % (repr(core_groups)))

    config = symtab._sys.config
    for attr in dir(config):
        buff.append('##Larch %s: %s' % (attr, repr(getattr(config, attr, None))))
    buff.append("##</CONFIG>")

    try:
        histbuff = _larch.input.history.get(session_only=True)
    except:
        histbuff = None
    if histbuff is not None:
        buff.append("##<Session Commands>")
        buff.extend(["%s" % l for l in histbuff])
        buff.append("##</Session Commands>")

    syms = []
    for attr in dir(symtab):
        if attr in core_groups:
            continue
        syms.append(attr)
    buff.append("##<Symbols: count=%d>"  % len(syms))

    for attr in dir(symtab):
        if attr in core_groups:
            continue
        buff.append('<:%s:>' % attr)
        buff.append('%s' % json.dumps(encode4js(getattr(symtab, attr))))

    buff.append("##</Symbols>")
    buff.append("")

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

    fopen = GzipFile if is_gzip(fname) else open
    with fopen(fname, 'rb') as fh:
        text = fh.read().decode('utf-8')

    lines = text.split('\n')
    if not lines[0].startswith('##LARIX:'):
        raise ValueError(f"Invalid Larch session file: '{fname:s}'")

    version = lines[0].split()[1]

    data = {'unknown':{}}
    section = 'unknown'
    cmd_history = []
    nsyms = nsym_expected = 0
    symname = '_unknown_'

    for line in lines:
        if line.startswith("##<"):
            section = line.replace('##<','').replace('>', '').strip().lower()
            options = ''
            if ':' in section:
                section, options = section.split(':', 1)
                section = section.strip()
                options = options.strip()
            if section.startswith('/'):
                section = 'unknown'
            else:
                if section == 'session commands' and len(options) > 0:
                    nsyms_expected = int(options.replace('count=', ''))
                if section not in data:
                    data[section] = {}
        elif section == 'config':
            if line.startswith('##'): line = line[2:]
            key, val = line.split(':', 1)
            data[section][key] = val
        elif section == 'session commands':
            cmd_history.append(line)

        elif section == 'symbols':
            if line.startswith('<:') and line.endswith(':>'):
                symname = line.replace('<:', '').replace(':>', '')
            else:
                data[section][symname] = decode4js(json.loads(line))

    data['session commands'] = cmd_history

    x = data.pop('unknown')
    if len(x) > 0:
        print("Warning: unknown data in Larch Session file")
        print(x)

    if _larch is not None:
        for sym, val in data['symbols'].items():
            setattr(_larch.symtable, key, val)
    return data
