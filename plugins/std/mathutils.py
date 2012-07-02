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

def index_of(array, value):
    """return index of array *at or just below* value
    returns 0 if value < min(array)
    """
    if value < min(array):
        return 0
    return max(np.where(array<=value)[0])

def index_nearest(array, value):
    """return index of array *nearest* to value
    """
    return np.abs(array-value).argmin()

def realimag(arr, _larch=None):
    "return real array of real/imag pairs from complex array"
    return np.array([(i.real, i.imag) for i in arr]).flatten()

def complex_phase(arr, _larch=None):
    "return phase, modulo 2pi jumps"
    phase = np.arctan2(arr.imag, arr.real)
    for i in range(1, len(phase)):
        while (phase[i] - phase[i-1]) > 1.5*np.pi:
            phase[i] -= 2*np.pi
    return phase

def remove_dups(arr, tiny=1.e-12):
    "avoid repeated successive values of an array"
    if isinstance(arr, np.ndarray):
        shape = arr.shape
        arr   = arr.flatten()
        npts  = len(arr)
        try:
            dups = np.where(abs(arr[:-1] - arr[1:]) < tiny)[0].tolist()
        except ValueError:
            dups = []
        for i in dups:
            t = [2*tiny]
            if i > 0:
                t.append(0.01*abs(arr[i]-arr[i-1]))
            if i < len(arr)-1:
                t.append(0.01*abs(arr[i+1]-arr[i]))
            dx = max(t)
            arr[i] = arr[i] - dx
        arr.shape = shape
    return arr
    
def registerLarchPlugin():
    return ('_math', {'realimag': realimag,
                      'complex_phase': complex_phase,
                      'deriv': _deriv,
                      'remove_dups': remove_dups,
                      'index_of': index_of,
                      'index_nearest': index_nearest,
                      }
            )
