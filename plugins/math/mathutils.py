#!/usr/bin/env python
"""
Some common math utilities
"""
import numpy as np
import scipy
import scipy.stats
from scipy.interpolate import interp1d, UnivariateSpline

# functions more or less directly from scipy or numpy
def linregress(x, y, _larch=None):
    return scipy.stats.linregress(x, y)
linregress.__doc__ = scipy.stats.linregress.__doc__

def polyfit(x, y, deg, rcond=None, full=False, _larch=None):
    return scipy.polyfit(x, y, deg, rcond=rcond, full=full)
polyfit.__doc__ = scipy.polyfit.__doc__


def _interp1d(x, y, xnew, kind='linear', fill_value=np.nan, _larch=None, **kws):
    """interpolate x, y array onto new x values, using one of
    linear, quadratic, or cubic interpolation

        > ynew = interp1d(x, y, xnew, kind='linear')
    arguments
    ---------
      x          original x values
      y          original y values
      xnew       new x values for values to be interpolated to  
      kind       method to use: one of 'linear', 'quadratic', 'cubic'
      fill_value value to use to fill values for out-of-range x values

    note:  unlike interp, this version will not extrapolate for values of `xnew` 
           that are outside the range of `x` -- it will use NaN or `fill_value`.
           this is a bare-bones wrapping of scipy.interpolate.interp1d.

    see also: interp
    """
    kwargs  = {'kind': kind, 'fill_value': fill_value,
               'copy': False, 'bounds_error': False}
    kwargs.update(kws)
    return  interp1d(x, y, **kwargs)(xnew)


def _interp(x, y, xnew, kind='linear', fill_value=np.nan, _larch=None, **kws):
    """interpolate x, y array onto new x values, using one of
    linear, quadratic, or cubic interpolation

        > ynew = interp(x, y, xnew, kind='linear')
    arguments
    ---------
      x          original x values
      y          original y values
      xnew       new x values for values to be interpolated to  
      kind       method to use: one of 'linear', 'quadratic', 'cubic'
      fill_value value to use to fill values for out-of-range x values

    note:  unlike interp1d, this version will extrapolate for values of `xnew` 
           that are outside the range of `x`, using the polynomial order `kind`.

    see also: interp1d
    """
    kind = kind.lower()
    kwargs  = {'kind': kind, 'fill_value': fill_value,
               'copy': False, 'bounds_error': False}
    kwargs.update(kws)
    out = interp1d(x, y, **kwargs)(xnew)

    below = np.where(xnew<x[0])[0]
    above = np.where(xnew>x[-1])[0]
    if len(above) == 0 and len(below) == 0:
        return out
    for span, isbelow in ((below, True), (above, False)):
        if len(span) < 1:
            continue
        ncoef = 5
        if kind.startswith('lin'):
            ncoef = 2
        elif kind.startswith('quad'):
            ncoef = 3
        sel = slice(None, ncoef) if isbelow  else slice(-ncoef, None)
        if kind.startswith('lin'):
            coefs = scipy.polyfit(x[sel], y[sel], 1)
            out[span] = coefs[1] + coefs[0]*xnew[span]
        elif kind.startswith('quad'):
            coefs = scipy.polyfit(x[sel], y[sel], 2)
            out[span] = coefs[2] + xnew[span]*(coefs[1] + coefs[0]*xnew[span])
        elif kind.startswith('cubic'):
            out[span] = UnivariateSpline(x[sel], y[sel], s=0)(xnew[span])
    return out
    
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

def index_of(arrval, value):
    """return index of array *at or below* value
    returns 0 if value < min(array)
    """
    if value < min(arrval):
        return 0
    return max(np.where(arrval<=value)[0])

def index_nearest(array, value, _larch=None):
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
            print( 'remove_dups: argument is not an array')
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


def remove_nans2(a, b):
    """removes NAN and INF from 2 arrays,
    returning 2 arrays of the same length
    with NANs and INFs removed

    Parameters
    ----------
    a :      array 1
    b :      array 2
    
    Returns
    -------
    anew, bnew

    Example
    -------
    >>> x = array([0, 1.1, 2.2, nan, 3.3])
    >>> y = array([1,  2,   3,   4,   5)
    >>> emove_nans2(x, y)
    >>> array([ 0.   ,  1.1, 2.2, 3.3]), array([1, 2, 3, 5])

    """
    if not isinstance(a, np.ndarray):
        try:
            a = np.array(a)
        except:
            print( 'remove_nans2: argument 1 is not an array')
    if not isinstance(b, np.ndarray):
        try:
            b = np.array(b)
        except:
            print( 'remove_nans2: argument 2 is not an array')
    if (np.any(np.isinf(a)) or np.any(np.isinf(b)) or
        np.any(np.isnan(a)) or np.any(np.isnan(b))):
        a1 = a[:]
        b1 = b[:]
        if np.any(np.isinf(a)):
            bad = np.where(a==np.inf)[0]
            a1 = np.delete(a1, bad)
            b1 = np.delete(b1, bad)
        if np.any(np.isinf(b)):
            bad = np.where(b==np.inf)[0]
            a1 = np.delete(a1, bad)
            b1 = np.delete(b1, bad)            
        if np.any(np.isnan(a)):
            bad = np.where(a==np.nan)[0]
            a1 = np.delete(a1, bad)
            b1 = np.delete(b1, bad)            
        if np.any(np.isnan(b)):
            bad = np.where(b==np.nan)[0]
            a1 = np.delete(a1, bad)
            b1 = np.delete(b1, bad)            
        return a1, b1
    return a, b

def registerLarchPlugin():
    return ('_math', {'linregress': linregress,
                      'polyfit': polyfit,
                      'realimag': realimag,
                      'as_ndarray': as_ndarray,
                      'complex_phase': complex_phase,
                      'deriv': _deriv,
                      'interp': _interp,
                      'interp1d': _interp1d,
                      'remove_dups': remove_dups,
                      'remove_nans2': remove_nans2,                      
                      'index_of': index_of,
                      'index_nearest': index_nearest,
                      }
            )
