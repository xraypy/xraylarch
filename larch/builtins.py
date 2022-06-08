#!/usr/bin/env python
""" Builtins for larch"""

import os
import imp
import sys
import time
import re
import traceback
import io
import asteval
from .helper import Helper
from . import inputText
from . import site_config
from . import utils
from .utils.show import _larch_builtins as show_builtins

from .larchlib import parse_group_args, LarchExceptionHolder, Journal
from .symboltable import isgroup as sym_isgroup

from . import math
from . import io
from . import fitting
from . import xray
from . import xrf
from . import xafs
from . import xrd
from . import xrmmap
from .utils import physical_constants

__core_modules = [math, fitting, io, xray, xrf, xafs, xrd, xrmmap]

try:
    from . import epics
    __core_modules.append(epics)
except ImportError:
    pass


try:
    import wx
    HAS_WXPYTHON = True
except (ImportError, AttributeError):
    HAS_WXPYTHON = False

from . import wxlib
__core_modules.extend([wxlib])
if HAS_WXPYTHON:
    try:
        from .wxlib import plotter
        from . import wxmap, wxxas, wxxrd
        __core_modules.extend([plotter, wxmap, wxxas, wxxrd])
    except:
        pass

helper = Helper()

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
from_numpy = ('ComplexWarning', 'Inf', 'NAN', 'abs', 'absolute', 'add',
              'alen', 'all', 'allclose', 'alltrue', 'amax', 'amin',
              'angle', 'any', 'append', 'apply_along_axis',
              'apply_over_axes', 'arange', 'arccos', 'arccosh', 'arcsin',
              'arcsinh', 'arctan', 'arctan2', 'arctanh', 'argmax',
              'argmin', 'argsort', 'argwhere', 'around', 'array',
              'asanyarray', 'asarray', 'asscalar', 'atleast_1d',
              'atleast_2d', 'atleast_3d', 'average', 'bartlett',
              'bincount', 'bitwise_and', 'bitwise_not', 'bitwise_or',
              'bitwise_xor', 'blackman', 'bmat', 'broadcast', 'ceil',
              'chararray', 'choose', 'clip', 'column_stack', 'common_type',
              'complex128', 'compress', 'concatenate', 'conj', 'conjugate',
              'convolve', 'copysign', 'corrcoef', 'correlate', 'cos',
              'cosh', 'cov', 'cross', 'cumprod', 'cumproduct', 'cumsum',
              'datetime_data', 'deg2rad', 'degrees', 'delete', 'diag',
              'diag_indices', 'diag_indices_from', 'diagflat', 'diagonal',
              'diff', 'digitize', 'disp', 'divide', 'dot', 'dsplit',
              'dstack', 'dtype', 'e', 'ediff1d', 'empty', 'empty_like',
              'equal', 'errstate', 'exp', 'exp2', 'expand_dims', 'expm1',
              'extract', 'eye', 'fabs', 'fastCopyAndTranspose', 'fft',
              'fill_diagonal', 'find_common_type', 'finfo', 'fix',
              'flatiter', 'flatnonzero', 'flexible', 'fliplr', 'flipud',
              'float64', 'floor', 'floor_divide', 'fmax', 'fmin', 'fmod',
              'format_parser', 'frexp', 'frombuffer', 'fromfile',
              'fromfunction', 'fromiter', 'frompyfunc', 'fromregex',
              'fromstring', 'genfromtxt', 'get_array_wrap', 'get_include',
              'get_printoptions', 'getbufsize', 'geterr', 'geterrcall',
              'geterrobj', 'gradient', 'greater', 'greater_equal',
              'hamming', 'hanning', 'histogram', 'histogram2d',
              'histogramdd', 'hsplit', 'hstack', 'hypot', 'i0', 'identity',
              'iinfo', 'imag', 'in1d', 'index_exp', 'indices', 'inexact',
              'inf', 'info', 'infty', 'inner', 'insert', 'int32',
              'integer', 'interp', 'intersect1d', 'invert', 'iscomplex',
              'iscomplexobj', 'isfinite', 'isinf', 'isnan', 'isneginf',
              'isposinf', 'isreal', 'isrealobj', 'isscalar', 'issctype',
              'issubclass_', 'issubdtype', 'issubsctype', 'iterable',
              'kaiser', 'kron', 'ldexp', 'left_shift', 'less',
              'less_equal', 'lexsort', 'lib', 'linalg', 'linspace',
              'little_endian', 'loadtxt', 'log', 'log10', 'log1p', 'log2',
              'logaddexp', 'logaddexp2', 'logical_and', 'logical_not',
              'logical_or', 'logical_xor', 'logspace', 'longcomplex',
              'longdouble', 'longfloat', 'longlong', 'lookfor', 'ma',
              'mafromtxt', 'mask_indices', 'mat', 'math', 'matrix',
              'matrixlib', 'max', 'maximum', 'maximum_sctype',
              'may_share_memory', 'mean', 'median', 'memmap', 'meshgrid',
              'mgrid', 'min', 'minimum', 'mintypecode', 'mod', 'modf',
              'msort', 'multiply', 'nan', 'nan_to_num', 'nanargmax',
              'nanargmin', 'nanmax', 'nanmin', 'nansum', 'nbytes',
              'ndarray', 'ndenumerate', 'ndfromtxt', 'ndim', 'ndindex',
              'negative', 'nextafter', 'nonzero', 'not_equal', 'number',
              'obj2sctype', 'object0', 'object_', 'ogrid', 'ones',
              'ones_like', 'outer', 'packbits', 'percentile', 'pi',
              'piecewise', 'place', 'poly', 'poly1d', 'polyadd', 'polyder',
              'polydiv', 'polyfit', 'polyint', 'polymul', 'polynomial',
              'polysub', 'polyval', 'power', 'prod', 'product', 'ptp',
              'put', 'putmask', 'rad2deg', 'radians', 'random', 'ravel',
              'real', 'real_if_close', 'rec', 'recarray', 'recfromcsv',
              'recfromtxt', 'reciprocal', 'record', 'remainder', 'repeat',
              'require', 'reshape', 'resize', 'right_shift', 'rint',
              'roll', 'rollaxis', 'roots', 'rot90', 'round', 'round_',
              'row_stack', 'safe_eval', 'savetxt', 'savez', 'sctype2char',
              'sctypeDict', 'searchsorted', 'select', 'setbufsize',
              'setdiff1d', 'seterr', 'seterrcall', 'seterrobj', 'setxor1d',
              'shape', 'short', 'show_config', 'sign', 'signbit',
              'signedinteger', 'sin', 'sinc', 'single', 'singlecomplex',
              'sinh', 'size', 'sometrue', 'sort', 'sort_complex', 'source',
              'spacing', 'split', 'sqrt', 'square', 'squeeze', 'std',
              'subtract', 'sum', 'swapaxes', 'take', 'tan', 'tanh',
              'tensordot', 'tile', 'trace', 'transpose', 'trapz', 'tri',
              'tril', 'tril_indices', 'tril_indices_from', 'trim_zeros',
              'triu', 'triu_indices', 'triu_indices_from', 'true_divide',
              'trunc', 'typename', 'ubyte', 'ufunc', 'uint', 'uint32',
              'union1d', 'unique', 'unpackbits', 'unravel_index',
              'unsignedinteger', 'unwrap', 'ushort', 'vander', 'var',
              'vdot', 'vectorize', 'version', 'vsplit', 'vstack', 'where',
              'who', 'zeros', 'zeros_like')

numpy_renames = {'ln':'log', 'asin':'arcsin', 'acos':'arccos',
                 'atan':'arctan', 'atan2':'arctan2', 'atanh':'arctanh',
                 'acosh':'arccosh', 'asinh':'arcsinh', 'npy_save': 'save',
                 'npy_load': 'load', 'npy_copy': 'copy'}

constants = {}
for pconst_name in ('PLANCK_HC', 'AVOGADRO', 'AMU',
                    'R_ELECTRON_ANG','DEG2RAD', 'RAD2DEG'):
    constants[pconst_name] = getattr(physical_constants, pconst_name)

##
## More builtin commands, to set up the larch language:

def _group(_larch=None, **kws):
    """create a group"""
    if _larch is None:
        raise Warning("cannot create group -- larch broken?")

    group = _larch.symtable.create_group()
    for key, val in kws.items():
        setattr(group, key, val)
    return group

def _eval(text, filename=None, _larch=None):
    """evaluate a string of larch text
    """
    if _larch is None:
        raise Warning("cannot eval string -- larch broken?")
    return _larch.eval(text, fname=filename)


def _run(filename=None, new_module=None, _larch=None):
    "execute the larch text in a file as larch code."
    if _larch is None:
        raise Warning("cannot run file '%s' -- larch broken?" % filename)
    return _larch.runfile(filename, new_module=new_module)

def _reload(mod, _larch=None):
    """reload a module, either larch or python"""
    if _larch is None:
        raise Warning("cannot reload module '%s' -- larch broken?" % mod)

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
    helper.buffer = []
    if helper._larch is None and _larch is not None:
        helper._larch = _larch
    if args == ('',):
        args = ('help',)
    if helper._larch is None:
        helper.addtext('cannot start help system!')
    else:
        for a in args:
            helper.help(a)
    if helper._larch is not None:
        helper._larch.writer.write("%s\n" % helper.getbuffer())
    else:
        return helper.getbuffer()

def _journal(*args, **kws):
    return Journal(*args, **kws)

def _dir(obj=None, _larch=None):
    "return directory of an object -- thin wrapper about python builtin"
    if _larch is None:
        raise Warning("cannot run dir() -- larch broken?")
    if obj is None:
        obj = _larch.symtable
    return dir(obj)

def _subgroups(obj, _larch=None):
    "return list of subgroups"
    if _larch is None:
        raise Warning("cannot run subgroups() -- larch broken?")
    if sym_isgroup(obj):
        return obj._subgroups()
    else:
        raise Warning("subgroups() argument must be a group")

def _groupitems(obj, _larch=None):
    "returns group items as if items() method of a dict"
    if _larch is None:
        raise Warning("cannot run subgroups() -- larch broken?")
    if sym_isgroup(obj):
        return obj._members().items()
    else:
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
    return which(sym, _larch=_larch) is not None

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
    if _larch is None:
        raise Warning("cannot run isgroup() -- larch broken?")
    stable = _larch.symtable
    if isinstance(obj, str) and stable.has_symbol(obj):
        obj = stable.get_symbol(obj)
    return sym_isgroup(obj)


def _pause(msg='Hit return to continue', _larch=None):
    if _larch is None:
        raise Warning("cannot pause() -- larch broken?")
    return input(msg)

def _sleep(t=0):  return time.sleep(t)
_sleep.__doc__ = time.sleep.__doc__

def _time():  return time.time()
_time.__doc__ = time.time.__doc__

def _strftime(format, *args):  return time.strftime(format, *args)
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


_main_builtins = dict(group=_group, dir=_dir, which=_which, exists=_exists,
                      isgroup=_isgroup, subgroups=_subgroups,
                      group_items=_groupitems,
                      parse_group_args=parse_group_args, pause=_pause,
                      sleep=_sleep, systime=_time, clock=_time,
                      strftime=_strftime, reload=_reload, run=_run,
                      eval=_eval, help=_help, journal=_journal,
                      save_history=save_history, show_history=show_history)

_main_builtins.update(utils._larch_builtins)
_main_builtins.update(show_builtins)


# names to fill in the larch namespace at startup
init_builtins = dict(_builtin=_main_builtins)

# functions to run (with signature fcn(_larch)) at interpreter startup
init_funcs = [init_display_group]

# group/classes to register for save-restore
init_moddocs = {}

for mod in __core_modules:
    if mod is None:
        continue
    modname  = getattr(mod, '_larch_name', mod.__name__)
    if modname.startswith('larch.'):
        modname = modname.replace('larch.', '_')

    doc = getattr(mod, '__DOC__', None)
    if doc is not None:
        init_moddocs[modname] = doc
    builtins = getattr(mod, '_larch_builtins', {})
    init_fcn = getattr(mod, '_larch_init', None)

    for key, val in builtins.items():
        if key not in init_builtins:
            init_builtins[key] = val
        else:
            init_builtins[key].update(val)

    if init_fcn is not None:
        init_funcs.append(init_fcn)

# list of supported valid commands -- don't need parentheses for these
valid_commands = ['run', 'help', 'show', 'which', 'more', 'cd']
