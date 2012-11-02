#!/usr/bin/env python
"""
Save / Restore configurations of scan objects
"""
import json

class Saveable(object):
    """mixin class to enable saving the creation of
    an object to a json string for later recreation
    """
    def __init__(self, *args, **kws):
        self.__class = self.__class__.__name__
        self.__args = args
        self.__kws = kws

    def __repr__(self):
        return self._saved_repr()

    def _saved_kws(self):
        return json.dumps(self.__kws, sort_keys=True)

    def _saved_args(self):
        return json.dumps(self.__args)

    def _saved_class(self):
        return self.__class

    def _saved_repr(self):
        return "<%s: args=%s, kws=%s>" % (self.__class,
                                          self._saved_args(),
                                          self._saved_kws())
    def _saved_state(self):
        return (self.__class, self._saved_args(), self._saved_kws())

    def __eq__(self, other):
        return (self._saved_class() == other._saved_class() and
                self._saved_args() == other._saved_args() and
                self._saved_kws() == other._saved_kws())


def unpack_args(args, kws):
    """unpacks the args, *kws for a Saveable, suitable
    for passing to object creation.

    That is for Saveable object a
        write a._saved_class(), a._saved_args(), a._saved_kws()
        to output.   Later,
          read ClassName, argstring, kwstring
        unpack as
          args, kws = unpack_args(argstring, kwstring)
        identify the ClassCreation object and run:

        newobj = ClassCreator(*args, **kws)

    """
    args = [str(u) for u in json.loads(args)]
    kws  = dict((str(k),v) for k, v in json.loads(kws).items())
    return args, kws

class TestCase(Saveable):
    def __init__(self, pvname, label=None, array=None, **kws):
        Saveable.__init__(self, pvname, label=label, array=array, **kws)

if __name__ == '__main__':
    a = TestCase('foo', label='a label')
    print a._saved_class()
    print a._saved_args()
    print a._saved_kws()

    print a

    if a._saved_class()=='TestCase':
        args, kws = unpack_args(a._saved_args(), a._saved_kws())
        b = TestCase(*args, **kws) #@ *args, **kws)
        print b
        print a == b, a is b

