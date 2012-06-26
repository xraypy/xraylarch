#!/usr/bin/env python
"""
  XAFS Fourier transforms
"""
import numpy as np
from numpy import (pi, arange, zeros, ones, sin, cos,
                   exp, log, sqrt, where, interp, linspace)
from numpy.fft import fft, ifft
from scipy.special import i0 as bessel0

MODNAME = '_xafs'
VALID_WINDOWS = ['han', 'fha', 'gau', 'kai', 'par','wel', 'sin', 'bes']

def ftwindow(x, xmin=None, xmax=None, dx=1, dx2=None,
             window='hanning', _larch=None, **kws):
    """
    calculate and return XAFS FT Window function
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
    x1 = max(min(x), xmin - dx1 / 2.0)
    x2 = xmin + dx1 / 2.0  + xeps
    x3 = xmax - dx2 / 2.0  - xeps
    x4 = min(max(x), xmax + dx2 / 2.0)
    if nam == 'fha':
        if dx1 < 0: dx1 = 0
        if dx2 > 1: dx2 = 1
        x2 = x1 + xeps + dx1*(xmax-xmin)/2.0
        x3 = x4 - xeps - dx2*(xmax-xmin)/2.0
    elif nam == 'gau':
        dx1 = max(dx1, xeps)
    elif nam == 'sin':
        x1 = xmin - dx1
        x4 = xmax + dx2

    def asint(val): return int((val+xeps)/xstep)
    i1, i2, i3, i4 = asint(x1), asint(x2), asint(x3), asint(x4)

    # initial window
    fwin =  zeros(len(x))
    fwin[i2:i3] = ones(i3-i2)

    # now finish making window
    if nam in ('han', 'fha'):
        fwin[i1:i2] = sin((pi/2)*(x[i1:i2]-x1) / (x2-x1))**2
        fwin[i3:i4] = cos((pi/2)*(x[i3:i4]-x3) / (x4-x3))**2
    elif nam == 'par':
        fwin[i1:i2] = (x[i1:i2]-x1) / (x2-x1)
        fwin[i3:i4] = 1 - (x[i3:i4]-x3) / (x4-x3)
    elif nam == 'wel':
        fwin[i1:i2] = 1 - ((x[i1:i2]-x2) / (x2-x1))**2
        fwin[i3:i4] = 1 - ((x[i3:i4]-x3) / (x4-x3))**2
    elif nam in ('kai', 'bes'):
        cen  = (x4+x1)/2
        wid  = (x4-x1)/2
        arg  = wid**2 - (x-cen)**2
        arg[where(arg<0)] = 0
        fwin = bessel0((dx/wid) * sqrt(arg)) / bessel0(dx1)
        if nam == 'kai':
            fwin[where(x<=x1)] = 0
            fwin[where(x>=x4)] = 0
        else:
            off = min(fwin)
            fwin = (fwin - off) / (1.0 - off)
    elif nam == 'sin':
        fwin[i1:i4] = sin(pi*(x4-x[i1:i4]) / (x4-x1))
    elif nam == 'gau':
        fwin =  exp(-(((x - dx2)**2)/(2*dx1*dx1)))
    return fwin

def xafsift(r, chir, group=None, rmin=0, rmax=20,
            dr=1, dr2=None, rw=0, window='kaiser', qmax_out=None,
            nfft=2048, kstep=0.05, _larch=None, **kws):
    """
    calculate reverse XAFS Fourier transform
    This assumes that chir_re and (optional chir_im are
    on a uniform r-grid given by r.
    """
    if _larch is None:
        raise Warning("cannot do xafsft -- larch broken?")
    if 'rweight' in kws:
        rw = kws['rweight']

    rstep = r[1] - r[0]
    kstep = pi/(rstep*nfft)
    scale = 1.0

    cchir = zeros(nfft, dtype='complex128')
    r_    = rstep * arange(nfft, dtype='float64')

    cchir[0:len(chir)] = chir
    if chir.dtype == np.dtype('complex128'):
        scale = 0.5

    win = ftwindow(r_, xmin=rmin, xmax=rmax, dx=dr, dx2=dr2, window=window)
    out = scale * xafsift_fast( cchir*win * r_**rw, kstep=kstep, nfft=nfft)
    if qmax_out is None: qmax_out = 30.0
    q = linspace(0, qmax_out, int(1.05 + qmax_out/kstep))
    nkpts = len(q)
    if _larch.symtable.isgroup(group):
        group.q = q
        mag = sqrt(out.real**2 + out.imag**2)
        group.rwin =  win[:len(chir)]
        group.chiq_mag =  mag[:nkpts]
        group.chiq_pha =  atan2(out.imag[:nkpts], out.real[:nkpts])
        group.chiq_re  =  out.real[:nkpts]
        group.chiq_im  =  out.imag[:nkpts]
    else:
        return out[:nkpts]

def xafsft(k, chi, group=None, kmin=0, kmax=20, kweight=0, dk=1, dk2=None,
           window='kaiser', rmax_out=10, nfft=2048, kstep=0.05, _larch=None, **kws):
    """
    calculate forward XAFS Fourier transform
    """
    if _larch is None:
        raise Warning("cannot do xafsft -- larch broken?")
    # allow kweight keyword == kw
    if 'kw' in kws:
        kweight = kws['kw']

    cchi, win  = xafsft_prep(k, chi, kmin=kmin, kmax=kmax, kweight=kweight,
                             dk=dk, dk2=dk2, nfft=nfft, kstep=kstep,
                             window=window, _larch=_larch)

    out = xafsft_fast(cchi*win, kstep=kstep, nfft=nfft)
    rstep = pi/(kstep*nfft)

    irmax = min(nfft/2, int(1.01 + rmax_out/rstep))

    if _larch.symtable.isgroup(group):
        r   = rstep * arange(irmax)
        mag = sqrt(out.real**2 + out.imag**2)
        group.kwin =  win[:len(chi)]
        group.r    =  r[:irmax]
        group.chir =  out[:irmax]
        group.chir_mag =  mag[:irmax]
        group.chir_pha =  atan2(out.imag[:irmax], out.real[:irmax])
        group.chir_re  =  out.real[:irmax]
        group.chir_im  =  out.imag[:irmax]

    else:
        return out[:irmax]

def xafsft_prep(k, chi, kmin=0, kmax=20, kweight=2, dk=1, dk2=None,
                window='kaiser', nfft=2048, kstep=0.05, _larch=None):
    """
    calculate weighted chi(k) on uniform grid of len=nfft, and the
    ft window.

    Returns weighted chi, window function which can easily be multiplied
    and used in xafsft_fast.
    """
    ikmax = int(1.01 + max(k)/kstep)
    k_   = kstep * arange(ikmax, dtype='float64')
    ochi = interp(k_, k, chi)
    win = ftwindow(k_, xmin=kmin, xmax=kmax, dx=dk, dx2=dk2, window=window)
    return (ochi*k_**kweight, win)

def xafsft_fast(chi, nfft=2048, kstep=0.05, _larch=None, **kws):
    """
    calculate forward XAFS Fourier transform.  Unlike xafsft(),
    this assumes that:
      1. data is already on a uniform grid
      2. any windowing and/or kweighting has been applied.
    and simply returns the complex chi(R), not setting any larch data.

    This is useful for repeated FTs, as inside loops.
    """
    cchi = zeros(nfft, dtype='complex128')
    cchi[0:len(chi)] = chi
    return (kstep / sqrt(pi)) * fft(cchi)[:nfft/2]

def xafsift_fast(chir, nfft=2048, kstep=0.05, _larch=None, **kws):
    """
    calculate inverse XAFS Fourier transform.  Unlike xafsft(),
    this assumes that:
      1. data is already on a uniform grid
      2. any windowing and/or kweighting has been applied.
    and simply returns the complex chi(R), not setting any larch data.

    This is useful for repeated FTs, as inside loops.
    """
    cchi = zeros(nfft, dtype='complex128')
    cchi[0:len(chir)] = chir
    return  (4*sqrt(pi)/kstep) * ifft(cchi)[:nfft/2]


def registerLarchPlugin():
    return (MODNAME, {'xafsft': xafsft,
                      'xafsft_prep': xafsft_prep,
                      'xafsft_fast': xafsft_fast,
                      'xafsift': xafsift,
                      'ftwindow': ftwindow,
                      })
