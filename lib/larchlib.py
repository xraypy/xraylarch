#!/usr/bin/env python
"""
Helper classes for larch interpreter
"""
from __future__ import division
import sys, os
import ast
import numpy as np
import traceback
import inspect
import ctypes
import ctypes.util
from .utils import Closure
from .symboltable import Group, isgroup
from .site_config import larchdir, usr_larchdir

HAS_TERMCOLOR = False
try:
    from termcolor import colored
    if os.name == 'nt':
        # HACK (hopefully temporary):
        # disable color output for Windows command terminal
        # because it interferes with wx event loop.
        import CannotUseTermcolorOnWindowsWithWx
        # os.environ.pop('TERM')
        # import colorama
        # colorama.init()
    HAS_TERMCOLOR = True
except ImportError:
    HAS_TERMCOLOR = False

class LarchPluginException(Exception):
    """Exception with Larch Plugin"""
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return "\n%s" % (self.msg)

class Empty:
    def __nonzero__(self): return False

# holder for 'returned None' from Larch procedure
ReturnedNone = Empty()

def get_filetext(fname, lineno):
    """try to extract line from source text file"""
    out = '<could not find text>'
    try:
        ftmp = open(fname, 'r')
        lines = ftmp.readlines()
        ftmp.close()
        lineno = min(lineno, len(lines)) - 1
        out = lines[lineno][:-1]
    except:
        pass
    return out

class LarchExceptionHolder:
    "basic exception handler"
    def __init__(self, node=None, msg='', fname='<stdin>',
                 func=None, expr=None, exc=None, lineno=0):
        self.node = node
        self.fname  = fname
        self.func = func
        self.expr = expr
        self.msg  = msg
        self.exc  = exc
        self.lineno = lineno
        self.exc_info = sys.exc_info()

        if self.exc is None and self.exc_info[0] is not None:
            self.exc = self.exc_info[0]
        if self.msg in ('', None) and self.exc_info[1] is not None:
            self.msg = self.exc_info[1]

    def get_error(self):
        "retrieve error data"
        col_offset = -1
        e_type, e_val, e_tb = self.exc_info
        if self.node is not None:
            try:
                col_offset = self.node.col_offset
            except AttributeError:
                pass
        try:
            exc_name = self.exc.__name__
        except AttributeError:
            exc_name = str(self.exc)
        if exc_name in (None, 'None'):
            exc_name = 'UnknownError'

        out = []
        fname = self.fname

        if isinstance(self.expr, ast.AST):
            self.expr = 'In compiled script'
        if self.expr is None:
            out.append('unknown error\n')
        elif '\n' in self.expr:
            out.append("\n%s" % self.expr)
        else:
            out.append("    %s" % self.expr)
        if col_offset > 0:
            out.append("%s^^^" % ((col_offset)*' '))

        fline = '   File %s, line %i' % (fname, self.lineno)
        if self.func is not None:
            func = self.func
            fname = self.fname
            if fname is None:
                if isinstance(func, Closure):
                    func = func.func
                    fname = inspect.getmodule(func).__file__
                try:
                    fname = inspect.getmodule(func).__file__
                except AttributeError:
                    fname = 'unknown'
            if fname.endswith('.pyc'):
                fname = fname[:-1]

            if hasattr(self.func, 'name'):
                dec = ''
                if isinstance(self.func, Procedure):
                    dec = 'procedure '
                pname = self.func.name
                ftext = get_filetext(self.fname, self.lineno)
                fline = "%s, in %s%s\n%s" % (fline, dec, pname, ftext)

        if fline is not None:
            out.append(fline)

        tblist = []
        for tb in traceback.extract_tb(self.exc_info[2]):
            if not (sys.prefix in tb[0] and
                    ('ast.py' in tb[0] or
                     os.path.join('larch', 'utils') in tb[0] or
                     os.path.join('larch', 'interpreter') in tb[0] or
                     os.path.join('larch', 'symboltable') in tb[0])):
                tblist.append(tb)
        if len(tblist) > 0:
            out.append(''.join(traceback.format_list(tblist)))

        if self.msg not in ('',  None):
            ex_msg = getattr(e_val, 'message', '')
            if ex_msg is '':
                ex_msg = str(self.msg)
            out.append("%s: %s" % (exc_name, ex_msg))

        out.append("")
        return (exc_name, '\n'.join(out))


class StdWriter(object):
    """Standard writer method for Larch,
    to be used in place of sys.stdout

    supports methods:
      write(text, color=None, bkg=None, bold=Fals, reverse=False)
      flush()
    """
    valid_termcolors = ('grey', 'red', 'green', 'yellow',
                        'blue', 'magenta', 'cyan', 'white')

    termcolor_attrs = ('bold', 'underline', 'blink', 'reverse')
    def __init__(self, stdout=None, has_color=True, _larch=None):
        if stdout is None:
            stdout = sys.stdout
        self.has_color = has_color and HAS_TERMCOLOR
        self.writer = stdout
        self._larch = _larch
        self.termcolor_opts = None

    def _getcolor(self, color=None):
        if self.has_color and color in self.valid_termcolors:
            return color
        return None

    def write(self, text, color=None, bkg=None, **kws):
        """write text to writer
        write('hello', color='red', bkg='grey', bold=True, blink=True)
        """
        attrs = []
        for key, val in kws.items():
            if val and (key in self.termcolor_attrs):
                attrs.append(key)
        if self.termcolor_opts is None:
            try:
                self.termcolor_opts = \
                       self._larch.symtable._builtin.get_termcolor_opts
            except:
                pass
        if color is None:
            color_opts = {'color': None}
            if callable(self.termcolor_opts) and self._larch is not None:
                color_opts = self.termcolor_opts('text', _larch=self._larch)
            color = color_opts.pop('color')
            for key in color_opts.keys():
                if key in self.termcolor_attrs:
                    attrs.append('%s' % key)

        color = self._getcolor(color)
        if color is not None:
            bkg = self._getcolor(bkg)
            if bkg is not None:
                bkg= 'on_%s' % bkg
            text = colored(text, color, on_color=bkg, attrs=attrs)
        self.writer.write(text)

    def flush(self):
        self.writer.flush()


class Procedure(object):
    """larch procedure:  function """
    def __init__(self, name, _larch=None, doc=None,
                 fname='<stdin>', lineno=0,
                 body=None, args=None, kwargs=None,
                 vararg=None, varkws=None):
        self.name     = name
        self._larch    = _larch
        self.modgroup = _larch.symtable._sys.moduleGroup
        self.body     = body
        self.argnames = args
        self.kwargs   = kwargs
        self.vararg   = vararg
        self.varkws   = varkws
        self.__doc__  = doc
        self.lineno   = lineno
        self.__file__ = fname
        self.__name__ = name

    def __repr__(self):
        sig = self._signature()
        sig = "<Procedure %s, file=%s>" % (sig, self.__file__)
        if self.__doc__ is not None:
            sig = "%s\n  %s" % (sig, self.__doc__)
        return sig

    def _signature(self):
        sig = ""
        if len(self.argnames) > 0:
            sig = "%s%s" % (sig, ', '.join(self.argnames))
        if self.vararg is not None:
            sig = "%s, *%s" % (sig, self.vararg)
        if len(self.kwargs) > 0:
            if len(sig) > 0:
                sig = "%s, " % sig
            _kw = ["%s=%s" % (k, v) for k, v in self.kwargs]
            sig = "%s%s" % (sig, ', '.join(_kw))

            if self.varkws is not None:
                sig = "%s, **%s" % (sig, self.varkws)
        return "%s(%s)" % (self.name, sig)

    def raise_exc(self, **kws):
        ekws = dict(lineno=self.lineno, func=self, fname=self.__file__)
        ekws.update(kws)
        self._larch.raise_exception(None,  **ekws)

    def __call__(self, *args, **kwargs):
        # msg = 'Cannot run Procedure %s' % self.name
        lgroup  = Group()
        lgroup.__name__ = hex(id(lgroup))
        args    = list(args)
        nargs  = len(args)
        nkws   = len(kwargs)
        nargs_expected = len(self.argnames)
        # print("LARCHPROCCALL ", self.name)
        # print(" defn: args, kwargs ", self.argnames, self.kwargs)
        # print(" defn: vararg, varkws ", self.vararg, self.varkws)
        # print(" passed args, kws: ", args, kwargs)

        # case 1: too few arguments, but the correct keyword given
        if (nargs < nargs_expected) and nkws > 0:
            for name in self.argnames[nargs:]:
                if name in kwargs:
                    args.append(kwargs.pop(name))
            nargs = len(args)
            nargs_expected = len(self.argnames)
            nkws = len(kwargs)

        # case 2: multiple values for named argument
        if len(self.argnames) > 0 and kwargs is not None:
            msg = "%s() got multiple values for keyword argument '%s'"
            for targ in self.argnames:
                if targ in kwargs:
                    self.raise_exc(exc=TypeError,
                                   msg=msg % (targ, self.name))
                    return

        # case 3: too few args given
        if nargs < nargs_expected:
            mod = 'at least'
            if len(self.kwargs) == 0:
                mod = 'exactly'
            msg = '%s() expected %s %i arguments (got %i)'
            self.raise_exc(exc=TypeError,
                           msg=msg%(self.name, mod, nargs_expected, nargs))
            return

        # case 4: more args given than expected, varargs not given
        if nargs > nargs_expected and self.vararg is None:
            if nargs - nargs_expected > len(self.kwargs):
                msg = 'too many arguments for %s() expected at most %i, got %i'
                msg = msg % (self.name, len(self.kwargs)+nargs_expected, nargs)
                self.raise_exc(exc=TypeError, msg=msg)
                return
            for i, xarg in enumerate(args[nargs_expected:]):
                kw_name = self.kwargs[i][0]
                if kw_name not in kwargs:
                    kwargs[kw_name] = xarg

        for argname in self.argnames:
            if len(args) > 0:
                setattr(lgroup, argname, args.pop(0))
        try:
            if self.vararg is not None:
                setattr(lgroup, self.vararg, tuple(args))

            for key, val in self.kwargs:
                if key in kwargs:
                    val = kwargs.pop(key)
                setattr(lgroup, key, val)

            if self.varkws is not None:
                setattr(lgroup, self.varkws, kwargs)
            elif len(kwargs) > 0:
                msg = 'extra keyword arguments for procedure %s (%s)'
                msg = msg % (self.name, ','.join(list(kwargs.keys())))
                self.raise_exc(exc=TypeError, msg=msg)
                return

        except (ValueError, LookupError, TypeError,
                NameError, AttributeError):
            msg = 'incorrect arguments for procedure %s' % self.name
            self.raise_exc(msg=msg)
            return

        stable  = self._larch.symtable
        stable.save_frame()
        stable.set_frame((lgroup, self.modgroup))
        retval = None
        self._larch.retval = None
        self._larch.debug = True
        for node in self.body:
            self._larch.run(node, fname=self.__file__, func=self,
                            lineno=node.lineno+self.lineno-1, with_raise=False)
            if len(self._larch.error) > 0:
                break
            if self._larch.retval is not None:
                retval = self._larch.retval
                if retval is ReturnedNone: retval = None
                break
        stable.restore_frame()
        self._larch.debug = False
        self._larch.retval = None
        del lgroup
        return retval

def plugin_path(val):
    """return absolute path of a plugin folder - a convenience
    for adding these paths to sys.path, as with

    sys.path.insert(0, plugin_path('std'))
    """
    return os.path.abspath(os.path.join(larchdir, 'plugins', val))

def use_plugin_path(val):
    """include the specifed Larch plugin path in a module:

    sys.path.insert(0, plugin_path(val))
    """
    ppath = plugin_path(val)
    if ppath not in sys.path:
        sys.path.insert(0, ppath)

def enable_plugins():
    """add all available Larch plugin paths
    """
    if 'larch_plugins' not in sys.modules:
        sys.path.insert(1, os.path.abspath(larchdir))
        import plugins
        sys.modules['larch_plugins'] = plugins
    return sys.modules['larch_plugins']

def add2path(envvar='PATH', dirname='.'):
    """add specified dir to begninng of PATH and
    DYLD_LIBRARY_PATH, LD_LIBRARY_PATH environmental variables,
    returns previous definition of PATH, for restoration"""
    sep = ':'
    if os.name == 'nt':
        sep = ';'
    oldpath = os.environ.get(envvar, '')
    if oldpath == '':
        os.environ[envvar] = dirname
    else:
        paths = oldpath.split(sep)
        paths.insert(0, os.path.abspath(dirname))
        os.environ[envvar] = sep.join(paths)
    return oldpath

def get_dlldir():
    import  os, sys
    from platform import uname, architecture
    system, node, release, version, mach, processor = uname()
    arch = architecture()[0]
    dlldir = None
    suff = '32'
    if arch.startswith('64'):  suff = '64'
    if os.name == 'nt':
        return 'win%s' % suff
    elif system.lower().startswith('linux'):
        return 'linux%s' % suff
    elif system.lower().startswith('darwin'):
        return 'darwin'
    return ''

def isNamedClass(obj, cls):
    """this is essentially a replacement for
      isinstance(obj, cls)
    that looks if an objects class name matches that of a class
    obj.__class__.__name__ == cls.__name__
    """
    return  obj.__class__.__name__ == cls.__name__

def get_dll(libname):
    """find and load a shared library"""
    _paths = {'PATH': '', 'LD_LIBRARY_PATH': '', 'DYLD_LIBRARY_PATH':''}
    _dylib_formats = {'win32': '%s.dll', 'linux2': 'lib%s.so',
                      'darwin': 'lib%s.dylib'}
    thisdir = os.path.abspath(os.path.join(larchdir, 'dlls',
                                           get_dlldir()))
    dirs = [thisdir]

    loaddll = ctypes.cdll.LoadLibrary

    if sys.platform == 'win32':
        loaddll = ctypes.windll.LoadLibrary
        dirs.append(larchdir)

    if hasattr(sys, 'frozen'): # frozen with py2exe!!
        dirs.append(os.path.dirname(sys.executable))

    for key in _paths:
        for d in dirs:
            _paths[key] = add2path(key, d)

    # normally, we expect the dll to be here in the larch dlls tree
    # if we find it there, use that one
    fname = _dylib_formats[sys.platform] % libname
    dllpath = os.path.join(thisdir, fname)
    if os.path.exists(dllpath):
        return loaddll(dllpath)

    # if not found in the larch dlls tree, try your best!
    return loaddll(ctypes.util.find_library(libname))


def read_workdir(conffile):
    """read working dir from a config file in the users larch dir
    compare save_workdir(conffile) which will save this value

    can be used to ensure that application startup starts in
    last working directory
    """

    try:
        w_file = os.path.join(usr_larchdir, conffile)
        if os.path.exists(w_file):
            line = open(w_file, 'r').readlines()
            workdir = line[0][:-1]
            os.chdir(workdir)
    except:
        pass

def save_workdir(conffile):
    """write working dir to a config file in the users larch dir
    compare read_workdir(conffile) which will read this value

    can be used to ensure that application startup starts in
    last working directory
    """

    try:
        w_file = os.path.join(usr_larchdir, conffile)
        fh = open(w_file, 'w')
        fh.write("%s\n" % os.getcwd())
        fh.close()
    except:
        pass


def parse_group_args(arg0, members=None, group=None, defaults=None,
                     fcn_name=None, check_outputs=True):
    """parse arguments for functions supporting First Argument Group convention

    That is, if the first argument is a Larch Group and contains members
    named in 'members', this will return data extracted from that group.

    Arguments
    ----------
    arg0:         first argument for function call.
    members:      list/tuple of names of required members (in order)
    defaults:     tuple of default values for remaining required
                  arguments past the first (in order)
    group:        group sent to parent function, used for outputs
    fcn_name:     name of parent function, used for error messages
    check_output: True/False (default True) setting whether a Warning should
                  be raised in any of the outputs (except for the final group)
                  are None.  This effectively checks that all expected inputs
                  have been specified
    Returns
    -------
     tuple of output values in the order listed by members, followed by the
     output group (which could be None).

    Notes
    -----
    This implements the First Argument Group convention, used for many Larch functions.
    As an example, the function _xafs.find_e0 is defined like this:
       find_e0(energy, mu=None, group=None, ...)

    and uses this function as
       energy, mu, group = parse_group_arg(energy, members=('energy', 'mu'),
                                           defaults=(mu,), group=group,
                                           fcn_name='find_e0', check_output=True)

    This allows the caller to use
         find_e0(grp)
    as a shorthand for
         find_e0(grp.energy, grp.mu, group=grp)

    as long as the Group grp has member 'energy', and 'mu'.

    With 'check_output=True', the value for 'mu' is not actually allowed to be None.

    The defaults tuple should be passed so that correct values are assigned
    if the caller actually specifies arrays as for the full call signature.
    """
    if members is None:
        members = []
    if isgroup(arg0, *members):
        if group is None:
            group = arg0
        out = [getattr(arg0, attr) for attr in members]
    else:
        out = [arg0] + list(defaults)

    # test that all outputs are non-None
    if check_outputs:
        _errmsg = """%s: needs First Argument Group or valid arguments for
  %s"""
        if fcn_name is None:
            fcn_name ='unknown function'
        for i, nam in enumerate(members):
            if out[i] is None:
                raise Warning(_errmsg % (fcn_name, ', '.join(members)))

    out.append(group)
    return out

def Make_CallArgs(skipped_args):
    """
    decorator to create a 'call_args' dictionary
    containing function arguments
    """
    def wrap(fcn):
        def wrapper(*args, **kwargs):
            result = fcn(*args, **kwargs)
            call_args = inspect.getcallargs(fcn, *args, **kwargs)
            skipped = skipped_args[:]
            at0 = skipped[0]
            at1 = skipped[1]
            a, b, groupx = parse_group_args(call_args[at0],
                                            members=(at0, at1),
                                            defaults=(call_args[at1],),
                                            group=call_args['group'],
                                            fcn_name=fcn.__name__)

            for attr in ('group', '_larch'):
                if attr not in skipped: skipped.append(attr)

            for k in skipped:
                call_args.pop(k)
            details_name = '%s_details' % fcn.__name__
            if not hasattr(groupx, details_name):
                setattr(groupx, details_name, Group())
            setattr(getattr(groupx, details_name),
                    'call_args', call_args)
            return result
        wrapper.__doc__ = fcn.__doc__
        wrapper.__name__ = fcn.__name__
        wrapper._larchfunc_ = fcn
        wrapper__filename__ = fcn.__code__.co_filename
        wrapper.__dict__.update(fcn.__dict__)
        return wrapper
    return wrap

def ValidateLarchPlugin(fcn):
    """function decorator to ensure that _larch is included in keywords,
    and that it is a valid Interpeter"""
    errmsg = "plugin function '%s' needs a valid '_larch' argument"

    def wrapper(*args, **keywords):
        "ValidateLarchPlugin"
        if ('_larch' not in keywords or
            ('Interpreter' not in keywords['_larch'].__class__.__name__)):
            raise LarchPluginException(errmsg % fcn.__name__)
        return fcn(*args, **keywords)
    wrapper.__doc__ = fcn.__doc__
    wrapper.__name__ = fcn.__name__
    wrapper._larchfunc_ = fcn
    wrapper.__filename__ = fcn.__code__.co_filename
    wrapper.__dict__.update(fcn.__dict__)
    return wrapper
