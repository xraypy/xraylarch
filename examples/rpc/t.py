import larch
from larch import isParameter, Group, Interpreter
import numpy as np

# from larch.utils.jsonutils import json_encode
import json
def json_encode(expr, _larch=None):
    """
    return json encoded larch expression
    """
    print( 'Encode ', expr)
    def _get(expr, _larch=None):
        if _larch is None:
            return None
        obj = _larch.eval(expr)
        print( ' .. get ', obj)
        if isinstance(obj, np.ndarray):
            out = {'__class__': 'Array', '__shape__': obj.shape,
                   '__dtype__': obj.dtype.name}
            out['value'] = obj.tolist()
            return out
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
        elif isinstance(obj, basestring):
            return '%s' % obj
        else:
            return obj
    return json.dumps(_get(expr, _larch=_larch))


def json_decode(value, _larch=None):
    """
    return json decoded object from larch symbol table
    for Parameter decoding, a non-None larch instance
    must be passed in
    """
    out = None
    if isinstance(value, basestring):
        try:
            value = json.loads(value)
        except ValueError:
            return value

    if isinstance(value, dict):
        classname = value.get('__class__', None)
        if classname == 'Array':
            out = np.fromiter(value['value'],
                              dtype=value['__dtype__'])
        elif classname == 'Group':
            out = Group()
            value.pop('__class__')
            for key, val in value.items():
                print( 'Key ', key, val)
                setattr(out, key,  json_decode(val))
        elif classname == 'Parameter':
            args = {'_larch': _larch}
            for attr in ('value', 'name', 'vary', 'min', 'max', 'expr'):
                val = value.get(attr, None)
                if val is not None:
                    args[attr] = val

            out = Parameter(**args)
    else:
        out = value
    return out

_larch = larch.Interpreter()
_larch.eval("x = 'a string'")
_larch.eval("y = 77")
_larch.eval("g = group(a=1.1, s='hello')") # , b='a string')")

print( json.loads(json_encode('x', _larch=_larch)))
print( json.loads(json_encode('y', _larch=_larch)))
print( json.loads(json_encode('g', _larch=_larch)))
out = json_decode(json_encode('g', _larch=_larch))
print( out)
for a in dir(out): print( a, getattr(out, a))
