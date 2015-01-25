#!/usr/bin/env python
"""
 json utilities for larch objects
"""

import larch
from larch import isParameter, Parameter, isgroup, Group

import numpy as np

def encode4js(obj):
    """return an object ready for json encoding.
    has special handling for many Python types
      numpy array
      complex numbers
      Larch Groups
      Larch Parameters
    """
    if isinstance(obj, np.ndarray):
        out = {'__class__': 'Array', '__shape__': obj.shape,
               '__dtype__': obj.dtype.name}
        out['value'] = obj.flatten().tolist()
        if 'complex' in obj.dtype.name:
            out['value'] = [(obj.real).tolist(), (obj.imag).tolist()]
        return out
    elif isinstance(obj, (np.float, np.int)):
        return float(obj)
    elif isinstance(obj, (np.str, np.unicode)):
        return str(obj)
    elif isinstance(obj, np.complex):
        return {'__class__': 'Complex', 'value': (obj.real, obj.imag)}
    elif isgroup(obj):
        out = {'__class__': 'Group'}
        for item in dir(obj):
            out[item] = encode4js(getattr(obj, item))
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
        val = [encode4js(item) for item in obj]
        return {'__class__': ctype, 'value': val}
    elif isinstance(obj, dict):
        out = {'__class__': 'Dict'}
        for key, val in obj.items():
            out[encode4js(key)] = encode4js(val)
        return out
    return obj


def decode4js(val):
    """
    return decoded Python object from encoded object.
    """
    if isinstance(val, dict):
        classname = val.pop('__class__', None)
        if classname is None:
            return val
        elif classname == 'Complex':
            return val['value'][0] + 1j*val['value'][1]
        elif classname in ('List', 'Tuple'):
            out = []
            for item in val['value']:
                out.append(decode4js(item))
            if classname == 'Tuple':
                out = tuple(out)
            return out
        elif classname == 'Array':
            if val['__dtype__'].startswith('complex'):
                re = np.fromiter(val['value'][0], dtype='double')
                im = np.fromiter(val['value'][1], dtype='double')
                out = re + 1j*im
            else:
                out = np.fromiter(val['value'],
                                  dtype=val['__dtype__'])
            out.shape = val['__shape__']
            return out
        elif classname == 'Parameter':
            args = {}
            for key, value in val.items():
                args[key] = decode4js(value)
            return Parameter(**args)
        elif classname == 'Group':
            args = {}
            for key, value in val.items():
                args[key] = decode4js(value)
            return Group(**args)
    return val

#         elif classname == 'Parameter':
#             args = {'_larch': _larch}
#             for attr in ('value', 'name', 'vary', 'min', 'max', 'expr'):
#                 val = value.get(attr, None)
#                 if val is not None:
#                     args[attr] = val
#             out = Parameter(**args)
#         elif classname == 'Tuple':
#             out = tuple(out['value'])
#     return out
