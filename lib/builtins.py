#!/usr/bin/env python
""" Builtins for larch"""

import os
import imp
import sys
import time
import re
import traceback

import six
if six.PY3:
    import io


from .helper import Helper
from . import inputText
from . import site_config
from . import fitting
from .larchlib import parse_group_args, LarchExceptionHolder
from .symboltable import isgroup

PLUGINSTXT = 'plugins.txt'
PLUGINSREQ = 'requirements.txt'
REQMATCH = re.compile(r"(.*)\s*(<=?|>=?|==|!=)\s*(.*)", re.IGNORECASE).match

helper = Helper()

# inherit most available symbols from python's __builtins__
from_builtin = [sym for sym in __builtins__ if not sym.startswith('__')]

# inherit these from math (many will be overridden by numpy

from_math = ('acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2', 'atanh',
            'ceil', 'copysign', 'cos', 'cosh', 'degrees', 'e', 'exp',
            'fabs', 'factorial', 'floor', 'fmod', 'frexp', 'fsum', 'hypot',
            'isinf', 'isnan', 'ldexp', 'log', 'log10', 'log1p', 'modf',
            'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh',
            'trunc')

# inherit these from numpy
from_numpy = ('ComplexWarning', 'Inf', 'NAN', 'abs', 'absolute', 'add',
              'alen', 'all', 'allclose', 'alltrue', 'alterdot', 'amax',
              'amin', 'angle', 'any', 'append', 'apply_along_axis',
              'apply_over_axes', 'arange', 'arccos', 'arccosh', 'arcsin',
              'arcsinh', 'arctan', 'arctan2', 'arctanh', 'argmax',
              'argmin', 'argsort', 'argwhere', 'around', 'array',
              'asanyarray', 'asarray', 'asscalar', 'atleast_1d',
              'atleast_2d', 'atleast_3d', 'average', 'bartlett',
              'bincount', 'bitwise_and', 'bitwise_not', 'bitwise_or',
              'bitwise_xor', 'blackman', 'bmat', 'bool', 'broadcast',
              'ceil', 'chararray', 'choose', 'clip', 'column_stack',
              'common_type', 'complex', 'complex128', 'compress',
              'concatenate', 'conj', 'conjugate', 'convolve', 'copysign',
              'corrcoef', 'correlate', 'cos', 'cosh', 'cov', 'cross',
              'cumprod', 'cumproduct', 'cumsum', 'datetime_data',
              'deg2rad', 'degrees', 'delete', 'diag', 'diag_indices',
              'diag_indices_from', 'diagflat', 'diagonal', 'diff',
              'digitize', 'disp', 'divide', 'dot', 'dsplit', 'dstack',
              'dtype', 'e', 'ediff1d', 'empty', 'empty_like', 'equal',
              'errstate', 'exp', 'exp2', 'expand_dims', 'expm1', 'extract',
              'eye', 'fabs', 'fastCopyAndTranspose', 'fft',
              'fill_diagonal', 'find_common_type', 'finfo', 'fix',
              'flatiter', 'flatnonzero', 'flexible', 'fliplr', 'flipud',
              'float', 'float64', 'floor', 'floor_divide', 'fmax', 'fmin',
              'fmod', 'format_parser', 'frexp', 'frombuffer', 'fromfile',
              'fromfunction', 'fromiter', 'frompyfunc', 'fromregex',
              'fromstring', 'fv', 'genfromtxt', 'get_array_wrap',
              'get_include', 'get_numarray_include', 'get_numpy_include',
              'get_printoptions', 'getbuffer', 'getbufsize', 'geterr',
              'geterrcall', 'geterrobj', 'gradient', 'greater',
              'greater_equal', 'hamming', 'hanning', 'histogram',
              'histogram2d', 'histogramdd', 'hsplit', 'hstack', 'hypot',
              'i0', 'identity', 'iinfo', 'imag', 'in1d', 'index_exp',
              'indices', 'inexact', 'inf', 'info', 'infty', 'inner',
              'insert', 'int', 'int32', 'int_asbuffer',
              'integer', 'interp', 'intersect1d', 'intersect1d_nu',
              'invert', 'ipmt', 'irr', 'iscomplex', 'iscomplexobj',
              'isfinite', 'isinf', 'isnan', 'isneginf', 'isposinf',
              'isreal', 'isrealobj', 'isscalar', 'issctype', 'issubclass_',
              'issubdtype', 'issubsctype', 'iterable', 'kaiser', 'kron',
              'ldexp', 'left_shift', 'less', 'less_equal', 'lexsort',
              'lib', 'linalg', 'linspace', 'little_endian', 'loadtxt',
              'log', 'log10', 'log1p', 'log2', 'logaddexp', 'logaddexp2',
              'logical_and', 'logical_not', 'logical_or', 'logical_xor',
              'logspace', 'long', 'longcomplex', 'longdouble', 'longfloat',
              'longlong', 'lookfor', 'ma', 'mafromtxt', 'mask_indices',
              'mat', 'math', 'matrix', 'matrixlib', 'max', 'maximum',
              'maximum_sctype', 'may_share_memory', 'mean', 'median',
              'memmap', 'meshgrid', 'mgrid', 'min', 'minimum',
              'mintypecode', 'mirr', 'mod', 'modf', 'msort', 'multiply',
              'nan', 'nan_to_num', 'nanargmax', 'nanargmin', 'nanmax',
              'nanmin', 'nansum', 'nbytes', 'ndarray', 'ndenumerate',
              'ndfromtxt', 'ndim', 'ndindex', 'negative', 'newaxis',
              'newbuffer', 'nextafter', 'nonzero', 'not_equal', 'nper',
              'npv', 'number', 'obj2sctype', 'object', 'object0',
              'object_', 'ogrid', 'ones', 'ones_like', 'outer', 'packbits',
              'percentile', 'pi', 'piecewise', 'pkgload', 'place', 'pmt',
              'poly', 'poly1d', 'polyadd', 'polyder', 'polydiv', 'polyfit',
              'polyint', 'polymul', 'polynomial', 'polysub', 'polyval',
              'power', 'ppmt', 'prod', 'product', 'ptp', 'put', 'putmask',
              'pv', 'rad2deg', 'radians', 'random', 'rank', 'rate',
              'ravel', 'real', 'real_if_close', 'rec', 'recarray',
              'recfromcsv', 'recfromtxt', 'reciprocal', 'record',
              'remainder', 'repeat', 'require', 'reshape', 'resize',
              'restoredot', 'right_shift', 'rint', 'roll', 'rollaxis',
              'roots', 'rot90', 'round', 'round_', 'row_stack',
              'safe_eval', 'savetxt', 'savez', 'sctype2char', 'sctypeDict',
              'sctypeNA', 'searchsorted', 'select', 'setbufsize',
              'setdiff1d', 'seterr', 'seterrcall', 'seterrobj',
              'setmember1d', 'setxor1d', 'shape', 'short', 'show_config',
              'sign', 'signbit', 'signedinteger', 'sin', 'sinc', 'single',
              'singlecomplex', 'sinh', 'size', 'sometrue', 'sort',
              'sort_complex', 'source', 'spacing', 'split', 'sqrt',
              'square', 'squeeze', 'std', 'subtract', 'sum', 'swapaxes',
              'take', 'tan', 'tanh', 'tensordot', 'tile', 'trace',
              'transpose', 'trapz', 'tri', 'tril', 'tril_indices',
              'tril_indices_from', 'trim_zeros', 'triu', 'triu_indices',
              'triu_indices_from', 'true_divide', 'trunc', 'typeDict',
              'typeNA', 'typename', 'ubyte', 'ufunc', 'uint', 'uint32',
              'union1d', 'unique', 'unique1d', 'unpackbits',
              'unravel_index', 'unsignedinteger', 'unwrap', 'ushort',
              'vander', 'var', 'vdot', 'vectorize', 'version', 'vsplit',
              'vstack', 'where', 'who', 'zeros', 'zeros_like')

numpy_renames = {'ln':'log', 'asin':'arcsin', 'acos':'arccos',
                 'atan':'arctan', 'atan2':'arctan2', 'atanh':'arctanh',
                 'acosh':'arccosh', 'asinh':'arcsinh', 'npy_save': 'save',
                 'npy_load': 'load', 'npy_loads': 'loads', 'npy_copy': 'copy'}

##
## More builtin commands, to set up the larch language:

def _group(_larch=None, **kws):
    """create a group"""
    group = _larch.symtable.create_group()
    for key, val in kws.items():
        setattr(group, key, val)
    return group

def _eval(text=None, filename=None, _larch=None, new_module=None):
    """evaluate a string of larch text
    """
    if _larch is None:
        raise Warning("cannot eval string. larch broken?")

    if text is None:
        return None

    symtable = _larch.symtable
    lineno = 0
    output = None

    inp = inputText.InputText(_larch=_larch)
    inp.put(text, filename=filename, lineno=0)
    if not inp.complete:
        msg = "File '%s' ends with incomplete input" % (filename)
        text = None
        if len(inp.blocks) > 0 and filename is not None:
            blocktype, lineno, text = inp.blocks[0]
            msg = "File '%s' ends with un-terminated '%s'" % (filename,
                                                              blocktype)
        elif inp.saved_text is not None:
            text, fname, lineno = inp.saved_text
            msg = "File '%s' ends with incomplete statement" % (filename)
        while not inp.queue.empty():
            inp.get()
        err = LarchExceptionHolder(node=None, exc=SyntaxError, msg=msg,
                                   expr=text, fname=filename,
                                   lineno=lineno)

        _larch.error.append(err)
        symtable._sys.last_error = err

    thismod = None
    if new_module is not None:
        # save current module group
        #  create new group, set as moduleGroup and localGroup
        symtable.save_frame()
        thismod = symtable.create_group(name=new_module)
        symtable._sys.modules[new_module] = thismod
        symtable.set_frame((thismod, thismod))

    if len(_larch.error) > 0:
        inp.clear()

    complete = inp.run()
    # for a "newly created module" (as on import),
    # the module group is the return value
    # print('eval End ', new_module, output)
    if new_module is not None:
        symtable.restore_frame()

    return thismod

def _run(filename=None, new_module=None, _larch=None):
    "execute the larch text in a file as larch code."
    if _larch is None:
        raise Warning("cannot run file '%s' -- larch broken?" % filename)

    text = None
    if six.PY2:
        filetype = file
    else:
        filetype = io.IOBase
    if isinstance(filename, filetype):
        text = filename.read()
        filename = filename.name
    elif os.path.exists(filename) and os.path.isfile(filename):
        try:
            text = open(filename).read()
        except IOError:
            _larch.writer.write("cannot read file '%s'\n" % filename)
            return
    else:
        _larch.writer.write("file not found '%s'\n" % filename)
        return
    return  _eval(text=text, filename=filename, _larch=_larch,
                  new_module=new_module)

def _reload(mod, _larch=None, **kws):
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

def _help(*args, **kws):
    "show help on topic or object"
    helper.buffer = []
    _larch = kws.get('_larch', None)
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

def _addplugin(plugin, _larch=None, **kws):
    """add plugin components from plugin directory"""
    if _larch is None:
        raise Warning("cannot add plugins. larch broken?")
    write = _larch.writer.write
    errmsg = 'is not a valid larch plugin\n'
    pjoin = os.path.join
    path = site_config.plugins_path
    _sysconf = _larch.symtable._sys.config
    if not hasattr(_larch.symtable._sys, 'import_ok'):
        _larch.symtable._sys.import_ok  = True
    if not _larch.symtable._sys.import_ok:
        return

    if not hasattr(_sysconf, 'plugins_path'):
        _sysconf.plugins_path = site_config.plugins_path

    def _find_plugin(plugin, p_path):
        """find the plugin from path
        returns True, package name for packages
                False, (fh, modpath, desc) for imported modules
                None, None for Not Found
        """
        if not _larch.symtable._sys.import_ok:
            return

        if plugin == '__init__':
            return None, None
        mod, is_pkg = None, False
        try:
            mod = imp.find_module(plugin, [p_path])
        except ImportError:
            is_pkg = os.path.isdir(pjoin(p_path, plugin))

        if is_pkg or (mod is not None and
                      mod[2][2] == imp.PKG_DIRECTORY):
            return True, pjoin(p_path, plugin)
        elif mod is not None:
            return False, mod
        else:
            return None, None

    def on_error(msg):
        _larch.raise_exception(None, exc=ImportError, msg=msg)
        _larch.symtable._sys.import_ok = False

    def _check_requirements(ppath):
        """check for requirements.txt, return True only if all
        requirements are met
        """
        req_file = os.path.abspath(os.path.join(ppath, PLUGINSREQ))
        if not os.path.exists(req_file):
            return True
        if os.path.exists(req_file):
            with open(req_file, 'r') as fh:
                for line in fh.readlines():
                    line = line[:-1]
                    if line.startswith('#'):  continue
                    match = REQMATCH(line)
                    if match is None:
                        continue
                    ok = False
                    modname, cmp, req_vers = match.groups()
                    try:
                        mod = __import__(modname)
                        vers = getattr(mod, '__version__', None)
                        if   cmp == '>':  ok = vers >  req_vers
                        elif cmp == '<':  ok = vers <  req_vers
                        elif cmp == '>=': ok = vers >= req_vers
                        elif cmp == '<=': ok = vers <= req_vers
                        elif cmp == '==': ok = vers == req_vers
                        elif cmp == '=':  ok = vers == req_vers
                        elif cmp == '!=': ok = vers != req_vers
                    except:
                        ok = False
                    if not ok:
                        return False
        return True

    def _plugin_file(plugin, path=None):
        "defined here to allow recursive imports for packages"
        fh = None
        if plugin == '__init__':
            return
        if not _larch.symtable._sys.import_ok:
            return

        if path is None:
            try:
                path = _larch.symtable._sys.config.plugins_path
            except:
                path = site_config.plugins_path

        for p_path in path:
            # print(" -- find_plugin ", plugin)
            is_pkg, mod = _find_plugin(plugin, p_path)
            if is_pkg is not None:
                break
        if is_pkg is None and mod is None:
            write('Warning: plugin %s not found\n' % plugin)
            return False

        retval = True
        if is_pkg:
            if _check_requirements(plugin):
                filelist = []
                if PLUGINSTXT in sorted(os.listdir(mod)):
                    pfile = os.path.abspath(os.path.join(mod, PLUGINSTXT))
                    try:
                        with open(pfile, 'r') as pluginsfile:
                            for name in pluginsfile:
                                name = name[:-1].strip()
                                if (not name.startswith('#') and
                                    name.endswith('.py') and len(name) > 3):
                                    filelist.append(name)
                    except:
                        write("Warning:: Error reading plugin file:\n %s\n" %
                              pfile)
                if len(filelist) == 0:
                    for fname in sorted(os.listdir(mod)):
                        if fname.endswith('.py') and len(fname) > 3:
                            filelist.append(fname)

                retvals = []
                for fname in filelist:
                    if not _larch.symtable._sys.import_ok:
                        return
                    try:
                        ret =  _plugin_file(fname[:-3], path=[mod])
                    except:
                        err, exc, tback = sys.exc_info()
                        write('Warning: %s is =not= a valid plugin\n' %
                              pjoin(mod, fname))
                        write("   error:  %s\n" % (repr(sys.exc_info()[1])))
                        ret = False
                        _larch.symtable._sys.import_ok = False
                    retvals.append(ret)
                retval = all(retvals)
        else:
            fh, modpath, desc = mod
            try:
                out = imp.load_module(plugin, fh, modpath, desc)
                _larch.symtable.add_plugin(out, on_error, **kws)
            except:
                err, exc, tback = sys.exc_info()
                lineno = getattr(exc, 'lineno', 0)
                offset = getattr(exc, 'offset', 0)
                etext  = getattr(exc, 'text', '')
                emsg   = getattr(exc, 'message', '')
                try:
                    write(traceback.print_tb(tback))
                except:
                    pass
                write("""Python Error at plugin '%s', line %d
  %s %s^
%s: %s\n""" % (modpath, lineno, etext, ' '*offset, err.__name__, emsg))
                retval = False
                _larch.symtable._sys.import_ok = False

        if _larch.error:
            retval = False
            err = _larch.error.pop(0)
            fname, lineno = err.fname, err.lineno
            output = ["Error Adding Plugin %s from file %s" % (plugin, fname),
                      "%s" % (err.get_error()[1])]

            for err in _larch.error:
                if ((err.fname != fname or err.lineno != lineno) and
                    err.lineno > 0 and lineno > 0):
                    output.append("%s" % (err.get_error()[1]))
            write('\n'.join(output))

        if fh is not None:
            fh.close()
        return retval

    return _plugin_file(plugin)

def _dir(obj=None, _larch=None, **kws):
    "return directory of an object -- thin wrapper about python builtin"
    if _larch is None:
        raise Warning("cannot run dir() -- larch broken?")
    if obj is None:
        obj = _larch.symtable
    return dir(obj)

def _subgroups(obj, _larch=None, **kws):
    "return list of subgroups"
    if _larch is None:
        raise Warning("cannot run subgroups() -- larch broken?")
    if isgroup(obj):
        return obj._subgroups()
    else:
        raise Warning("subgroups() argument must be a group")

def _groupitems(obj, _larch=None, **kws):
    "returns group items as if items() method of a dict"
    if _larch is None:
        raise Warning("cannot run subgroups() -- larch broken?")
    if isgroup(obj):
        return obj._members().items()
    else:
        raise Warning("group_items() argument must be a group")

def _which(sym, _larch=None, **kws):
    "return full path of object, or None if object cannot be found"
    if _larch is None:
        raise Warning("cannot run which() -- larch broken?")
    stable = _larch.symtable
    if hasattr(sym, '__name__'):
        sym = sym.__name__
    if isinstance(sym, six.string_types) and stable.has_symbol(sym):
        obj = stable.get_symbol(sym)
        if obj is not None:
            return '%s.%s' % (stable.get_parentpath(sym), sym)
    return None

def _exists(sym, _larch=None):
    "return True if a named symbol exists and can be found, False otherwise"
    return which(sym, _larch=_larch, **kws) is not None

def _isgroup(obj, *args, **kws):
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
    _larch = kws.get('_larch', None)
    if _larch is None:
        raise Warning("cannot run isgroup() -- larch broken?")
    stable = _larch.symtable
    if isinstance(obj, six.string_types) and stable.has_symbol(obj):
        obj = stable.get_symbol(obj)
    return isgroup(obj, *args)


def _pause(msg='Hit return to continue', _larch=None):
    if _larch is None:
        raise Warning("cannot pause() -- larch broken?")
    return raw_input(msg)

def _sleep(t=0):  return time.sleep(t)
_sleep.__doc__ = time.sleep.__doc__

def _time():  return time.time()
_time.__doc__ = time.time.__doc__

def _clock():  return time.clock()
_clock.__doc__ = time.clock.__doc__

def _strftime(format, *args):  return time.strftime(format, *args)
_strftime.__doc__ = time.strftime.__doc__

def my_eval(text, _larch=None):
    return  _eval(text=text, _larch=_larch, new_module=None)

def _ufloat(arg, _larch=None):
    return fitting.ufloat(arg)

local_funcs = {'_builtin': {'group':_group,
                            'dir': _dir,
                            'which': _which,
                            'exists': _exists,
                            'isgroup': _isgroup,
                            'subgroups': _subgroups,
                            'group_items': _groupitems,
                            'parse_group_args': parse_group_args,
                            'pause': _pause,
                            'sleep': _sleep,
                            'systime': _time,
                            'clock': _clock,
                            'strftime': _strftime,
                            'reload':_reload,
                            'run': _run,
                            'eval': my_eval,
                            'help': _help,
                            'add_plugin':_addplugin},
               '_math':{'param': fitting.param,
                        'guess': fitting.guess,
                        'confidence_intervals': fitting.confidence_intervals,
                        'confidence_report': fitting.confidence_report,
                        'f_test': fitting.f_test,
                        'chi2_map': fitting.chi2_map,
                        'is_param': fitting.is_param,
                        'isparam': fitting.is_param,
                        'minimize': fitting.minimize,
                        'ufloat': _ufloat,
                        'fit_report': fitting.fit_report},
               }

# list of supported valid commands -- don't need parentheses for these
valid_commands = ['run', 'help', 'show', 'which']

if six.PY3:
    valid_commands.append('print')
