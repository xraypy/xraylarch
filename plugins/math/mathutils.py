#!/usr/bin/env python
"""
Some common math utilities
"""
import numpy as np
import scipy
import scipy.stats

# functions more or less directly from scipy or numpy
def linregress(x, y, _larch=None):
    return scipy.stats.linregress(x, y)
linregress.__doc__ = scipy.stats.linregress.__doc__

def polyfit(x, y, deg, rcond=None, full=False, _larch=None):
    return scipy.polyfit(x, y, deg, rcond=rcond, full=full)
polyfit.__doc__ = scipy.polyfit.__doc__

def _deriv(arr, _larch=None, **kws):
    if not isinstance(arr, np.ndarray):
        raise Warning("cannot take derivative of non-numeric array")
    return np.gradient(arr)
_deriv.__doc__ = np.gradient.__doc__

def as_ndarray(obj):
    """make sure a float, int, list of floats or ints,
    or tuple of floats or ints, acts as a numpy array
    """
    if isinstance(obj, (float, int)):
        return np.array([obj])
    return np.asarray(obj)

def index_of(array, value):
    """return index of array *at or below* value
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
    d   = np.diff(phase)/np.pi
    out = 1.0*phase[:]
    out[1:] -= np.pi*(np.round(abs(d))*np.sign(d)).cumsum()
    return out

def remove_dups(arr, tiny=1.e-8, frac=0.02):
    """avoid repeated successive values of an array that is expected
    to be monotonically increasing.

    For repeated values, the first encountered occurance (at index i)
    will be reduced by an amount that is the largest of these:

    [tiny, frac*abs(arr[i]-arr[i-1]), frac*abs(arr[i+1]-arr[i])]

    where tiny and frac are optional arguments.

    Parameters
    ----------
    arr :  array of values expected to be monotonically increasing
    tiny : smallest expected absolute value of interval [1.e-8]
    frac : smallest expected fractional interval   [0.02]

    Returns
    -------
    out : ndarray, strictly monotonically increasing array

    Example
    -------
    >>> x = array([0, 1.1, 2.2, 2.2, 3.3])
    >>> print remove_dups(x)
    >>> array([ 0.   ,  1.1  ,  2.178,  2.2  ,  3.3  ])

    """
    if not isinstance(arr, np.ndarray):
        try:
            arr = np.array(arr)
        except:
            print 'remove_dups: argument is not an array'
    if isinstance(arr, np.ndarray):
        shape = arr.shape
        arr   = arr.flatten()
        npts  = len(arr)
        try:
            dups = np.where(abs(arr[:-1] - arr[1:]) < tiny)[0].tolist()
        except ValueError:
            dups = []
        for i in dups:
            t = [tiny]
            if i > 0:
                t.append(frac*abs(arr[i]-arr[i-1]))
            if i < len(arr)-1:
                t.append(frac*abs(arr[i+1]-arr[i]))
            dx = max(t)
            arr[i] = arr[i] - dx
        arr.shape = shape
    return arr

def registerLarchPlugin():
    return ('_math', {'linregress': linregress,
                      'polyfit': polyfit,
                      'realimag': realimag,
                      'as_ndarray': as_ndarray,
                      'complex_phase': complex_phase,
                      'deriv': _deriv,
                      'remove_dups': remove_dups,
                      'index_of': index_of,
                      'index_nearest': index_nearest,
                      }
            )
