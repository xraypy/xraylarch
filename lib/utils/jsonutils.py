#!/usr/bin/env python
"""
 json utilities for larch objects
"""

import larch
from larch import isParameter, Parameter, Group

import numpy as np
import json


def json_encode(expr, _larch=None):
    """
    return value of a larch expression ready for json encoding
    this has special handling for
      numpy array
      complex numbers
      Larch Groups
      Larch Parameters
    """
    def _get(expr, _larch=None):
        if _larch is None:
            return None
        obj = _larch.eval(expr)
        if isinstance(obj, np.ndarray):
            out = {'__class__': 'Array', '__shape__': obj.shape,
                   '__dtype__': obj.dtype.name}
            out['value'] = obj.tolist()
            if 'complex' in obj.dtype.name:
                out[value] = [(obj.real).tolist(), (obj.imag).tolist()]
            return out
        elif isinstance(obj, (np.float, np.int)):
            return float(obj)
        elif isinstance(obj, (np.str, np.unicode)):
            return str(obj)
        elif isinstance(obj, np.complex):
            return {'__class__': 'Complex', 'value': (obj.real, obj.imag)}
        elif _larch.symtable.isgroup(obj):
            out = {'__class__': 'Group'}
            for item in dir(obj):
                out[item] = _get(repr(getattr(obj, item)), _larch=_larch)
            return out
        elif isParameter(obj):
            out = {'__class__': 'Parameter'}
            for attr in ('value', 'name', 'vary', 'min', 'max',
                         'expr', 'stderr', 'correl'):
                val = getattr(obj, attr, None)
                if val is not None:
                    out[attr] = val
            return out
        elif isinstance(obj, (tuple, list)):
            ctype = 'List'
            if isinstance(obj, tuple):
                ctype = 'Tuple'
            val = [_get(repr(item), _larch=_larch) for item in obj]
            return {'__class__': ctype, 'value': val}
        else:
            return obj
    return _get(expr, _larch=_larch)


def json_decode(value, _larch=None):
    """
    return json decoded object from larch symbol table
    for Parameter decoding, a non-None larch instance
    must be passed in
    """
    if isinstance(value, basestring):
        try:
            value = json.loads(value)
        except ValueError: # happens if value is a string
            pass
    dtype = type(value)
    if isinstance(value, dict):
        dtype = 'dict %s' % value.get('__class__', 'plain')

    print "DECODE : ", dtype

    out = value

    if isinstance(value, dict):
        classname = value.get('__class__', None)
        if classname == 'Array':
            out = np.fromiter(value['value'],
                              dtype=value['__dtype__'])
        elif classname == 'Group':
            out = Group()
            value.pop('__class__')
            for key, val in value.items():
                setattr(out, key,  json_decode(val))
        elif classname == 'Parameter':
            args = {'_larch': _larch}
            for attr in ('value', 'name', 'vary', 'min', 'max', 'expr'):
                val = value.get(attr, None)
                if val is not None:
                    args[attr] = val
            out = Parameter(**args)
        elif classname == 'Tuple':
            out = tuple(out['value'])
    return out
