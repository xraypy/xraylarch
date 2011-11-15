""" Builtins for larch"""

import os
import imp
import sys
from helper import Helper
from . import inputText
from . import site_config

helper = Helper()

# inherit these from python's __builtins__
from_builtin = ('ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'BufferError', 'BytesWarning',
                'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'False', 'FloatingPointError',
                'GeneratorExit', 'IOError', 'ImportError', 'ImportWarning',
                'IndentationError', 'IndexError', 'KeyError',
                'KeyboardInterrupt', 'LookupError', 'MemoryError',
                'NameError', 'None', 'NotImplemented',
                'NotImplementedError', 'OSError', 'OverflowError',
                'ReferenceError', 'RuntimeError', 'RuntimeWarning',
                'StandardError', 'StopIteration', 'SyntaxError',
                'SyntaxWarning', 'SystemError', 'SystemExit', 'True',
                'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError',
                'UnicodeTranslateError', 'UnicodeWarning', 'ValueError',
                'Warning', 'ZeroDivisionError', 'abs', 'all', 'any',
                'apply', 'basestring', 'bin', 'bool', 'buffer',
                'bytearray', 'bytes', 'callable', 'chr', 'cmp', 'coerce',
                'complex', 'delattr', 'dict', 'dir', 'divmod', 'enumerate',
                'file', 'filter', 'float', 'format', 'frozenset',
                'getattr', 'hasattr', 'hash', 'hex', 'id', 'int',
                'isinstance', 'len', 'list', 'map', 'max', 'min',
                'oct', 'open', 'ord', 'pow', 'property', 'range',
                'raw_input', 'reduce', 'repr', 'reversed', 'round', 'set',
                'setattr', 'slice', 'sorted', 'str', 'sum', 'tuple',
                'type', 'unichr', 'unicode', 'zip')

# inherit these from math (many will be overridden by numpy

from_math = ('acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2', 'atanh',
            'ceil', 'copysign', 'cos', 'cosh', 'degrees', 'e', 'exp', 'fabs',
            'factorial',
            'floor', 'fmod', 'frexp', 'fsum', 'hypot', 'isinf',
            'isnan', 'ldexp', 'log', 'log10', 'log1p', 'modf', 'pi', 'pow',
            'radians', 'sin',  'sinh', 'sqrt', 'tan', 'tanh', 'trunc')

# inherit these from numpy

from_numpy = ('ComplexWarning', 'Inf', 'NAN', 'abs', 'absolute', 'add',
              'alen', 'all', 'allclose', 'alltrue', 'alterdot', 'amax',
              'amin', 'angle', 'any', 'append', 'apply_along_axis',
              'apply_over_axes', 'arange', 'arccos', 'arccosh', 'arcsin',
              'arcsinh', 'arctan', 'arctan2', 'arctanh', 'argmax',
              'argmin', 'argsort', 'argwhere', 'around', 'array',
              'array2string', 'array_equal', 'array_equiv', 'array_repr',
              'array_split', 'array_str', 'asanyarray', 'asarray',
              'asarray_chkfinite', 'ascontiguousarray', 'asfarray',
              'asfortranarray', 'asmatrix', 'asscalar', 'atleast_1d',
              'atleast_2d', 'atleast_3d', 'average', 'bartlett',
              'base_repr', 'bench', 'binary_repr', 'bincount',
              'bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor',
              'blackman', 'bmat', 'bool', 'bool8', 'bool_', 'broadcast',
              'broadcast_arrays', 'byte', 'byte_bounds', 'bytes_', 'c_',
              'can_cast', 'cast', 'cdouble', 'ceil', 'cfloat', 'char',
              'character', 'chararray', 'choose', 'clip', 'clongdouble',
              'clongfloat', 'column_stack', 'common_type',
              'compare_chararrays', 'compat', 'complex', 'complex128',
              'complex256', 'complex64', 'complex_', 'complexfloating',
              'compress', 'concatenate', 'conj', 'conjugate', 'convolve',
              'copy', 'copysign', 'core', 'corrcoef', 'correlate', 'cos',
              'cosh', 'cov', 'cross', 'csingle', 'ctypeslib', 'cumprod',
              'cumproduct', 'cumsum', 'datetime_data', 'deg2rad',
              'degrees', 'delete', 'deprecate', 'deprecate_with_doc',
              'diag', 'diag_indices', 'diag_indices_from', 'diagflat',
              'diagonal', 'diff', 'digitize', 'disp', 'divide', 'dot',
              'double', 'dsplit', 'dstack', 'dtype', 'e', 'ediff1d',
              'emath', 'empty', 'empty_like', 'equal', 'errstate', 'exp',
              'exp2', 'expand_dims', 'expm1', 'extract', 'eye', 'fabs',
              'fastCopyAndTranspose', 'fft', 'fill_diagonal',
              'find_common_type', 'finfo', 'fix', 'flatiter',
              'flatnonzero', 'flexible', 'fliplr', 'flipud', 'float',
              'float128', 'float32', 'float64', 'float_', 'floating',
              'floor', 'floor_divide', 'fmax', 'fmin', 'fmod',
              'format_parser', 'frexp', 'frombuffer', 'fromfile',
              'fromfunction', 'fromiter', 'frompyfunc', 'fromregex',
              'fromstring', 'fv', 'generic', 'genfromtxt',
              'get_array_wrap', 'get_include', 'get_numarray_include',
              'get_numpy_include', 'get_printoptions', 'getbuffer',
              'getbufsize', 'geterr', 'geterrcall', 'geterrobj',
              'gradient', 'greater', 'greater_equal', 'hamming', 'hanning',
              'histogram', 'histogram2d', 'histogramdd', 'hsplit',
              'hstack', 'hypot', 'i0', 'identity', 'iinfo', 'imag', 'in1d',
              'index_exp', 'indices', 'inexact', 'inf', 'info', 'infty',
              'inner', 'insert', 'int', 'int0', 'int16', 'int32', 'int64',
              'int8', 'int_', 'int_asbuffer', 'intc', 'integer', 'interp',
              'intersect1d', 'intersect1d_nu', 'intp', 'invert', 'ipmt',
              'irr', 'iscomplex', 'iscomplexobj', 'isfinite', 'isfortran',
              'isinf', 'isnan', 'isneginf', 'isposinf', 'isreal',
              'isrealobj', 'isscalar', 'issctype', 'issubclass_',
              'issubdtype', 'issubsctype', 'iterable', 'ix_', 'kaiser',
              'kron', 'ldexp', 'left_shift', 'less', 'less_equal',
              'lexsort', 'lib', 'linalg', 'linspace', 'little_endian',
              'load', 'loads', 'loadtxt', 'log', 'log10', 'log1p', 'log2',
              'logaddexp', 'logaddexp2', 'logical_and', 'logical_not',
              'logical_or', 'logical_xor', 'logspace', 'long',
              'longcomplex', 'longdouble', 'longfloat', 'longlong',
              'lookfor', 'ma', 'mafromtxt', 'mask_indices', 'mat', 'math',
              'matrix', 'matrixlib', 'max', 'maximum', 'maximum_sctype',
              'may_share_memory', 'mean', 'median', 'memmap', 'meshgrid',
              'mgrid', 'min', 'minimum', 'mintypecode', 'mirr', 'mod',
              'modf', 'msort', 'multiply', 'nan', 'nan_to_num',
              'nanargmax', 'nanargmin', 'nanmax', 'nanmin', 'nansum',
              'nbytes', 'ndarray', 'ndenumerate', 'ndfromtxt', 'ndim',
              'ndindex', 'negative', 'newaxis', 'newbuffer', 'nextafter',
              'nonzero', 'not_equal', 'nper', 'npv', 'number',
              'obj2sctype', 'object', 'object0', 'object_', 'ogrid',
              'ones', 'ones_like', 'outer', 'packbits', 'percentile', 'pi',
              'piecewise', 'pkgload', 'place', 'pmt', 'poly', 'poly1d',
              'polyadd', 'polyder', 'polydiv', 'polyfit', 'polyint',
              'polymul', 'polynomial', 'polysub', 'polyval', 'power',
              'ppmt', 'prod', 'product', 'ptp', 'put', 'putmask', 'pv',
              'r_', 'rad2deg', 'radians', 'random', 'rank', 'rate',
              'ravel', 'real', 'real_if_close', 'rec', 'recarray',
              'recfromcsv', 'recfromtxt', 'reciprocal', 'record',
              'remainder', 'repeat', 'require', 'reshape', 'resize',
              'restoredot', 'right_shift', 'rint', 'roll', 'rollaxis',
              'roots', 'rot90', 'round', 'round_', 'row_stack', 's_',
              'safe_eval', 'save', 'savetxt', 'savez', 'sctype2char',
              'sctypeDict', 'sctypeNA', 'sctypes', 'searchsorted',
              'select', 'set_numeric_ops', 'set_printoptions',
              'set_string_function', 'setbufsize', 'setdiff1d', 'seterr',
              'seterrcall', 'seterrobj', 'setmember1d', 'setxor1d',
              'shape', 'short', 'show_config', 'sign', 'signbit',
              'signedinteger', 'sin', 'sinc', 'single', 'singlecomplex',
              'sinh', 'size', 'sometrue', 'sort', 'sort_complex', 'source',
              'spacing', 'split', 'sqrt', 'square', 'squeeze', 'std',
              'str', 'str_', 'string0', 'string_', 'subtract', 'sum',
              'swapaxes', 'take', 'tan', 'tanh', 'tensordot',
              'tile', 'trace', 'transpose', 'trapz', 'tri',
              'tril', 'tril_indices', 'tril_indices_from', 'trim_zeros',
              'triu', 'triu_indices', 'triu_indices_from', 'true_divide',
              'trunc', 'typeDict', 'typeNA', 'typecodes', 'typename',
              'ubyte', 'ufunc', 'uint', 'uint0', 'uint16', 'uint32',
              'uint64', 'uint8', 'uintc', 'uintp', 'ulonglong', 'unicode',
              'unicode0', 'unicode_', 'union1d', 'unique', 'unique1d',
              'unpackbits', 'unravel_index', 'unsignedinteger', 'unwrap',
              'ushort', 'vander', 'var', 'vdot', 'vectorize', 'version',
              'void', 'void0', 'vsplit', 'vstack', 'where', 'who', 'zeros',
              'zeros_like')

numpy_renames = {'ln':'log', 'asin':'arcsin', 'acos':'arccos',
                 'atan':'arctan', 'atan2':'arctan2', 'atanh':'arctanh',
                 'acosh':'arccosh', 'asinh':'arcsinh'}
##
## More builtin commands, to set up the larch language:
def _group(larch=None, **kws):
    """create a group"""
    group = larch.symtable.create_group()
    for key, val in kws.items():
        setattr(group, key, val)
    return group

def _show_group(gname=None, larch=None, **kws):
    """display group members"""
    if larch is None:
        raise Warning("cannot show group -- larch broken?")
    if gname is None:
        gname = '_main'
    larch.writer.write("%s\n" % larch.symtable.show_group(gname))


def _run(filename=None, larch=None, new_module=None,
         interactive=False,   printall=False):
    """execute the larch text in a file as larch code. options:
       larch:       larch interpreter instance
       new_module:  create new "module" frame
       printall:    whether to print all outputs
    """
    if larch is None:
        raise Warning("cannot run file '%s' -- larch broken?" % filename)

    symtable = larch.symtable
    text     = None
    if isinstance(filename, file):
        text = filename.read()
        filename = filename.name
    elif (isinstance(filename, str) and
          os.path.exists(filename) and
          os.path.isfile(filename)):
        text = open(filename).read()

    output = None
    if text is not None:
        inptext = inputText.InputText(interactive=interactive)
        is_complete = inptext.put(text, filename=filename)
        if new_module is not None:
            # save current module group
            #  create new group, set as moduleGroup and localGroup
            symtable.save_frame()
            thismod = symtable.create_group(name=new_module)
            symtable._sys.modules[new_module] = thismod
            symtable.set_frame((thismod, thismod))

        output = []
        while inptext:
            block, fname, lineno = inptext.get()
            ret = larch.eval(block, fname=fname, lineno=lineno)
            if hasattr(ret, '__call__') and not isinstance(ret, type):
                try:
                    if 1 == len(block.split()):
                        ret = ret()
                except:
                    pass
            if larch.error:
                break
        if not is_complete:
            larch.raise_exception(None,
                                  msg='Syntax Error -- input incomplete',
                                  expr="\n".join(inptext.block),
                                  fname=fname, lineno=lineno)

        if larch.error:
            err = larch.error.pop(0)
            fname, lineno = err.fname, err.lineno
            output.append("%s:\n%s" % err.get_error())
            for err in larch.error:
                if ((err.fname != fname or err.lineno != lineno) and
                    err.lineno > 0 and lineno > 0):
                    output.append("%s" % (err.get_error()[1]))
            larch.raise_exception(None,
                                  msg='Syntax Error -- input incomplete',
                                  expr="\n".join(inptext.block),
                                  fname=fname, lineno=lineno)
            inptext.clear()
        elif printall and ret is not None:
            output.append("%s" % ret)

        # for a "newly created module" (as on import),
        # the module group is the return value
        if new_module is not None:
            symtable.restore_frame()
            output = thismod
        elif len(output) > 0:
            output = "\n".join(output)
        else:
            output = None
    return output


def _reload(mod, larch=None, **kws):
    """reload a module, either larch or python"""
    if larch is None: return None
    modname = None
    if mod in larch.symtable._sys.modules.values():
        for k, v in larch.symtable._sys.modules.items():
            if v == mod:
                modname = k
    elif mod in sys.modules.values():
        for k, v in sys.modules.items():
            if v == mod:
                modname = k
    elif (mod in larch.symtable._sys.modules.keys() or
          mod in sys.modules.keys()):
        modname = mod

    if modname is not None:
        return larch.import_module(modname, do_reload=True)

def _help(*args, **kws):
    "show help on topic or object"
    helper.buffer = []
    larch = kws.get('larch', None)
    if helper.larch is None and larch is not None:
        helper.larch = larch
    if args == ('',):
        args = ('help',)
    if helper.larch is None:
        helper.addtext('cannot start help system!')
    else:
        for a in args:

            helper.help(a.strip())

    if helper.larch is not None:
        helper.larch.writer.write("%s\n" % helper.getbuffer())
    else:
        return helper.getbuffer()


def _addplugin(plugin, system=False, larch=None, **kws):
    """add plugin components from plugin directory"""
    if larch is None:
        raise Warning("cannot add plugind. larch broken?")

    errmsg = 'is not a valid larch plugin\n'
    pjoin = os.path.join

    p_path = site_config.usr_plugins_dir
    if system:
        p_path = site_config.sys_plugins_dir
    def _plugin_file(plugin, p_path):
        is_package, fh, desc = False, None, [None, None, None]
        try:
            fh, modpath, desc = imp.find_module(plugin, [p_path])
        except ImportError:
            is_package = os.path.isdir(pjoin(p_path, plugin))
        if is_package or (desc[2] == imp.PKG_DIRECTORY):
            moddir = pjoin(p_path, plugin)
            for fname in os.listdir(moddir):
                if fname.endswith('.py') and len(fname) > 3:
                    try:
                        _plugin_file(fname[:-3], moddir)
                    except Warning:
                        larch.writer.write(' Warning: %s %s' %
                                           (pjoin(moddir, fname), errmsg))
                        
        else:
            out = imp.load_module(plugin, fh, modpath, desc)
            larch.symtable.add_plugin(out, **kws)
        if fh is not None:
            fh.close()
        return
    _plugin_file(plugin, p_path)


local_funcs = {'group':_group,
               'show_group':_show_group,
               'reload':_reload,
               'run': _run,
               'help': _help,
               'add_plugin':_addplugin,
               }

