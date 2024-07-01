#!/usr/bin/env python
""" Builtins for larch"""

import sys
import time

from . import utils
from .utils.show import _larch_builtins as show_builtins

from .larchlib import parse_group_args, Journal
from .symboltable import Group
from .version import show_version

from . import math
from . import io
from . import fitting
from . import xray
from . import xrf
from . import xafs
from . import xrd
from . import xrmmap
from . import wxlib

from .utils import physical_constants

__core_modules = [math, fitting, io, xray, xrf, xafs, xrd, xrmmap, wxlib]

try:
    from . import epics
    __core_modules.append(epics)
except ImportError:
    pass

if wxlib.HAS_WXPYTHON:
    try:
        from .wxlib import plotter
        from . import wxmap, wxxas, wxxrd
        __core_modules.extend([plotter, wxmap, wxxas, wxxrd])
    except:
        pass

# inherit most available symbols from python's __builtins__
from_builtin = [sym for sym in __builtins__ if not sym.startswith('__')]

# inherit these from math (many will be overridden by numpy)
from_math = ('acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2', 'atanh',
            'ceil', 'copysign', 'cos', 'cosh', 'degrees', 'e', 'exp',
            'fabs', 'factorial', 'floor', 'fmod', 'frexp', 'fsum', 'hypot',
            'isinf', 'isnan', 'ldexp', 'log', 'log10', 'log1p', 'modf',
            'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh',
            'trunc')

# inherit these from numpy
from_numpy = ('abs', 'add', 'all', 'amax', 'amin', 'angle', 'any', 'append',
    'arange', 'arccos', 'arccosh', 'arcsin', 'arcsinh', 'arctan', 'arctan2',
    'arctanh', 'argmax', 'argmin', 'argsort', 'argwhere', 'around', 'array',
    'asarray', 'atleast_1d', 'atleast_2d', 'atleast_3d', 'average', 'bartlett',
    'bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor', 'blackman',
    'broadcast', 'ceil', 'choose', 'clip', 'column_stack', 'common_type',
    'complex128', 'compress', 'concatenate', 'conjugate', 'convolve',
    'copysign', 'corrcoef', 'correlate', 'cos', 'cosh', 'cov', 'cross',
    'cumprod', 'cumsum', 'datetime_data', 'deg2rad', 'degrees', 'delete',
    'diag', 'diag_indices', 'diag_indices_from', 'diagflat', 'diagonal',
    'diff', 'digitize', 'divide', 'dot', 'dsplit', 'dstack', 'dtype', 'e',
    'ediff1d', 'empty', 'empty_like', 'equal', 'exp', 'exp2', 'expand_dims',
    'expm1', 'extract', 'eye', 'fabs', 'fft', 'fill_diagonal', 'finfo', 'fix',
    'flatiter', 'flatnonzero', 'fliplr', 'flipud', 'float64', 'floor',
    'floor_divide', 'fmax', 'fmin', 'fmod', 'format_parser', 'frexp',
    'frombuffer', 'fromfile', 'fromfunction', 'fromiter', 'frompyfunc',
    'fromregex', 'fromstring', 'genfromtxt', 'getbufsize', 'geterr',
    'gradient', 'greater', 'greater_equal', 'hamming', 'hanning', 'histogram',
    'histogram2d', 'histogramdd', 'hsplit', 'hstack', 'hypot', 'i0',
    'identity', 'iinfo', 'imag', 'indices', 'inexact', 'inf', 'info', 'inner',
    'insert', 'int32', 'integer', 'interp', 'intersect1d', 'invert',
    'iscomplex', 'iscomplexobj', 'isfinite', 'isinf', 'isnan', 'isneginf',
    'isposinf', 'isreal', 'isrealobj', 'isscalar', 'iterable', 'kaiser',
    'kron', 'ldexp', 'left_shift', 'less', 'less_equal', 'linalg', 'linspace',
    'little_endian', 'loadtxt', 'log', 'log10', 'log1p', 'log2', 'logaddexp',
    'logaddexp2', 'logical_and', 'logical_not', 'logical_or', 'logical_xor',
    'logspace', 'longdouble', 'longlong', 'mask_indices', 'matrix', 'maximum',
    'may_share_memory', 'mean', 'median', 'memmap', 'meshgrid', 'minimum',
    'mintypecode', 'mod', 'modf', 'msort', 'multiply', 'nan', 'nan_to_num',
    'nanargmax', 'nanargmin', 'nanmax', 'nanmin', 'nansum', 'ndarray',
    'ndenumerate', 'ndim', 'ndindex', 'negative', 'nextafter', 'nonzero',
    'not_equal', 'number', 'ones', 'ones_like', 'outer', 'packbits',
    'percentile', 'pi', 'piecewise', 'place', 'poly', 'poly1d', 'polyadd',
    'polyder', 'polydiv', 'polyint', 'polymul', 'polynomial', 'polysub',
    'polyval', 'power', 'prod', 'ptp', 'put', 'putmask', 'rad2deg', 'radians',
    'random', 'ravel', 'real', 'real_if_close', 'reciprocal', 'record',
    'remainder', 'repeat', 'reshape', 'resize', 'right_shift', 'rint', 'roll',
    'rollaxis', 'roots', 'rot90', 'round', 'searchsorted', 'select',
    'setbufsize', 'setdiff1d', 'seterr', 'setxor1d', 'shape', 'short', 'sign',
    'signbit', 'signedinteger', 'sin', 'sinc', 'single', 'sinh', 'size',
    'sort', 'sort_complex', 'spacing', 'split', 'sqrt', 'square', 'squeeze',
    'std', 'subtract', 'sum', 'swapaxes', 'take', 'tan', 'tanh', 'tensordot',
    'tile', 'trace', 'transpose', 'tri', 'tril', 'tril_indices',
    'tril_indices_from', 'trim_zeros', 'triu', 'triu_indices',
    'triu_indices_from', 'true_divide', 'trunc', 'ubyte', 'uint', 'uint32',
    'union1d', 'unique', 'unravel_index', 'unsignedinteger', 'unwrap',
    'ushort', 'vander', 'var', 'vdot', 'vectorize', 'vsplit', 'vstack',
    'where', 'zeros', 'zeros_like')

numpy_renames = {'ln':'log', 'asin':'arcsin', 'acos':'arccos',
                 'atan':'arctan', 'atan2':'arctan2', 'atanh':'arctanh',
                 'acosh':'arccosh', 'asinh':'arcsinh', 'npy_save': 'save',
                 'npy_load': 'load', 'npy_copy': 'copy'}

constants = {}
for pconst_name in ('PLANCK_HC', 'AVOGADRO', 'AMU',
                    'R_ELECTRON_ANG','DEG2RAD', 'RAD2DEG'):
    constants[pconst_name] = getattr(physical_constants, pconst_name)



## More builtin commands, to set up the larch language:

# def _group(_larch=None, **kws):
#     """create a group"""
#     if _larch is None:
#         _larch = Group()
#     else:
#         group = _larch.symtable.create_group()
#     for key, val in kws.items():
#         setattr(group, key, val)
#     return group

def _eval(text, filename=None, _larch=None):
    """evaluate a string of larch text
    """
    if _larch is None:
        raise Warning("cannot eval string -- larch broken?")
    return _larch.eval(text, fname=filename)


def _run(filename=None, new_module=None, _larch=None):
    "execute the larch text in a file as larch code."
    if _larch is None:
        raise Warning(f"cannot run file '{filename:s}' -- larch broken?")
    return _larch.runfile(filename, new_module=new_module)

def _reload(mod, _larch=None):
    """reload a module, either larch or python"""
    if _larch is None:
        raise Warning(f"cannot reload module '{mod:s}' -- larch broken?")

    modname = None
    if mod in _larch.symtable._sys.modules.values():
        for k, v in _larch.symtable._sys.modules.items():
            if v == mod:
                modname = k
    elif mod in sys.modules.values():
        for k, v in sys.modules.items():
            if v == mod:
                modname = k
    elif (mod in _larch.symtable._sys.modules.keys() or
          mod in sys.modules.keys()):
        modname = mod

    if modname is not None:
        return _larch.import_module(modname, do_reload=True)

def _help(*args, _larch=None):
    "show help on topic or object"
    write = sys.stdout.write
    if _larch is not None:
        write = _larch.writer.write
    buff = []
    for arg in args:
        if _larch is not None and isinstance(arg, str):
            arg= _larch.symtable.get_symbol(arg, create=False)
        buff.append(repr(arg))
        if callable(arg) and arg.__doc__ is not None:
            buff.append(arg.__doc__)
    buff.append('')
    write('\n'.join(buff))


def _journal(*args, **kws):
    return Journal(*args, **kws)

def _dir(obj=None, _larch=None):
    "return directory of an object -- thin wrapper about python builtin"
    if obj is None and _larch is not None:
        obj = _larch.symtable
    return dir(obj)

def _subgroups(obj):
    "return list of subgroups"
    if isinstance(obj, Group):
        return obj._subgroups()
    raise Warning("subgroups() argument must be a group")

def _groupitems(obj):
    "returns group items as if items() method of a dict"
    if isinstance(obj, Group):
        return obj._members().items()
    raise Warning("group_items() argument must be a group")

def _which(sym, _larch=None):
    "return full path of object, or None if object cannot be found"
    if _larch is None:
        raise Warning("cannot run which() -- larch broken?")
    stable = _larch.symtable
    if hasattr(sym, '__name__'):
        sym = sym.__name__
    if isinstance(sym, str) and stable.has_symbol(sym):
        obj = stable.get_symbol(sym)
        if obj is not None:
            return '%s.%s' % (stable.get_parentpath(sym), sym)
    return None

def _exists(sym, _larch=None):
    "return True if a named symbol exists and can be found, False otherwise"
    return _which(sym, _larch=_larch) is not None

def _isgroup(obj, _larch=None):
    """return whether argument is a group or the name of a group

    With additional arguments (all must be strings), it also tests
    that the group has an an attribute named for each argument. This
    can be used to test not only if a object is a Group, but whether
    it a group with expected arguments.

        > x = 10
        > g = group(x=x, y=2)
        > isgroup(g), isgroup(x)
        True, False
        > isgroup('g'), isgroup('x')
        True, False
        > isgroup(g, 'x', 'y')
        True
        > isgroup(g, 'x', 'y', 'z')
        False

    """
    if (_larch is not None and
        isinstance(obj, str) and
        _larch.symtable.has_symbol(obj)):
        obj = _larch.symtable.get_symbol(obj)
    return isinstance(obj, Group)


def _pause(msg='Hit return to continue', _larch=None):
    if _larch is None:
        raise Warning("cannot pause() -- larch broken?")
    return input(msg)

def _sleep(t=0):
    return time.sleep(t)
_sleep.__doc__ = time.sleep.__doc__

def _time():
    return time.time()
_time.__doc__ = time.time.__doc__

def _strftime(format, *args):
    return time.strftime(format, *args)
_strftime.__doc__ = time.strftime.__doc__


def save_history(filename, session_only=False, maxlines=5000, _larch=None):
    """save history of larch commands to a file"""
    _larch.input.history.save(filename, session_only=session_only, maxlines=maxlines)

def show_history(max_lines=10000, _larch=None):
    """show history of larch commands"""
    nhist = min(max_lines, len(_larch.history.buffer))
    for hline in _larch.history.buffer[-nhist:]:
        _larch.writer.write("%s\n" % hline)

def init_display_group(_larch):
    symtab = _larch.symtable
    if not symtab.has_group('_sys.display'):
        symtab.new_group('_sys.display')
        colors = {}
        colors['text'] = {'color': None}
        colors['text2'] = {'color': 'cyan'}
        colors['comment'] = {'color': 'green'}
        colors['error'] = {'color': 'red',  'attrs': ['bold']}
        display = symtab._sys.display
        display.colors = colors
        display.use_color = True
        display.terminal = 'xterm'


_main_builtins = dict(group=Group, Group=Group, dir=_dir, which=_which,
                      exists=_exists, isgroup=_isgroup,
                      subgroups=_subgroups, group_items=_groupitems,
                      parse_group_args=parse_group_args, pause=_pause,
                      sleep=_sleep, systime=_time, clock=_time,
                      strftime=_strftime, reload=_reload, run=_run,
                      eval=_eval, help=_help, journal=_journal,
                      show_version=show_version,
                      save_history=save_history,
                      show_history=show_history)

_main_builtins.update(utils._larch_builtins)
_main_builtins.update(show_builtins)


# names to fill in the larch namespace at startup
init_builtins = dict(_builtin=_main_builtins)

# functions to run (with signature fcn(_larch)) at interpreter startup
init_funcs = [init_display_group]

# group/classes to register for save-restore
init_moddocs = {}

for cmod in __core_modules:
    if cmod is None:
        continue
    cmodname  = getattr(cmod, '_larch_name', cmod.__name__)
    if cmodname.startswith('larch.'):
        cmodname = cmodname.replace('larch.', '_')

    doc = getattr(cmod, '__DOC__', None)
    if doc is not None:
        init_moddocs[cmodname] = doc
    builtins = getattr(cmod, '_larch_builtins', {})
    init_fcn = getattr(cmod, '_larch_init', None)

    for bkey, bval in builtins.items():
        if bkey not in init_builtins:
            init_builtins[bkey] = bval
        else:
            init_builtins[bkey].update(bval)

    if init_fcn is not None:
        init_funcs.append(init_fcn)

# list of supported valid commands -- don't need parentheses for these
valid_commands = ['run', 'help', 'show', 'which', 'more', 'cd']
