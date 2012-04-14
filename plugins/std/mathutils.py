#!/usr/bin/env python
"""
Some common math utilities
"""
import numpy as np

def _deriv(arr, _larch=None, **kws):
    """take numerical derivitive of an array:"""
    if not isinstance(arr, np.ndarray):
        raise Warning("cannot take derivative of non-numeric array")
    return np.gradient(arr)
#     n = len(arr)
#     out  = np.zeros(n)
#     out[0] = arr[1] - arr[0]
#     out[n-1] = arr[n-1] - arr[n-2]
#     out[1:n-2] = [(arr[i+1] - arr[i-1])/2.0 for i in range(1, n-2)]
#    return out

def _index_of(array, value):
    """return index of array *at or just below* value
    returns 0 if value < min(array)
    """
    if value < min(array):
        return 0
    return max(np.where(array<=value)[0])

def _index_nearest(array, value):
    """return index of array *nearest* to value
    """
    return np.abs(array-value).argmin()

def realimag(arr, _larch=None):
    "return real array of real/imag pairs from complex array"
    return np.array([(i.real, i.imag) for i in arr]).flatten()

def registerLarchPlugin():
    return ('_math', {'realimag': realimag,
                      'deriv': _deriv,
                      'index_of': _index_of,
                      'index_nearest': _index_nearest,
                      }
            )
