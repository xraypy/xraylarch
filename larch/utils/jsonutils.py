#!/usr/bin/env python
"""
 json utilities for larch objects
"""
from .. import isgroup, Group
from ..fitting import isParameter, Parameter

import numpy as np

def encode4js(obj, grouplist=None):
    """return an object ready for json encoding.
    has special handling for many Python types
      numpy array
      complex numbers
      Larch Groups
      Larch Parameters

    grouplist: list of subclassed Groups to assist reconstucting the object
    """
    _groups = {}
    if grouplist is not None:
        for g in grouplist:
            _groups[g.__name__] = g

    if isinstance(obj, np.ndarray):
        out = {'__class__': 'Array', '__shape__': obj.shape,
               '__dtype__': obj.dtype.name}
        out['value'] = obj.flatten().tolist()

        if 'complex' in obj.dtype.name:
            out['value'] = [(obj.real).tolist(), (obj.imag).tolist()]
        elif obj.dtype.name == 'object':
            out['value'] = [encode4js(i, grouplist=grouplist) for i in out['value']]

        return out
    elif isinstance(obj, (np.float, np.int)):
        return float(obj)
    elif isinstance(obj, str):
        return str(obj)
    elif isinstance(obj, np.complex):
        return {'__class__': 'Complex', 'value': (obj.real, obj.imag)}
    elif isgroup(obj):
        classname = 'Group'
        if obj.__class__.__name__ in _groups:
            classname = obj.__class__.__name__
        out = {'__class__': classname}
        for item in dir(obj):
            out[item] = encode4js(getattr(obj, item), grouplist=grouplist)
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
        val = [encode4js(item, grouplist=grouplist) for item in obj]
        return {'__class__': ctype, 'value': val}
    elif isinstance(obj, dict):
        out = {'__class__': 'Dict'}
        for key, val in obj.items():
            out[encode4js(key, grouplist=grouplist)] = encode4js(val, grouplist=grouplist)
        return out
    elif callable(obj):
        return {'__class__': 'Method', '__name__': repr(obj)}

    return obj

def decode4js(obj, grouplist=None):
    """
    return decoded Python object from encoded object.

    grouplist: list of subclassed Groups to assist reconstucting the object
   """
    if not isinstance(obj, dict):
        return obj
    out = obj
    classname = obj.pop('__class__', None)
    if classname is None:
        return obj

    _groups = {'Group': Group, 'Parameter': Parameter}
    if grouplist is not None:
        for g in grouplist:
            _groups[g.__name__] = g
    if classname == 'Complex':
        out = obj['value'][0] + 1j*obj['value'][1]
    elif classname in ('List', 'Tuple'):
        out = []
        for item in obj['value']:
            out.append(decode4js(item, grouplist))
        if classname == 'Tuple':
            out = tuple(out)
    elif classname == 'Array':
        if obj['__dtype__'].startswith('complex'):
            re = np.fromiter(obj['value'][0], dtype='double')
            im = np.fromiter(obj['value'][1], dtype='double')
            out = re + 1j*im
        elif obj['__dtype__'].startswith('object'):
            val = [decode4js(v, grouplist=grouplist) for v in obj['value']]
            out = np.array(val,  dtype=obj['__dtype__'])

        else:
            out = np.fromiter(obj['value'], dtype=obj['__dtype__'])
        out.shape = obj['__shape__']
    elif classname in ('Dict', 'dict'):
        out = {}
        for key, val in obj.items():
            out[key] = decode4js(val, grouplist)
    elif classname in _groups:
        out = {}
        for key, val in obj.items():
            if (isinstance(val, dict) and
                val.get('__class__', None) == 'Method' and
                val.get('__name__', None) is not None):
                pass  # ignore class methods for subclassed Groups
            else:
                out[key] = decode4js(val, grouplist)
        out = _groups[classname](**out)

    return out
