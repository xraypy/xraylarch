#!/usr/bin/env python
"""
 json utilities for larch objects
"""
import json
import io
import numpy as np
import h5py

from lmfit import Parameter, Parameters
from lmfit.model import Model, ModelResult
from lmfit.minimizer import Minimizer, MinimizerResult
from lmfit.parameter import SCIPY_FUNCTIONS

from larch import Group, isgroup
from larch.fitting import  isParameter, ParameterGroup
from larch.xafs import FeffitDataSet, FeffDatFile, FeffPathGroup, TransformGroup
from larch.utils.strutils import bytes2str, str2bytes, fix_varname


LarchGroupTypes = {'Group': Group,
                   'ParameterGroup': ParameterGroup,
                   'FeffitDataSet': FeffitDataSet,
                   'FeffDatFile':  FeffDatFile,
                   'FeffPathGroup': FeffPathGroup,
                   'TransformGroup': TransformGroup,
                   'MinimizerResult': MinimizerResult
                   }

def encode4js(obj):
    """return an object ready for json encoding.
    has special handling for many Python types
      numpy array
      complex numbers
      Larch Groups
      Larch Parameters

    grouplist: list of subclassed Groups to assist reconstucting the object
    """
    if obj is None:
        return None
    if isinstance(obj, np.ndarray):
        out = {'__class__': 'Array', '__shape__': obj.shape,
               '__dtype__': obj.dtype.name}
        out['value'] = obj.flatten().tolist()

        if 'complex' in obj.dtype.name:
            out['value'] = [(obj.real).tolist(), (obj.imag).tolist()]
        elif obj.dtype.name == 'object':
            out['value'] = [encode4js(i, grouplist=grouplist) for i in out['value']]
        return out
    elif isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    elif isinstance(obj, (float, np.float64, np.float32, int, np.int64, np.int32)):
        return float(obj)
    elif isinstance(obj, str):
        return str(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')
    elif isinstance(obj, type):
        return {'__class__': 'Type',  'value': repr(obj),
                'module': getattr(obj, '__module__', None)}
    elif isinstance(obj,(complex, np.complex128)):
        return {'__class__': 'Complex', 'value': (obj.real, obj.imag)}
    elif isinstance(obj, io.IOBase):
        return {'__class__':  'IOBasee', 'class': obj.__class__.__name__,
                'name': obj.name, 'closed': obj.closed,
                'readable': obj.readable()}
    elif isinstance(obj, h5py.File):
        return {'__class__': 'HDF5File',
                'value': (obj.name, obj.filename, obj.mode, obj.libver),
                'keys': list(obj.keys())}
    elif isinstance(obj, h5py.Group):
        return {'__class__': 'HDF5Group', 'value': (obj.name, obj.file.filename),
                'keys': list(obj.keys())}
    elif isinstance(obj, slice):
        return {'__class__': 'Slice', 'value': (obj.start, obj.stop, obj.step)}
    elif isgroup(obj):
        try:
            classname = obj.__class__.__name__
        except:
            classname = 'Group'
        out = {'__class__': classname}
        for item in dir(obj):
            out[item] = encode4js(getattr(obj, item))
        return out
    elif isinstance(obj, MinimizerResult):
        out = {'__class__': 'MinimizerResult'}
        for attr in ('aborted', 'aic', 'bic', 'call_kws', 'chisqr',
                     'covar', 'errorbars', 'ier', 'init_vals',
                     'init_values', 'last_internal_values',
                     'lmdif_message', 'message', 'method', 'ndata', 'nfev',
                     'nfree', 'nvarys', 'params', 'redchi', 'residual',
                     'success', 'var_names'):
            out[attr] = encode4js(getattr(obj, attr, None))
        return out

    elif isinstance(obj, Parameters):
        out = {'__class__': 'Parameters'}
        o_ast = obj._asteval
        out['unique_symbols'] = {key: encode4js(o_ast.symtable[key])
                                 for key in o_ast.user_defined_symbols()}
        out['params'] = [(p.name, p.__getstate__()) for p in obj.values()]
        return out
    elif isinstance(obj, Parameter):
        return {'__class__': 'Parameter', 'name': obj.name, 'state': obj.__getstate__()}
    elif hasattr(obj, '__getstate__'):
        return {'__class__': 'StatefulObject', 'value': obj.__getstate__()}
    elif hasattr(obj, 'dumps'):
        print("Encode Warning: using dumps for ", obj)
        return {'__class__': 'DumpableObject', 'value': obj.dumps()}
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
    elif callable(obj):
        return {'__class__': 'Method', '__name__': repr(obj)}
    else:
        print("Warning: generic object dump for ", repr(obj))
        out = {'__class__': 'Object', '__repr__': repr(obj),
               '__classname__': obj.__class__.__name__}
        for attr in dir(obj):
            if attr.startswith('__') and attr.endswith('__'):
                continue
            thing = getattr(obj, attr)
            if not callable(thing):
                out[attr] = encode4js(thing)
        return out

    return obj

def decode4js(obj):
    """
    return decoded Python object from encoded object.

    """
    if not isinstance(obj, dict):
        return obj



    out = obj
    classname = obj.pop('__class__', None)
    if classname is None:
        return obj

    if classname == 'Complex':
        out = obj['value'][0] + 1j*obj['value'][1]
    elif classname in ('List', 'Tuple'):
        out = []
        for item in obj['value']:
            out.append(decode4js(item))
        if classname == 'Tuple':
            out = tuple(out)
    elif classname == 'Array':
        if obj['__dtype__'].startswith('complex'):
            re = np.fromiter(obj['value'][0], dtype='double')
            im = np.fromiter(obj['value'][1], dtype='double')
            out = re + 1j*im
        elif obj['__dtype__'].startswith('object'):
            val = [decode4js(v) for v in obj['value']]
            out = np.array(val,  dtype=obj['__dtype__'])

        else:
            out = np.fromiter(obj['value'], dtype=obj['__dtype__'])
        out.shape = obj['__shape__']
    elif classname in ('Dict', 'dict'):
        out = {}
        for key, val in obj.items():
            out[key] = decode4js(val)
    elif classname == 'Parameters':
        out = Parameters()
        out.clear()
        unique_symbols = {key: decode4js(obj['unique_symbols'][key]) for key
                          in obj['unique_symbols']}

        state = {'unique_symbols': unique_symbols, 'params': []}
        for name, parstate in obj['params']:
            par = Parameter(decode4js(name))
            par.__setstate__(decode4js(parstate))
            state['params'].append(par)
        out__setstate__(state)

    elif classname in ('Parameter', 'parameter'):
        name = decode4js(obj['name'])
        state = decode4js(obj['state'])
        out = Parameter(name)
        out.__setstate__(state)

    elif classname in LarchGroupTypes:
        out = {}
        for key, val in obj.items():
            if (isinstance(val, dict) and
                val.get('__class__', None) == 'Method' and
                val.get('__name__', None) is not None):
                pass  # ignore class methods for subclassed Groups
            else:
                out[key] = decode4js(val)
        out = LarchGroupTypes[classname](**out)
    elif classname == 'Method':
        mname = obj.get('__name__', '')
        if 'ufunc' in mname:
            mname = mname.replace('<ufunc', '').replace('>', '').replace("'","").strip()
        out = SCIPY_FUNCTIONS.get(mname, None)
    else:
        print("cannot decode ", classname)
    return out
