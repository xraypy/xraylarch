#!/usr/bin/env python
"""
Helper classes for larch interpreter
"""
from __future__ import division
import sys, os
import numpy as np
import traceback
import inspect
import ctypes
import ctypes.util
from .utils import Closure
from .symboltable import Group
from .site_config import sys_larchdir

class Empty:
    def __nonzero__(self): return False

# holder for 'returned None' from Larch procedure
ReturnedNone = Empty()

class LarchExceptionHolder:
    "basic exception handler"
    def __init__(self, node, msg='', fname='<stdin>',
                 func=None, expr=None, exc=None, lineno=0):
        self.node = node
        self.fname  = fname
        self.func = func
        self.expr = expr
        self.msg  = msg
        self.exc  = exc
        self.lineno = lineno
        self.exc_info = sys.exc_info()
        # extract traceback, suppressing interpreter / symboltable
        tbfull = traceback.extract_tb(self.exc_info[2])
        tb_list = []
        for tb in tbfull:
            if not (sys.prefix in tb[0] and
                    ('ast.py' in tb[0] or
                     os.path.join('larch', 'interpreter') in tb[0] or
                     os.path.join('larch', 'symboltable') in tb[0])):
                tb_list.append(tb)
        self.tback = ''.join(traceback.format_list(tb_list))
        if self.tback.endswith('\n'):
            self.tback = self.tback[:-1]

        if self.exc_info[0] is not None:
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

        # print("GET ERROR ", exc_name, e_type, e_val)
        # print(" TB :" , e_tb)
        # print(traceback.print_tb(e_tb))

        out = []
        if len(self.tback) > 0:
            out.append(self.tback)
        call_expr = None
        fname = self.fname
        fline = None
        if fname != '<stdin>' or self.lineno > 0:
            fline = 'file %s, line %i' % (fname, self.lineno)

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
            found = False
            for tb in traceback.extract_tb(self.exc_info[2]):
                found = found or tb[0].startswith(fname)
                if found:
                    u = 'File "%s", line %i, in %s\n    %s' % tb
                    words = u.split('\n')
                    fline = words[0]
                    call_expr = self.expr
                    self.expr = words[1]
                    # 'File "%s", line %i, in %s\n    %s' % tb)
            if not found and isinstance(self.func, Procedure):
                pname = self.func.name
                fline = "%s, in %s" % (fline, pname)

        if fline is not None:
            out.append(fline)

        tline = exc_name
        if self.msg not in ('',  None):
            ex_msg = getattr(e_val, 'msg', '')
            if ex_msg is '':
                ex_msg = str(self.msg)
            tline = "%s: %s" % (exc_name, ex_msg)
        if tline is not None:
            out.append(tline)

        etext = getattr(e_val, 'text', '')
        if etext not in (None, ''):
            out.append(etext)

        if call_expr is None and (self.expr == '<>' or
                                  fname not in (None, '', '<stdin>')):
            # denotes non-saved expression -- go fetch from file!
            # print 'Trying to get non-saved expr ', self.fname
            try:
                if fname is not None and os.path.exists(fname):
                    ftmp = open(fname, 'r')
                    lines = ftmp.readlines()
                    lineno = min(self.lineno, len(lines))
                    try:
                        _expr = lines[lineno][:-1]
                    except IndexError:
                        _expr = 'unknown'
                    call_expr = self.expr
                    self.expr = _expr
                    ftmp.close()
            except (IOError, TypeError):
                pass
        if self.expr is None:
            out.append('unknown error\n')
        elif '\n' in self.expr:
            out.append("\n%s" % self.expr)
        else:
            out.append("    %s" % self.expr)
        if col_offset > 0:
            if '\n' in self.expr:
                out.append("%s^^^" % ((col_offset)*' '))
            else:
                out.append("    %s^^^" % ((col_offset)*' '))
        if call_expr is not None:
            out.append('  %s' % call_expr)
        return (exc_name, '\n'.join(out))


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

    def __repr__(self):
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
        sig = "<Procedure %s(%s), file=%s>" % (self.name, sig, self.__file__)
        if self.__doc__ is not None:
            sig = "%s\n  %s" % (sig, self.__doc__)
        return sig

    def raise_exc(self, **kws):
        ekws = dict(lineno=self.lineno, func=self, fname=self.__file__)
        ekws.update(kws)
        self._larch.raise_exception(None,  **ekws)

    def __call__(self, *args, **kwargs):
        # msg = 'Cannot run Procedure %s' % self.name
        lgroup  = Group()
        lgroup.__name__ = hex(id(lgroup))
        args    = list(args)
        n_args  = len(args)
        n_names = len(self.argnames)
        n_kws   = len(kwargs)
        # may need to move kwargs to args if names align!
        if (n_args < n_names) and n_kws > 0:
            for name in self.argnames[n_args:]:
                if name in kwargs:
                    args.append(kwargs.pop(name))
            n_args = len(args)
            n_names = len(self.argnames)
            n_kws = len(kwargs)

        if len(self.argnames) > 0 and kwargs is not None:
            msg = "%s() got multiple values for keyword argument '%s'"
            for targ in self.argnames:
                if targ in kwargs:
                    self.raise_exc(exc=TypeError,
                                   msg=msg % (targ, self.name))


        if n_args != n_names:
            msg = None
            if n_args < n_names:
                msg = 'not enough arguments for %s() expected %i, got %i'
                msg = msg % (self.name, n_names, n_args)
                # print '\n >>> raise exc ', msg
                self.raise_exc(exc=TypeError, msg=msg)

        for argname in self.argnames:
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

        except (ValueError, LookupError, TypeError,
                NameError, AttributeError):
            msg = 'incorrect arguments for procedure %s' % self.name
            self.raise_exc(msg=msg)

        stable  = self._larch.symtable
        stable.save_frame()
        stable.set_frame((lgroup, self.modgroup))
        retval = None
        self._larch.retval = None
        self._larch.debug = True
        for node in self.body:
            self._larch.run(node, fname=self.__file__, func=self,
                            lineno=node.lineno+self.lineno, with_raise=False)
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
    return os.path.abspath(os.path.join(sys_larchdir, 'plugins', val))


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

    thisdir = os.path.join(sys_larchdir, 'dlls', get_dlldir())
    dirs = [thisdir]

    loaddll = ctypes.cdll.LoadLibrary

    if sys.platform == 'win32':
        loaddll = ctypes.windll.LoadLibrary
        dirs.append(sys_larchdir)

    if hasattr(sys, 'frozen'): # frozen with py2exe!!
        dirs.append(os.path.dirname(sys.executable))

    for key in _paths:
        for d in dirs:
            _paths[key] = add2path(key, d)

    dllpath = ctypes.util.find_library(libname)

    if dllpath is None:
        fname = _dylib_formats[sys.platform] % libname
        dllpath = os.path.join(thisdir, fname)

    return loaddll(dllpath)
