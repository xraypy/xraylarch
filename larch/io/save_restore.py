import json
import time
import numpy as np
import uuid, socket, platform
from collections import namedtuple

from gzip import GzipFile

from lmfit import Parameter, Parameters
# from lmfit.model import Model, ModelResult
# from lmfit.minimizer import Minimizer, MinimizerResult

from larch import Group, isgroup, __date__, __version__, __release_version__
from ..utils import (isotime, bytes2str, str2bytes, fix_varname,
                     read_textfile, unique_name, format_exception, unixpath)
from ..utils.jsonutils import encode4js, decode4js

SessionStore = namedtuple('SessionStore', ('config', 'command_history', 'symbols'))

EMPTY_FEFFCACHE = {'paths': {}, 'runs': {}}

def invert_dict(d):
    "invert a dictionary {k: v} -> {v: k}"
    return {v: k for k, v in d.items()}

def get_machineid():
    "machine id / MAC address, independent of hostname"
    return hex(uuid.getnode())[2:]

def is_larch_session_file(fname):
    return read_textfile(fname, size=64).startswith('##LARIX:')

def save_groups(fname, grouplist):
    """save a list of groups (and other supported datatypes) to file

    This is a simplified and minimal version of save_session()

    Use 'read_groups()' to read data saved from this function
    """
    buff = ["##LARCH GROUPLIST"]
    for dat in grouplist:
        buff.append(json.dumps(encode4js(dat)))

    buff.append("")

    fh = GzipFile(unixpath(fname), "w")
    fh.write(str2bytes("\n".join(buff)))
    fh.close()

def read_groups(fname):
    """read a list of groups (and other supported datatypes)
    from a file saved with 'save_groups()'

    Returns a list of objects
    """
    text = read_textfile(fname)
    lines = text.split('\n')
    line0 = lines.pop(0)
    if not line0.startswith('##LARCH GROUPLIST'):
        raise ValueError(f"Invalid Larch group file: '{fname:s}'")

    out = []
    for line in lines:
        if len(line) > 1:
            out.append(decode4js(json.loads(line)))
    return out


def save_session(fname=None, symbols=None, histbuff=None,
                auto_xasgroups=False, _larch=None):
    """save all groups and data into a Larch Save File (.larix)
    A portable compressed json file, that can be loaded with `read_session()`

    Arguments:
        fname (str):   name of output save file.
        symbols [list of str or None]: names of symbols to save. [None]
               saving all non-core (user-generated) objects.
        histbuff [list of str or None]: command history, [None]
               saving the full history of the current session.
        auto_xasgroups [bool]: whether to automatically generate the
               `_xasgroups` dictionary for "XAS Groups" as used by
               Larix, which will include all symbols that are Groups
               and have both 'filename' and 'groupname' attributes.

    Notes:
        1. if `symbols` is `None` (default), all variables outside of the
           core groups will be saved: this effectively saves "the whole session".
           A limited list of symbol names can also be provided, saving part of
           a project (say, one or two data sets).
        2. if `histbuff` is `None` (default), the full list of commands in
           the session will be saved.
        3. auto_xasgroups will generate an `_xasgroups` dictionary (used by
           Larix to decide what groups to present as "Data Groups") from the
           supplied or available symbols: every Group with a "groupname" and
           "filename" will be included.

    See Also:
        read_session, load_session, clear_sessio

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
            ]

    core_groups = symtab._sys.core_groups
    buff.append('##Larch Core Groups: %s' % (json.dumps(core_groups)))

    config = symtab._sys.config
    for attr in dir(config):
        buff.append('##Larch %s: %s' % (attr, json.dumps(getattr(config, attr, None))))
    buff.append("##</CONFIG>")


    if histbuff is None:
        try:
            histbuff = _larch.input.history.get(session_only=True)
        except:
            histbuff = None

    if histbuff is not None:
        buff.append("##<Session Commands>")
        buff.extend(["%s" % l for l in histbuff])
        buff.append("##</Session Commands>")

    if symbols is None:
        symbols = []
        for attr in symtab.__dir__(): # insert order, not alphabetical order
            if attr not in core_groups:
                symbols.append(attr)
    nsyms = len(symbols)

    _xasgroups = None
    if '_xasgroups' not in symbols and auto_xasgroups:
        nsyms +=1
        _xasgroups = {}
        for sname in symbols:
            obj = getattr(symtab, sname, None)
            if isgroup(obj):
                gname = getattr(obj, 'groupname', None)
                fname = getattr(obj, 'filename', None)
                if gname is not None and fname is not None:
                    _xasgroups[fname] = gname

    buff.append("##<Symbols: count=%d>"  % len(symbols))
    if _xasgroups is not None:
        buff.append('<:_xasgroups:>')
        buff.append(json.dumps(encode4js(_xasgroups)))

    for attr in symbols:
        if attr not in core_groups:
            buff.append(f'<:{attr}:>')
            buff.append(json.dumps(encode4js(getattr(symtab, attr))))

    buff.append("##</Symbols>")
    buff.append("")

    fh = GzipFile(unixpath(fname), "w")
    fh.write(str2bytes("\n".join(buff)))
    fh.close()

def clear_session(_larch=None):
    """clear user-definded data in a session

    Example:
         >>> save_session('foo.larix')
         >>> clear_session()

     will effectively save and then reset the existing session.
    """
    if _larch is None:
        raise ValueError('_larch not defined')

    core_groups = _larch.symtable._sys.core_groups
    for attr in _larch.symtable.__dir__():
        if attr not in core_groups:
            delattr(_larch.symtable, attr)


def read_session(fname, clean_xasgroups=True):
    """read Larch Session File, returning data into new data in the
    current session

    Arguments:
         fname (str):  name of save file

    Returns:
       Tuple
       A tuple wih entries:

           | configuration  - a dict of configuration for the saved session.
           | command_history  - a list of commands in the saved session.
           | symbols         - a dict of Larch/Python symbols, groups, etc

    See Also:
       load_session


    """
    text = read_textfile(fname)
    lines = text.split('\n')
    line0 = lines.pop(0)
    if not line0.startswith('##LARIX:'):
        raise ValueError(f"Invalid Larch session file: '{fname:s}'")

    version = line0.split()[1]

    symbols = {}
    config = {'Larix Version': version}
    cmd_history = []
    nsyms = nsym_expected = 0
    section = symname = '_unknown_'
    for line in lines:
        if line.startswith("##<"):
            section = line.replace('##<','').replace('>', '').strip().lower()
            if ':' in section:
                section, options = section.split(':', 1)
            if section.startswith('/'):
                section = '_unknown_'
        elif section == 'session commands':
            cmd_history.append(line)

        elif section == 'symbols':
            if line.startswith('<:') and line.endswith(':>'):
                symname = line.replace('<:', '').replace(':>', '')
            else:
                try:
                    symbols[symname] = decode4js(json.loads(line))
                except:
                    print(''.join(format_exception()))
                    print("decode failed:: ", symname, repr(line)[:50])
        else:
            if line.startswith('##') and ':' in line:
                line = line[2:]
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip()
                if '[' in val or '{' in val:
                    try:
                        val = decode4js(json.loads(val))
                    except:
                        print(''.join(format_exception()))
                        print("decode failed @## ", repr(val)[:50])
                config[key] = val
    if '_xasgroups' in symbols and clean_xasgroups:
        missing = []
        for name, group in symbols['_xasgroups'].items():
            if group not in symbols:
                missing.append(name)
        for name in missing:
            symbols['_xasgroups'].pop(name)

    return SessionStore(config, cmd_history, symbols)


def load_session(fname, ignore_groups=None, include_xasgroups=None, _larch=None, verbose=False):
    """load all data from a Larch Session File into current larch session,
    merging into existing groups as appropriate (see Notes below)

    Arguments:
       fname  (str):  name of session file
       ignore_groups (list of strings): list of symbols to not import
       include_xasgroups (list of strings): list of symbols to import as XAS spectra,
                           even if not expicitly set in `_xasgroups`
       verbose (bool): whether to print warnings for overwrites [False]
    Returns:
        None

    Notes:
        1. data in the following groups will be merged into existing session groups:
           `_feffpaths` : dict of "current feff paths"
           `_feffcache` : dict with cached feff paths and feff runs
           `_xasgroups` : dict mapping "File Name" and "Group Name", used in `Larix`

        2. to avoid name clashes, group and file names in the `_xasgroups` dictionary
           may be modified on loading

    """
    if _larch is None:
        raise ValueError('load session needs a larch session')

    session = read_session(fname)

    if ignore_groups is None:
        ignore_groups = []
    if include_xasgroups is None:
        include_xasgroups = []

    # special groups to merge into existing session:
    #  _feffpaths, _feffcache, _xasgroups
    s_symbols = session.symbols
    s_xasgroups = s_symbols.pop('_xasgroups', {})

    s_xasg_inv = invert_dict(s_xasgroups)

    s_feffpaths = s_symbols.pop('_feffpaths', {})
    s_feffcache = s_symbols.pop('_feffcache', EMPTY_FEFFCACHE)

    symtab = _larch.symtable
    if not hasattr(symtab, '_xasgroups'):
        symtab._xasgroups = {}
    if not hasattr(symtab, '_feffpaths'):
        symtab._feffpaths = {}
    if not hasattr(symtab, '_feffcache'):
        symtab._feffcache = EMPTY_FEFFCACHE

    if not hasattr(symtab._sys, 'restored_sessions'):
        symtab._sys.restored_sessions = {}
    restore_data = {'date': isotime(),
                    'config': session.config,
                    'command_history': session.command_history}
    symtab._sys.restored_sessions[fname] = restore_data

    c_xas_gnames = list(symtab._xasgroups.values())

    for sym, val in s_symbols.items():
        if sym in ignore_groups:
            if sym in s_xasgroups.values():
                s_key = s_xasg_inv[sym]
                s_xasgroups.pop(s_key)
                s_xasg_inv = invert_dict(s_xasgroups)

            continue
        if sym in c_xas_gnames or sym in include_xasgroups:
            newsym = unique_name(sym, c_xas_gnames)
            c_xas_gnames.append(newsym)
            if sym in s_xasgroups.values():
                s_key = s_xasg_inv[sym]
                s_xasgroups[s_key] = newsym
                s_xasg_inv = invert_dict(s_xasgroups)
            sym = newsym

        if verbose and hasattr(symtab, sym):
            print(f"warning overwriting '{sym}'")
        setattr(symtab, sym, val)

    symtab._feffpaths.update(s_feffpaths)

    symtab._xasgroups.update(s_xasgroups)
    missing = []
    for name, group in symtab._xasgroups.items():
        if group not in symtab:
            missing.append(name)
    for name in missing:
        symtab._xasgroups.pop(name)

    for name in ('paths', 'runs'):
        symtab._feffcache[name].update(s_feffcache[name])
