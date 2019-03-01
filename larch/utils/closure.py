#!/usr/bin/env python

import inspect

class Closure(object):
    """Give a reference to a function with arguments so that it
    can be called later, optionally changing the argument list.

    The class provids a simple callback function which is then
    executed when called as a function. It can be defined as:

       >>>def my_action(x=None):
       ...        print 'my action: x = ', x
       >>>c = Closure(my_action,x=1)

    and used as:
       >>>c()
       my action: x = 1
       >>>c(x=2)
        my action: x = 2

    The code is based on the Command class from
    J. Grayson's Tkinter book.
    """
    def __init__(self, func=None, _name=None, **kwds):
        self.func = func
        self.kwds = kwds
        self.__name__ = _name
        if _name is None:
            self.__name__ = self.func.__name__

        argspec = inspect.getfullargspec(self.func)
        self._haskwargs  = argspec.varkw is not None
        self._hasvarargs = argspec.varargs is not None
        self._argvars    = argspec.args
        self._nkws  = 0
        if argspec.defaults is not None:
            self._nkws   = len(argspec.defaults)
        self._nargs      = len(self._argvars) - self._nkws


    def __repr__(self):
        return "<function %s, file=%s>" % (self.__name__, self.__file__)

    __str__ = __repr__

    @property
    def __doc__(self):
        if self.func is not None:
            return self.func.__doc__

    @property
    def __file__(self):
        fname = getattr(self.func, '__filename__', None)
        if fname is None:
            fname = self.func.__code__.co_filename
        return fname

    def __call__(self, *args, **c_kwds):
        if self.func is None:
            return None
        kwds = self.kwds.copy()
        kwds.update(c_kwds)
        if ('_larch' in kwds and not self._haskwargs and
            '_larch' not in self._argvars):
            kwds.pop('_larch')

        ngot = len(args) + len(kwds)
        nexp = self._nargs + self._nkws
        if not self._haskwargs and (ngot > nexp):
            exc_msg = "%s expected %i arguments, got %i "
            if '_larch' in kwds and '_larch' not in self._argvars:
                ngot -= 1
                nexp -= 1
            raise TypeError(exc_msg % (self.__name__, nexp, ngot))
        return self.func(*args, **kwds)
