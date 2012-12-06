#!/usr/bin/env python
"""
 json utilities for larch objects
"""

import larch
from larch import isParameter, Parameter, Group

import numpy as np
import json

def json_encode(name, symtable=None):
    """
    return json encoded object from larch symbol table
    """
    if symtable is None:
        return None
    if not symtable.has_symbol(name):
        return None
    obj = symtable.get_symbol(name)
    if isinstance(obj, np.ndarray):
        out = {'__class__': 'Array', '__shape__': obj.shape,
               '__dtype__': obj.dtype.name}
        out['value'] = json.dumps(obj.tolist())
    elif symtable.isgroup(obj):
        out = {'__class__': 'Group'}
        for member in dir(obj):
            try:
                out[member] = json_encode(getattr(obj, member))
            except:
                pass
        return out
    elif isParameter(obj):
        out = {'__class__': 'Parameter'}
        for attr in ('value', 'name', 'vary', 'min', 'max', 'expr'):
            val = getattr(obj, attr, None)
            if val is not None:
                out[attr] = val
    else:
        try:
            out = json.dumps(obj)
        except:
            try:
                out = json.dumps(repr(obj))
            except:
                out = None
    return out

def json_decode(value, _larch=None):
    """
    return json decoded object from larch symbol table
    for Parameter decoding, a non-None larch instance
    must be passed in
    """
    out = None
    if isinstance(value, dict):
        classname = value.get('__class__', None)
        if classname == 'Array':
            out = np.fromiter(json.loads(value['value']),
                              dtype=value['__dtype__'])
        elif classname == 'Group':
            out = Group()
            value.pop('__class__')
            for key, val in value.items():
                out[key] = json_decode(val)
        elif classname == 'Parameter':
            args = {'_larch': _larch}
            for attr in ('value', 'name', 'vary', 'min', 'max', 'expr'):
                val = value.get(attr, None)
                if attr == 'value': attr='val'
                if val is not None:
                    args[attr] = val

            out = Parameter(**args)
    if out is None:
        out = json.loads(value)
    return out

