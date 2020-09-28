#!/usr/bin/env python
"""
Some common math utilities
"""
import numpy as np

from scipy.stats import linregress
from scipy.interpolate import UnivariateSpline
from scipy.interpolate import interp1d as scipy_interp1d

from .lineshapes import gaussian, lorentzian, voigt

def as_ndarray(obj):
    """
    make sure a float, int, list of floats or ints,
    or tuple of floats or ints, acts as a numpy array
    """
    if isinstance(obj, (float, int)):
        return np.array([obj])
    return np.asarray(obj)

def index_of(array, value):
    """
    return index of array *at or below* value
    returns 0 if value < min(array)

    >> ix = index_of(array, value)

    Arguments
    ---------
    array  (ndarray-like):  array to find index in
    value  (float): value to find index of

    Returns
    -------
    integer for index in array at or below value
    """
    if value < min(array):
        return 0
    return max(np.where(array<=value)[0])

def index_nearest(array, value):
    """
    return index of array *nearest* to value

    >>> ix = index_nearest(array, value)

    Arguments
    ---------
    array  (ndarray-like):  array to find index in
    value  (float): value to find index of

    Returns
    -------
    integer for index in array nearest value

    """
    return np.abs(array-value).argmin()

def deriv(arr):
    return np.gradient(as_ndarray(arr))
deriv.__doc__ = np.gradient.__doc__

def realimag(arr):
    "return real array of real/imag pairs from complex array"
    return np.array([(i.real, i.imag) for i in arr]).flatten()

def complex_phase(arr):
    "return phase, modulo 2pi jumps"
    phase = np.arctan2(arr.imag, arr.real)
    d   = np.diff(phase)/np.pi
    out = 1.0*phase[:]
    out[1:] -= np.pi*(np.round(abs(d))*np.sign(d)).cumsum()
    return out

def interp1d(x, y, xnew, kind='linear', fill_value=np.nan, **kws):
    """interpolate x, y array onto new x values, using one of
    linear, quadratic, or cubic interpolation

        > ynew = interp1d(x, y, xnew, kind='linear')

    Arguments
    ---------
      x          original x values
      y          original y values
      xnew       new x values for values to be interpolated to
      kind       method to use: one of 'linear', 'quadratic', 'cubic'
      fill_value value to use to fill values for out-of-range x values

    Notes
    -----
    unlike interp, this version will not extrapolate for values of `xnew`
    that are outside the range of `x` -- it will use NaN or `fill_value`.
    this is a bare-bones wrapping of scipy.interpolate.interp1d.

    see also: interp

    """
    kwargs  = {'kind': kind.lower(), 'fill_value': fill_value,
               'copy': False, 'bounds_error': False}
    kwargs.update(kws)
    return  scipy_interp1d(x, y, **kwargs)(xnew)


def interp(x, y, xnew, kind='linear', fill_value=np.nan, **kws):
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
    out = interp1d(x, y, xnew, kind=kind, fill_value=fill_value, **kws)

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
            coefs = np.polyfit(x[sel], y[sel], 1)
            out[span] = coefs[1] + coefs[0]*xnew[span]
        elif kind.startswith('quad'):
            coefs = np.polyfit(x[sel], y[sel], 2)
            out[span] = coefs[2] + xnew[span]*(coefs[1] + coefs[0]*xnew[span])
        elif kind.startswith('cubic'):
            out[span] = UnivariateSpline(x[sel], y[sel], s=0)(xnew[span])
    return out


def remove_dups(arr, tiny=1.e-7, frac=1.e-6):
    """avoid repeated successive values of an array that is expected
    to be monotonically increasing.

    For repeated values, the second encountered occurance (at index i)
    will be increased by an amount that is the largest of:
      (tiny, frac*abs(arr[i]-arr[i-1]))

    Parameters
    ----------
    arr :  array of values expected to be monotonically increasing
    tiny : smallest expected absolute value of interval [1.e-7]
    frac : smallest expected fractional interval   [1.e-6]

    Returns
    -------
    out : ndarray, strictly monotonically increasing array

    Example
    -------
    >>> x = np.array([0, 1.1, 2.2, 2.2, 3.3])
    >>> print remove_dups(x)
    >>> array([ 0.   ,  1.1  ,  2.2,  2.2000001,  3.3  ])
    """
    if not isinstance(arr, np.ndarray):
        try:
            arr = np.array(arr)
        except:
            print( 'remove_dups: argument is not an array')

    shape = arr.shape
    arr   = arr.flatten()
    npts  = len(arr)
    dups = []
    try:
        reps = np.where(abs(arr[1:-1] - arr[:-2]) < tiny)[0].tolist()
        dups.extend([i+1 for i in reps])
    except ValueError:
        pass
    if abs(arr[-1] - arr[-2]) < tiny:
        dups.append(npts-1)
    arr = arr.tolist()
    for i in range(1, len(arr)):
        t = tiny
        if i > 0:
            t = max(tiny, frac*abs(arr[i]-arr[i-1]))
        if arr[i] - arr[i-1] < tiny:
            arr[i] = arr[i-1] + t
    if abs(arr[-1] - arr[-2]) < tiny:
        arr[-1] = arr[-2] + tiny
    arr = np.array(arr)
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


def smooth(x, y, sigma=1, gamma=None, npad=None, form='lorentzian'):
    """smooth a function y(x) by convolving wih a lorentzian, gaussian,
    or voigt function.

    arguments:
    ------------
      x       input 1-d array for absicca
      y       input 1-d array for ordinate: data to be smoothed
      sigma   primary width parameter for convolving function
      gamma   secondary width parameter for convolving function
      delx    delta x to use for interpolation [mean of
      form    name of convolving function:
                 'lorentzian' or 'gaussian' or 'voigt' ['lorentzian']
      npad    number of padding pixels to use [length of x]

    returns:
    --------
      1-d array with same length as input array y
    """
    # make uniform x, y data
    TINY = 1.e-12
    xstep = min(np.diff(x))
    if xstep < TINY:
        raise Warning('Cannot smooth data: must be strictly increasing ')
    npad = 5
    xmin = xstep * int( (min(x) - npad*xstep)/xstep)
    xmax = xstep * int( (max(x) + npad*xstep)/xstep)
    npts = 1 + int(abs(xmax-xmin+xstep*0.1)/xstep)
    x0  = np.linspace(xmin, xmax, npts)
    y0  = np.interp(x0, x, y)

    # put sigma in units of 1 for convolving window function
    sigma *= 1.0 / xstep
    if gamma is not None:
        gamma *= 1.0 / xstep

    wx = np.arange(2*npts)
    if form.lower().startswith('gauss'):
        win = gaussian(wx, center=npts, sigma=sigma)
    elif form.lower().startswith('voig'):
        win = voigt(wx, center=npts, sigma=sigma, gamma=gamma)
    else:
        win = lorentzian(wx, center=npts, sigma=sigma)

    y1 = np.concatenate((y0[npts:0:-1], y0, y0[-1:-npts-1:-1]))
    y2 = np.convolve(win/win.sum(), y1, mode='valid')
    if len(y2) > len(x0):
        nex = int((len(y2) - len(x0))/2)
        y2 = (y2[nex:])[:len(x0)]
    return interp(x0, y2, x)


def savitzky_golay(y, window_size, order, deriv=0):
    #
    # code from from scipy cookbook

    """Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techhniques.
    Parameters
    ----------
    y : array_like, shape (N,)
        the values of the time history of the signal.
    window_size : int
        the length of the window. Must be an odd integer number.
    order : int
        the order of the polynomial used in the filtering.
        Must be less then `window_size` - 1.
    deriv: int
        the order of the derivative to compute (default = 0 means only smoothing)
    Returns
    -------
    ys : ndarray, shape (N)
        the smoothed signal (or it's n-th derivative).
    Notes
    -----
    The Savitzky-Golay is a type of low-pass filter, particularly
    suited for smoothing noisy data. The main idea behind this
    approach is to make for each point a least-square fit with a
    polynomial of high order over a odd-sized window centered at
    the point.
    Examples
    --------
    t = np.linspace(-4, 4, 500)
    y = np.exp( -t**2 ) + np.random.normal(0, 0.05, t.shape)
    ysg = savitzky_golay(y, window_size=31, order=4)
    import matplotlib.pyplot as plt
    plt.plot(t, y, label='Noisy signal')
    plt.plot(t, np.exp(-t**2), 'k', lw=1.5, label='Original signal')
    plt.plot(t, ysg, 'r', label='Filtered signal')
    plt.legend()
    plt.show()
    References
    ----------
    .. [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures. Analytical
       Chemistry, 1964, 36 (8), pp 1627-1639.
    .. [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
       W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
       Cambridge University Press ISBN-13: 9780521880688
    """
    try:
        window_size = abs(int(window_size))
        order = abs(int(order))
    except ValueError:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = np.linalg.pinv(b).A[deriv]
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + abs(y[-half_window-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve( m, y, mode='valid')


def boxcar(data, nrepeats=1):
    """boxcar average of an array

    Arguments
    ---------
       data     nd-array, assumed to be 1d
       nrepeats integer number of repeats [1]

    Returns
    -------
       ndarray of same size as input data

    Notes
    -----
      This does a 3-point smoothing, that can be repeated

      out = data[:]
      for i in range(nrepeats):
          qdat = out/4.0
          left  = 1.0*qdat
          right = 1.0*qdat
          right[1:] = qdat[:-1]
          left[:-1] = qdat[1:]
          out = 2*qdat + left + right
    return out

    """
    out = data[:]
    for i in range(nrepeats):
        qdat = out/4.0
        left  = 1.0*qdat
        right = 1.0*qdat
        right[1:] = qdat[:-1]
        left[:-1] = qdat[1:]
        out = 2*qdat + left + right
    return out
