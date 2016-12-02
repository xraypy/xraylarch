#!/usr/bin/env python
"""
Smoothing routines

"""
from numpy import (pi, log, exp, sqrt, arange, concatenate, convolve,
                   int, abs, linalg, mat, linspace, interp, diff)

from itertools import islice

from larch_plugins.math.mathutils import index_of, index_nearest, realimag, remove_dups
from larch_plugins.math.lineshapes import gaussian, lorentzian, voigt

def lsmooth(x, sigma=1, gamma=None, form='lorentzian', npad=None):
    """convolve a 1-d array with a lorentzian, gaussian, or voigt function.

    fconvolve(x, sigma=1, gamma=None, form='lorentzian', npad=None)

    arguments:
    ------------
      x       input 1-d array for smoothing.
      sigma   primary width parameter for convolving function
      gamma   secondary width parameter for convolving function
      form    name of convolving function:
                 'lorentzian' or 'gaussian' or 'voigt' ['lorentzian']
      npad    number of padding pixels to use [length of x]

    returns:
    --------
      smoothed 1-d array with same length as input array x
    """
    if npad is None:
        npad  = len(x)
    wx = arange(2*npad)
    if form.lower().startswith('gauss'):
        win = gaussian(wx, cen=npad, sigma=sigma)
    elif form.lower().startswith('voig'):
        win = voigt(wx, cen=npad, sigma=sigma, gamma=gamma)
    else:
        win = lorentzian(wx, cen=npad, sigma=sigma)

    xax = concatenate((x[2*npad:0:-1], x, x[-1:-2*npad-1:-1]))
    out = convolve(win/win.sum(), xax, mode='valid')
    nextra = int((len(out) - len(x))/2)
    return (out[nextra:])[:len(x)]

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
    xstep = min(diff(x))
    if xstep < TINY:
        raise Warning('Cannot smooth data: must be strictly increasing ')
    npad = 5
    xmin = xstep * int( (min(x) - npad*xstep)/xstep)
    xmax = xstep * int( (max(x) + npad*xstep)/xstep)
    npts = 1 + int(abs(xmax-xmin+xstep*0.1)/xstep)
    x0  = linspace(xmin, xmax, npts)
    y0  = interp(x0, x, y)

    # put sigma in units of 1 for convolving window function
    sigma *= 1.0 / xstep
    if gamma is not None:
        gamma *= 1.0 / xstep

    wx = arange(2*npts)
    if form.lower().startswith('gauss'):
        win = gaussian(wx, cen=npts, sigma=sigma)
    elif form.lower().startswith('voig'):
        win = voigt(wx, cen=npts, sigma=sigma, gamma=gamma)
    else:
        win = lorentzian(wx, cen=npts, sigma=sigma)

    y1 = concatenate((y0[npts:0:-1], y0, y0[-1:-npts-1:-1]))
    y2 = convolve(win/win.sum(), y1, mode='valid')
    if len(y2) > len(x0):
        nex = int((len(y2) - len(x0))/2)
        y2 = (y2[nex:])[:len(x0)]
    return interp(x, x0, y2)


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
    except ValueError(msg):
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = linalg.pinv(b).A[deriv]
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + abs(y[-half_window-1:-1][::-1] - y[-1])
    y = concatenate((firstvals, y, lastvals))
    return convolve( m, y, mode='valid')


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



def registerLarchPlugin():
    return ('_math', {'savitzky_golay': savitzky_golay,
                      'smooth': smooth,
                      'boxcar': boxcar})
