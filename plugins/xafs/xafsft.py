#!/usr/bin/env python
"""
  XAFS Fourier transforms
"""

import numpy as np
from scipy.special import i0

fftmod = np.fft
halfpi = np.pi/2

MODNAME = '_xafs'

def ftwindow(x, xmin=None, xmax=None, dx=1, dx2=None,
             window='hanning', larch=None):
    """
    calculate and return XAFS FT Window function
    """
    if larch is None:
        raise Warning("cannot do ftwindow -- larch broken?")

    swin = window.strip().lower()[:3]
    WINDOWS = ['han', 'fha', 'gau', 'kai', 'par','wel', 'sin']
    iwin = 0
    if swin in WINDOWS: iwin = WINDOWS.index(swin)

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
    if iwin == 1:
        if dx1 < 0: dx1 = 0
        if dx2 > 1: dx2 = 1
        x2 = x1 + xeps + dx1*(xmax-xmin)/2.0
        x3 = x4 - xeps - dx2*(xmax-xmin)/2.0
    elif iwin == 2:
        dx1 = max(dx1, xeps)
    elif iwin == 6:
        x1 = xmin - dx1
        x4 = xmax + dx2

    def asint(val): return int((val+xeps)/xstep)
    i1, i2, i3, i4 = asint(x1), asint(x2), asint(x3), asint(x4)

    # initial window
    owin = np.zeros(len(x))
    owin[i2:i3] = np.ones(i3-i2)

    # now finish making window
    if iwin < 2: # hanning
        owin[i1:i2] = np.sin(halfpi*(x[i1:i2]-x1) / (x2-x1))**2
        owin[i3:i4] = np.cos(halfpi*(x[i3:i4]-x3) / (x4-x3))**2
    elif iwin == 2: # gaussian
        owin =  np.exp(-(((x - dx2)**2)/(2*dx1*dx1)))
    elif iwin == 3: #  Kaiser-Bessel window
        cen  = (x4+x1)/2
        wid  = (x4-x1)/2
        arg  = wid**2 - (x-cen)**2
        arg[np.where(arg<0)] = 0
        owin = i0((dx/wid) * np.sqrt(arg)) / i0(dx1)
    elif iwin == 4: # parzen
        owin[i1:i2] = (x[i1:i2]-x1) / (x2-x1)
        owin[i3:i4] = 1 - (x[i3:i4]-x3) / (x4-x3)
    elif iwin == 5: # welch
        owin[i1:i2] = 1 - ((x[i1:i2]-x2) / (x2-x1))**2
        owin[i3:i4] = 1 - ((x[i3:i4]-x3) / (x4-x3))**2
    elif iwin == 6: # sine
        owin[i1:i4] = np.sin(np.pi*(x4-x[i1:i4]) / (x4-x1))
    elif iwin == 7:
        owin = np.exp(- (dx1 * (x- dx2)**2))
    else:
        print 'no window found'
    return owin

def xafsift(k, chi, group=None, kmin=0, kmax=20, kw=2,
           dk=1, dk2=None, window='kaiser',
           rmax_out=10, nfft=2048, kstep=0.05, larch=None):
    """
    calculate reverse XAFS Fourier transform
    """
    if larch is None:
        raise Warning("cannot do xafsft -- larch broken?")

    print 'xafsift not implemented'

def xafsft(k, chi, group=None, kmin=0, kmax=20, kw=2,
           dk=1, dk2=None, window='kaiser',
           rmax_out=10, nfft=2048, kstep=0.05, larch=None):
    """
    calculate forward XAFS Fourier transform
    """
    if larch is None:
        raise Warning("cannot do xafsft -- larch broken?")

    ikmax = max(k)/kstep
    mk   = kstep * np.arange(nfft, dtype='f8')

    mchi = np.zeros(nfft, dtype='complex128')
    mchi[0:ikmax] = np.interp(mk[:ikmax], k, chi)

    out = fftmod.fft(mchi * mk**kw) [:nfft/2]
    r   = np.arange(nfft/2) * np.pi/ (kstep * nfft)

    if larch.symtable.isgroup(group):
        setattr(group, 'r', r)
        setattr(group, 'chir',   out)
        setattr(group, 'chir_mag',  np.sqrt(out.real**2 + out.imag**2))
        setattr(group, 'chir_re', out.real)
        setattr(group, 'chir_im', out.imag)

    return chir


def xafsft_fast(chi, nfft=2048, larch=None, **kws):
    """
    calculate forward XAFS Fourier transform.  Unlike xafsft(),
    this assumes that:
      1. data is already on a uniform grid
      2. any windowing and/or kweighting has been applied.
    and simply returns the complex chi(R), not setting any larch data.

    This is useful for repeated FTs, as inside loops.
    """
    if larch is None:
        raise Warning("cannot do xafsft_fast -- larch broken?")

    cchi = np.zeros(nfft, dtype='complex128')
    cchi[0:len(chi)] = chi
    return fftmod.fft(cchi) [:nfft/2]

def registerLarchPlugin():
    return (MODNAME, {'xafsft': xafsft,
                      'xafsft_fast': xafsft_fast,
                      'xafsift': xafsift,
                      'ftwindow': ftwindow,
                      })
