#!/usr/bin/env python
"""
Helper classes for larch interpreter
"""
from __future__ import division
import sys, os, time
import ast
import numpy as np
import traceback
import yaml
import inspect
from collections import OrderedDict
import ctypes
import ctypes.util

from .symboltable import Group, isgroup
from .site_config import user_larchdir
from .closure import Closure
from .utils import uname, bindir

HAS_TERMCOLOR = False
try:
    from termcolor import colored
    if uname == 'win':
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

        # try to get last error message, as from e_val.args
        ex_msg = getattr(e_val, 'args', None)
        try:
            ex_msg = ' '.join(ex_msg)
        except TypeError:
            pass

        if ex_msg is None:
            ex_msg = getattr(e_val, 'message', None)
        if ex_msg is None:
            ex_msg = self.msg
        out.append("%s: %s" % (exc_name, ex_msg))

        out.append("")
        return (exc_name, '\n'.join(out))



class StdWriter(object):
    """Standard writer method for Larch,
    to be used in place of sys.stdout

    supports methods:
      set_mode(mode) # one of 'text', 'text2', 'error', 'comment'
      write(text)
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
        self.textstyle = None

    def set_textstyle(self, mode='text'):
        """ set text style for output """
        if not self.has_color:
            self.textstyle = None
        display_colors = self._larch.symtable._sys.display.colors
        self.textstyle =  display_colors.get(mode, {})

    def write(self, text):
        """write text to writer
        write('hello')
        """
        if self.textstyle is not None and HAS_TERMCOLOR:
            text = colored(text, **self.textstyle)
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
        return "<Procedure %s, file=%s>" % (self.name, self.__file__)

    def _signature(self):
        sig = ""
        if len(self.argnames) > 0:
            sig = "%s%s" % (sig, ', '.join(self.argnames))
        if self.vararg is not None:
            sig = "%s, *%s" % (sig, self.vararg)
        if len(self.kwargs) > 0:
            if len(sig) > 0:
                sig = "%s, " % sig
            _kw = ["%s=%s" % (k, repr(v)) for k, v in self.kwargs]
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
                                   msg=msg % (self.name, targ))
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
        self._larch._calldepth += 1
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
        self._larch._calldepth -= 1
        self._larch.debug = False
        self._larch.retval = None
        del lgroup
        return retval

def enable_plugins():
    """add all available Larch plugin paths
    """
    # if 'larch_plugins' not in sys.modules:
    #     import larch
    #     sys.modules['larch_plugins'] = larch
    #return sys.modules['larch_plugins']
    return False

def add2path(envvar='PATH', dirname='.'):
    """add specified dir to begninng of PATH and
    DYLD_LIBRARY_PATH, LD_LIBRARY_PATH environmental variables,
    returns previous definition of PATH, for restoration"""
    sep = ':'
    if uname == 'win':
        sep = ';'
    oldpath = os.environ.get(envvar, '')
    if oldpath == '':
        os.environ[envvar] = dirname
    else:
        paths = oldpath.split(sep)
        paths.insert(0, os.path.abspath(dirname))
        os.environ[envvar] = sep.join(paths)
    return oldpath


def isNamedClass(obj, cls):
    """this is essentially a replacement for
      isinstance(obj, cls)
    that looks if an objects class name matches that of a class
    obj.__class__.__name__ == cls.__name__
    """
    return  obj.__class__.__name__ == cls.__name__

def get_dll(libname):
    """find and load a shared library"""
    _dylib_formats = {'win': '%s.dll', 'linux': 'lib%s.so',
                      'darwin': 'lib%s.dylib'}

    loaddll = ctypes.cdll.LoadLibrary
    if uname == 'win':
        loaddll = ctypes.windll.LoadLibrary

    # normally, we expect the dll to be here in the larch dlls tree
    # if we find it there, use that one
    fname = _dylib_formats[uname] % libname
    dllpath = os.path.join(bindir, fname)
    if os.path.exists(dllpath):
        return loaddll(dllpath)

    # if not found in the larch dlls tree, try your best!
    dllpath = ctypes.util.find_library(libname)
    if dllpath is not None and os.path.exists(dllpath):
        return loaddll(dllpath)
    return None


def read_workdir(conffile):
    """read working dir from a config file in the users larch dir
    compare save_workdir(conffile) which will save this value

    can be used to ensure that application startup starts in
    last working directory
    """

    try:
        w_file = os.path.join(user_larchdir, conffile)
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
        w_file = os.path.join(user_larchdir, conffile)
        fh = open(w_file, 'w')
        fh.write("%s\n" % os.getcwd())
        fh.close()
    except:
        pass


def read_config(conffile):
    """read yaml config file from users larch dir
    compare save_config(conffile) which will save such a config

    returns dictionary / configuration
    """
    cfile = os.path.join(user_larchdir, conffile)
    out = None
    if os.path.exists(cfile):
        with open(cfile, 'r') as fh:
            out = fh.read()
    if out is not None:
        try:
            out = yaml.safe_load(out)
        except:
            try:
                out = yaml.load(out, Loader=yaml.Loader)
            except:
                pass
    return out

def save_config(conffile, config):
    """write yaml config file in the users larch dir
    compare read_confif(conffile) which will read this value

    """
    cfile = os.path.join(user_larchdir, conffile)
    try:
        out = yaml.dump(config, default_flow_style=None)
        with open(cfile, 'w') as fh:
            fh.write(out)
    except:
        print(f"Could not save configuration file '{conffile:s}'")

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
            argspec = inspect.getfullargspec(fcn)

            offset = len(argspec.args) - len(argspec.defaults)
            call_args = OrderedDict()

            for k in argspec.args[:offset]:
                call_args[k] = None
            for k, v in zip(argspec.args[offset:], argspec.defaults):
                call_args[k] = v

            for iarg, arg in enumerate(args):
                call_args[argspec.args[iarg]] = arg

            call_args.update(kwargs)

            skipped = skipped_args[:]
            at0 = skipped[0]
            at1 = skipped[1]
            a, b, groupx = parse_group_args(call_args[at0],
                                            members=(at0, at1),
                                            defaults=(call_args[at1],),
                                            group=call_args['group'],
                                            fcn_name=fcn.__name__)

            for k in skipped + ['group', '_larch']:
                if k in call_args:
                    call_args.pop(k)

            if groupx is not None:
                details_name = '%s_details' % fcn.__name__
                if not hasattr(groupx, details_name):
                    setattr(groupx, details_name, Group())
                setattr(getattr(groupx, details_name),
                        'call_args', call_args)
            return result
        wrapper.__doc__ = fcn.__doc__
        wrapper.__name__ = fcn.__name__
        wrapper._larchfunc_ = fcn
        wrapper.__filename__ = fcn.__code__.co_filename
        wrapper.__dict__.update(fcn.__dict__)
        return wrapper
    return wrap

def ValidateLarchPlugin(fcn):
    """function decorator to ensure that _larch is included in keywords,
    and that it is a valid Interpeter in that it has:
    1. a symtable attribute
    2. a writer attribute
    """
    errmsg1 = "plugin function '%s' needs a '_larch' argument"
    errmsg2 = "plugin function '%s' has an invalid '_larch'  '%s'"

    def wrapper(*args, **keywords):
        "ValidateLarchPlugin"
        _larch = keywords.get('_larch', None)
        if _larch is None:
            raise LarchPluginException(errmsg1 % fcn.__name__)

        symtab = getattr(_larch, 'symtable', None)
        writer = getattr(_larch, 'writer', None)
        if not (isgroup(symtab) and callable(getattr(writer, 'write', None))):
            raise LarchPluginException(errmsg2 % (fcn.__name__, _larch))
        return fcn(*args, **keywords)
    wrapper.__doc__ = fcn.__doc__
    wrapper.__name__ = fcn.__name__
    wrapper._larchfunc_ = fcn
    wrapper.__filename__ = fcn.__code__.co_filename
    wrapper.__dict__.update(fcn.__dict__)
    return wrapper


def ensuremod(_larch, modname=None):
    "ensure that a group exists"
    if _larch is not None:
        symtable = _larch.symtable
        if modname is not None and not symtable.has_group(modname):
            symtable.newgroup(modname)
        return symtable
