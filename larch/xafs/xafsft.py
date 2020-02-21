#!/usr/bin/env python
"""
  XAFS Fourier transforms
"""
import numpy as np
from numpy import (pi, arange, zeros, ones, sin, cos,
                   exp, log, sqrt, where, interp, linspace)
# from numpy.fft import fft, ifft
from scipy.fftpack import fft, ifft
from scipy.special import i0 as bessel_i0

from larch import (Group, Make_CallArgs, parse_group_args)

from larch.math import complex_phase
from .xafsutils import set_xafsGroup


MODNAME = '_xafs'
VALID_WINDOWS = ['han', 'fha', 'gau', 'kai', 'par', 'wel', 'sin', 'bes']
sqrtpi = sqrt(pi)

def ftwindow(x, xmin=None, xmax=None, dx=1, dx2=None,
             window='hanning', _larch=None, **kws):
    """
    create a Fourier transform window array.

    Parameters:
    -------------
      x:        1-d array array to build window on.
      xmin:     starting x for FT Window
      xmax:     ending x for FT Window
      dx:       tapering parameter for FT Window
      dx2:      second tapering parameter for FT Window (=dx)
      window:   name of window type

    Returns:
    ----------
    1-d window array.

    Notes:
    -------
    Valid Window names:
        hanning              cosine-squared taper
        parzen               linear taper
        welch                quadratic taper
        gaussian             Gaussian (normal) function window
        sine                 sine function window
        kaiser               Kaiser-Bessel function-derived window

    """
    if window is None:
        window = VALID_WINDOWS[0]
    nam = window.strip().lower()[:3]
    if nam not in VALID_WINDOWS:
        raise RuntimeError("invalid window name %s" % window)

    dx1 = dx
    if dx2 is None:  dx2 = dx1
    if xmin is None: xmin = min(x)
    if xmax is None: xmax = max(x)

    xstep = (x[-1] - x[0]) / (len(x)-1)
    xeps  = 1.e-4 * xstep
    x1 = max(min(x), xmin - dx1/2.0)
    x2 = xmin + dx1/2.0  + xeps
    x3 = xmax - dx2/2.0  - xeps
    x4 = min(max(x), xmax + dx2/2.0)

    if nam == 'fha':
        if dx1 < 0: dx1 = 0
        if dx2 > 1: dx2 = 1
        x2 = x1 + xeps + dx1*(xmax-xmin)/2.0
        x3 = x4 - xeps - dx2*(xmax-xmin)/2.0
    elif nam == 'gau':
        dx1 = max(dx1, xeps)

    def asint(val): return int((val+xeps)/xstep)
    i1, i2, i3, i4 = asint(x1), asint(x2), asint(x3), asint(x4)
    i1, i2 = max(0, i1), max(0, i2)
    i3, i4 = min(len(x)-1, i3), min(len(x)-1, i4)
    if i2 == i1: i1 = max(0, i2-1)
    if i4 == i3: i3 = max(i2, i4-1)
    x1, x2, x3, x4 = x[i1], x[i2], x[i3], x[i4]
    if x1 == x2: x2 = x2+xeps
    if x3 == x4: x4 = x4+xeps
    # initial window
    fwin =  zeros(len(x))
    if i3 > i2:
        fwin[i2:i3] = ones(i3-i2)

    # now finish making window
    if nam in ('han', 'fha'):
        fwin[i1:i2+1] = sin((pi/2)*(x[i1:i2+1]-x1) / (x2-x1))**2
        fwin[i3:i4+1] = cos((pi/2)*(x[i3:i4+1]-x3) / (x4-x3))**2
    elif nam == 'par':
        fwin[i1:i2+1] =     (x[i1:i2+1]-x1) / (x2-x1)
        fwin[i3:i4+1] = 1 - (x[i3:i4+1]-x3) / (x4-x3)
    elif nam == 'wel':
        fwin[i1:i2+1] = 1 - ((x[i1:i2+1]-x2) / (x2-x1))**2
        fwin[i3:i4+1] = 1 - ((x[i3:i4+1]-x3) / (x4-x3))**2
    elif nam  in ('kai', 'bes'):
        cen  = (x4+x1)/2
        wid  = (x4-x1)/2
        arg  = 1 - (x-cen)**2 / (wid**2)
        arg[where(arg<0)] = 0
        if nam == 'bes': # 'bes' : ifeffit 1.0 implementation of kaiser-bessel
            fwin = bessel_i0(dx* sqrt(arg)) / bessel_i0(dx)
            fwin[where(x<=x1)] = 0
            fwin[where(x>=x4)] = 0
        else: # better version
            scale = max(1.e-10, bessel_i0(dx)-1)
            fwin = (bessel_i0(dx * sqrt(arg)) - 1) / scale
    elif nam == 'sin':
        fwin[i1:i4+1] = sin(pi*(x4-x[i1:i4+1]) / (x4-x1))
    elif nam == 'gau':
        cen  = (x4+x1)/2
        fwin =  exp(-(((x - cen)**2)/(2*dx1*dx1)))
    return fwin


@Make_CallArgs(["r", "chir"])
def xftr(r, chir=None, group=None, rmin=0, rmax=20, with_phase=False,
            dr=1, dr2=None, rw=0, window='kaiser', qmax_out=None,
            nfft=2048, kstep=0.05, _larch=None, **kws):
    """
    reverse XAFS Fourier transform, from chi(R) to chi(q).

    calculate reverse XAFS Fourier transform
    This assumes that chir_re and (optional chir_im are
    on a uniform r-grid given by r.

    Parameters:
    ------------
      r:        1-d array of distance, or group.
      chir:     1-d array of chi(R)
      group:    output Group
      qmax_out: highest *k* for output data (30 Ang^-1)
      rweight:  exponent for weighting spectra by r^rweight (0)
      rmin:     starting *R* for FT Window
      rmax:     ending *R* for FT Window
      dr:       tapering parameter for FT Window
      dr2:      second tapering parameter for FT Window
      window:   name of window type
      nfft:     value to use for N_fft (2048).
      kstep:    value to use for delta_k (0.05).
      with_phase: output the phase as well as magnitude, real, imag  [False]

    Returns:
    ---------
      None -- outputs are written to supplied group.

    Notes:
    -------
    Arrays written to output group:
        rwin               window Omega(R) (length of input chi(R)).
        q                  uniform array of k, out to qmax_out.
        chiq               complex array of chi(k).
        chiq_mag           magnitude of chi(k).
        chiq_re            real part of chi(k).
        chiq_im            imaginary part of chi(k).
        chiq_pha           phase of chi(k) if with_phase=True
                           (a noticable performance hit)

    Supports First Argument Group convention (with group member names 'r' and 'chir')
    """
    if 'rweight' in kws:
        rw = kws['rweight']

    r, chir, group = parse_group_args(r, members=('r', 'chir'),
                                     defaults=(chir,), group=group,
                                     fcn_name='xftr')
    rstep = r[1] - r[0]
    kstep = pi/(rstep*nfft)
    scale = 1.0

    cchir = zeros(nfft, dtype='complex128')
    r_    = rstep * arange(nfft, dtype='float64')

    cchir[0:len(chir)] = chir
    if chir.dtype == np.dtype('complex128'):
        scale = 0.5

    win = ftwindow(r_, xmin=rmin, xmax=rmax, dx=dr, dx2=dr2, window=window)
    out = scale * xftr_fast( cchir*win * r_**rw, kstep=kstep, nfft=nfft)
    if qmax_out is None: qmax_out = 30.0
    q = linspace(0, qmax_out, int(1.05 + qmax_out/kstep))
    nkpts = len(q)

    group = set_xafsGroup(group, _larch=_larch)
    group.q = q
    mag = sqrt(out.real**2 + out.imag**2)
    group.rwin =  win[:len(chir)]
    group.chiq     =  out[:nkpts]
    group.chiq_mag =  mag[:nkpts]
    group.chiq_re  =  out.real[:nkpts]
    group.chiq_im  =  out.imag[:nkpts]
    if with_phase:
        group.chiq_pha =  complex_phase(out[:nkpts])



@Make_CallArgs(["k", "chi"])
def xftf(k, chi=None, group=None, kmin=0, kmax=20, kweight=0,
         dk=1, dk2=None, with_phase=False, window='kaiser', rmax_out=10,
         nfft=2048, kstep=0.05, _larch=None, **kws):
    """
    forward XAFS Fourier transform, from chi(k) to chi(R), using
    common XAFS conventions.

    Parameters:
    -----------
      k:        1-d array of photo-electron wavenumber in Ang^-1 or group
      chi:      1-d array of chi
      group:    output Group
      rmax_out: highest R for output data (10 Ang)
      kweight:  exponent for weighting spectra by k**kweight
      kmin:     starting k for FT Window
      kmax:     ending k for FT Window
      dk:       tapering parameter for FT Window
      dk2:      second tapering parameter for FT Window
      window:   name of window type
      nfft:     value to use for N_fft (2048).
      kstep:    value to use for delta_k (0.05 Ang^-1).
      with_phase: output the phase as well as magnitude, real, imag  [False]

    Returns:
    ---------
      None   -- outputs are written to supplied group.

    Notes:
    -------
    Arrays written to output group:
        kwin               window function Omega(k) (length of input chi(k)).
        r                  uniform array of R, out to rmax_out.
        chir               complex array of chi(R).
        chir_mag           magnitude of chi(R).
        chir_re            real part of chi(R).
        chir_im            imaginary part of chi(R).
        chir_pha           phase of chi(R) if with_phase=True
                           (a noticable performance hit)

    Supports First Argument Group convention (with group member names 'k' and 'chi')
    """
    # allow kweight keyword == kw
    if 'kw' in kws:
        kweight = kws['kw']

    k, chi, group = parse_group_args(k, members=('k', 'chi'),
                                     defaults=(chi,), group=group,
                                     fcn_name='xftf')

    cchi, win  = xftf_prep(k, chi, kmin=kmin, kmax=kmax, kweight=kweight,
                               dk=dk, dk2=dk2, nfft=nfft, kstep=kstep,
                               window=window, _larch=_larch)

    out = xftf_fast(cchi*win, kstep=kstep, nfft=nfft)
    rstep = pi/(kstep*nfft)

    irmax = int(min(nfft/2, 1.01 + rmax_out/rstep))

    group = set_xafsGroup(group, _larch=_larch)
    r   = rstep * arange(irmax)
    mag = sqrt(out.real**2 + out.imag**2)
    group.kwin =  win[:len(chi)]
    group.r    =  r[:irmax]
    group.chir =  out[:irmax]
    group.chir_mag =  mag[:irmax]
    group.chir_re  =  out.real[:irmax]
    group.chir_im  =  out.imag[:irmax]
    if with_phase:
        group.chir_pha =  complex_phase(out[:irmax])



def xftf_prep(k, chi, kmin=0, kmax=20, kweight=2, dk=1, dk2=None,
                window='kaiser', nfft=2048, kstep=0.05, _larch=None):
    """
    calculate weighted chi(k) on uniform grid of len=nfft, and the
    ft window.

    Returns weighted chi, window function which can easily be multiplied
    and used in xftf_fast.
    """
    if dk2 is None: dk2 = dk
    npts = int(1.01 + max(k)/kstep)
    k_max = max(max(k), kmax+dk2)
    k_   = kstep * np.arange(int(1.01+k_max/kstep), dtype='float64')
    chi_ = interp(k_, k, chi)
    win  = ftwindow(k_, xmin=kmin, xmax=kmax, dx=dk, dx2=dk2, window=window)
    return ((chi_[:npts] *k_[:npts]**kweight), win[:npts])


def xftf_fast(chi, nfft=2048, kstep=0.05, _larch=None, **kws):
    """
    calculate forward XAFS Fourier transform.  Unlike xftf(),
    this assumes that:
      1. data is already on a uniform grid
      2. any windowing and/or kweighting has been applied.
    and simply returns the complex chi(R), not setting any larch data.

    This is useful for repeated FTs, as inside loops.

    Parameters:
    ------------
      chi:      1-d array of chi to be transformed
      nfft:     value to use for N_fft (2048).
      kstep:    value to use for delta_k (0.05).

    Returns:
    --------
      complex 1-d array chi(R)

    """
    cchi = zeros(nfft, dtype='complex128')
    cchi[0:len(chi)] = chi
    return (kstep / sqrtpi) * fft(cchi)[:int(nfft/2)]

def xftr_fast(chir, nfft=2048, kstep=0.05, _larch=None, **kws):
    """
    calculate reverse XAFS Fourier transform, from chi(R) to
    chi(q), using common XAFS conventions.  This version demands
    chir be the complex chi(R) as created from xftf().

    It returns the complex array of chi(q) without putting any
    values into an output group.

    Parameters:
    -------------
      chir:     1-d array of chi(R) to be transformed
      nfft:     value to use for N_fft (2048).
      kstep:    value to use for delta_k (0.05).

    Returns:
    ----------
      complex 1-d array for chi(q).

    This is useful for repeated FTs, as inside loops.
    """
    cchi = zeros(nfft, dtype='complex128')
    cchi[0:len(chir)] = chir
    return  (4*sqrtpi/kstep) * ifft(cchi)[:int(nfft/2)]
