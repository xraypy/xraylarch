#!/usr/bin/env python
"""
add custom encode/decode to json for

    numpy ndarray
    np.complex
    datetime
    pathlib.Path
    tuple, namedtuple
    ioBase (files)

This is meant to complement JSONutils, and perhaps slowly replace it.

That is, still use jsonutils, but use this to replace the json encode/decode
"""

import io
import json

from collections import namedtuple
from pathlib import Path, PosixPath

from base64 import b64decode, b64encode
from functools import partial

from datetime import datetime

import numpy as np
from numpy.lib import format as npformat

def custom_encoder(obj):
    """custom json encoder, supporting
        numpy ndarray
        complex, np.complex
        datetime
        pathlib.Path
        tuple, namedtuple
        ioBase (files)
    Args:
        obj: object to be encoded

    Returns:
        dict encoding object recognizeable by json

    See Also:
        custom_decoder
    """

    from larch import Group, isgroup

    if isinstance(obj, (np.ndarray, np.generic)):
        data = obj.data if obj.flags["C_CONTIGUOUS"] else obj.tobytes()
        return {'_type_': 'b64ndarray', 'shape': obj.shape,
                'dtype': npformat.dtype_to_descr(obj.dtype),
                'value': b64encode(data).decode()}

    elif isinstance(obj, (complex, np.complex128)):
        return {'_type_': 'complex', 'value': (obj.real, obj.imag)}
    elif isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    elif isinstance(obj, (int, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (float, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')
    elif isinstance(obj, slice):
        return {'_type': 'slice', 'value': (obj.start, obj.stop, obj.step)}
    elif isinstance(obj, datetime):
        return {'_type_': 'datetime', 'isotime': obj.isoformat()}
    elif isinstance(obj, (Path, PosixPath)):
        return {'_type_': 'path', 'value': obj.as_posix()}

    elif isinstance(obj, tuple):
        out = {'_type_': 'tuple', 'value': [o for o in obj]}
        if hasattr(obj, '_fields'):  # named tuple!
            out.update({'_type_': 'namedtuple',
                        '_name': obj.__class__.__name__,
                        '_fields': obj._fields})
        return out
    elif isinstance(obj, io.IOBase):
        _writeable = False
        try:
            _wrietable = obj.writable()
        except ValueError:
            pass
        return {'_type_':  'iobase', 'class': obj.__class__.__name__,
                'name': obj.name, 'closed': obj.closed,
                'readable': obj.readable(), 'writable': _writeable}

    elif isgroup(obj):
        out = {'_type_': 'group'}
        for item in dir(obj):
            out[item] = getattr(obj, item)
        return out
    return obj

def custom_decoder(dct) :
    """Custom jdon decoder, including numpy ndarrays

    Args:
        dct (dict): dictionary to decode.

    Returns:
        decoded object or undecoded dict
    """
    from larch import Group
    tname = obj.pop('_type_', None)
    if tname is None:
        return dct

    if tname == 'b64ndarray':
        obj = np.frombuffer(b64decode(dct['value']),
                            npformat.descr_to_dtype(dctl['dtype']))
        return obj.reshape(dct['shape'])
    elif tname == 'complex':
        return complex(*dct['value'])
    elif tname == 'slice':
        return slice(*dct['value'])
    elif tname == 'datetime':
        return datetime.fromisoformat(dct['isotime'])
    elif tname == 'path':
        return Path(dct['value'])
    elif tname in ('tuple', 'namedTuple'):
        out = [o for o in dct['value']]
        if classname == 'Tuple':
            return tuple(out)
        elif classname == 'NamedTuple':
            return namedtuple(dct['_name'], dctj['_fields'])(*out)
    elif tname == 'iobase':
        mode = 'r'
        if obj['readable']  and obj['writable']:
            mode = 'a'
        elif not obj['readable']  and obj['writable']:
            mode = 'w'
        out = open(obj['name'], mode=mode)
        if obj['closed']:
            out.close()
        return out
    elif tname == 'group':
        for key, val in obj.items():
            out[key] = val
        return Group(**out)
    return dct

def dump(*args, default=None, **kws):
    """json dump, using custom encoder"""
    if default is None:
        default = custom_encoder
    return json.dump(*args, default=default, **kws)

def dumps(*args, default=None, **kws):
    """json dumps, using custom encoder"""
    if default is None:
        default = custom_encoder
    return json.dumps(*args, default=default, **kws)

def load(*args, object_hook=None, **kws):
    """json load, using custom decoder"""
    if object_hook is not None:
        object_hook = custom_decoder
    return json.load(*args, object_hook=object_hook, **kws)

def loads(*args, object_hook=None, **kws):
    """json loads, using custom decoder"""
    if object_hook is not None:
        object_hook = custom_decoder
    return json.loads(*args, object_hook=object_hook, **kws)
