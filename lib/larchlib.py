#!/usr/bin/env python
"""
Helper classes for larch interpreter
"""
from __future__ import division
import sys, os
import numpy as np
import traceback
import inspect
from .utils import Closure
from .symboltable import Group
from .site_config import sys_larchdir

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
                    (os.path.join('larch', 'interpreter') in tb[0] or
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
            tline = "%s: %s" % (exc_name, str(self.msg))
        out.append(tline)

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
                break
        stable.restore_frame()
        self._larch.debug = False
        self._larch.retval = None
        del lgroup
        return retval

class Parameter(object):
    """returns a parameter object: a floating point value with bounds that can
    be flagged as a variable for a fit, or given an expression to use to
    automatically evaluate its value (as a thunk).

    >>> x = param(12.0, vary=True, min=0)
    will set the value to 12.0, and allow it be varied by changing x._val,
    but its returned value will never go below 0.

    >>> x = param(expr='sqrt(2*a)')
    will have a value of sqrt(2*a) even if the value of 'a' changes after
    the creation of x
    """
    __invalid = "Invalid expression for parameter: '%s'"

    def __init__(self, val=0, min=None, max=None, vary=False,
                expr=None, _larch=None, name=None, **kws):
        self._val = val
        self._initval = val
        self.vary = vary
        self.min = min
        self.max = max
        self.name = name
        self._expr = expr
        self._ast = None
        self._larch = None
        if (hasattr(_larch, 'run') and
            hasattr(_larch, 'parse') and
            hasattr(_larch, 'symtable')):
            self._larch = _larch
        if self._larch is not None and name is not None:
            self._larch.symtable.set_symbol(name, self)

    @property
    def expr(self):
        return self._expr

    @expr.setter
    def expr(self, val):
        self._ast = None
        self._expr = val

    @property
    def value(self):
        return self._getval()

    @value.setter
    def value(self, val):
        self._val = val

    def _getval(self):
        if self._larch is not None and self._expr is not None:
            if self._ast is None:
                self._expr = self._expr.strip()
                self._ast = self._larch.parse(self._expr)
                if self._ast is None:
                    self._larch.writer.write(self.__invalid % self._expr)
            if self._ast is not None:
                self._val = self._larch.run(self._ast, expr=self._expr)
                # self._larch.symtable.save_frame()
                # self._larch.symtable.restore_frame()

        if self.min is None: self.min = -np.inf
        if self.max is None: self.max =  np.inf
        if self.max < self.min:
            self.max, self.min = self.min, self.max

        try:
            if self.min > -np.inf:
               self._val = max(self.min, self._val)
            if self.max < np.inf:
                self.value = min(self.max, self._val)
        except TypeError, ValueError:
            self._val = np.nan

        return self._val

    def __hash__(self):
        return hash((self._getval(), self.min, self.max,
                     self.vary, self._expr))

    def __repr__(self):
        w = [repr(self._getval())]
        if self._expr is not None:
            w.append("expr='%s'" % self._expr)
        elif self.vary:
            w.append('vary=True')
        if self.min not in (None, -np.inf):
            w.append('min=%s' % repr(self.min))
        if self.max not in (None, np.inf):
            w.append('max=%s' % repr(self.max))
        return 'param(%s)' % ', '.join(w)

    #def __new__(self, val=0, **kws): return float.__new__(self, val)

    # these are more or less straight emulation of float,
    # but using _getval() to get current value
    def __str__(self):         return self.__repr__()

    def __abs__(self):         return abs(self._getval())
    def __neg__(self):         return -self._getval()
    def __pos__(self):         return +self._getval()
    def __nonzero__(self):     return self._getval() != 0

    def __int__(self):         return int(self._getval())
    def __long__(self):        return long(self._getval())
    def __float__(self):       return float(self._getval())
    def __trunc__(self):       return self._getval().__trunc__()

    def __add__(self, other):  return self._getval() + other
    def __sub__(self, other):  return self._getval() - other
    def __div__(self, other):  return self._getval() / other
    __truediv__ = __div__

    def __floordiv__(self, other):
        return self._getval() // other
    def __divmod__(self, other): return divmod(self._getval(), other)

    def __mod__(self, other):  return self._getval() % other
    def __mul__(self, other):  return self._getval() * other
    def __pow__(self, other):  return self._getval() ** other

    def __gt__(self, other):   return self._getval() > other
    def __ge__(self, other):   return self._getval() >= other
    def __le__(self, other):   return self._getval() <= other
    def __lt__(self, other):   return self._getval() < other
    def __eq__(self, other):   return self._getval() == other
    def __ne__(self, other):   return self._getval() != other

    def __radd__(self, other):  return other + self._getval()
    def __rdiv__(self, other):  return other / self._getval()
    __rtruediv__ = __rdiv__

    def __rdivmod__(self, other):  return divmod(other, self._getval())
    def __rfloordiv__(self, other): return other // self._getval()
    def __rmod__(self, other):  return other % self._getval()
    def __rmul__(self, other):  return other * self._getval()
    def __rpow__(self, other):  return other ** self._getval()
    def __rsub__(self, other):  return other - self._getval()

    #
    def as_integer_ratio(self):  return self._getval().as_integer_ratio()
    def hex(self):         return self._getval().hex()
    def is_integer(self):  return self._getval().is_integer()
    def real(self):        return self._getval().real()
    def imag(self):        return self._getval().imag()
    def conjugate(self):   return self._getval().conjugate()

    def __format__(self):  return format(self._getval())
    def fromhex(self, other):  self._val = other.fromhex()

    # def __getformat__(self, other):  return self._getval()
    # def __getnewargs__(self, other):  return self._getval()
    # def __reduce__(self, other):  return self._getval()
    # def __reduce_ex__(self, other):  return self._getval()
    # def __setattr__(self, other):  return self._getval()
    # def __setformat__(self, other):  return self._getval()
    # def __sizeof__(self, other):  return self._getval()

    # def __subclasshook__(self, other):  return self._getval()

def isParameter(x):
    return (isinstance(x, Parameter) or
            x.__class__.__name__ == 'Parameter')

def param_value(val):
    "get param value -- useful for 3rd party code"
    while isinstance(val, Parameter):
        val = val.value
    return val

def plugin_path(val):
    """return absolute path of a plugin folder - a convenience
    for adding these paths to sys.path, as with

    sys.path.insert(0, plugin_path('std'))
    """
    return os.path.abspath(os.path.join(sys_larchdir, 'plugins', val))
