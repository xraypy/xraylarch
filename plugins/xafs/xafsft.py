#!/usr/bin/env python
"""
  XAFS Fourier transforms
"""

import numpy as np

fftmod = np.fft


MODNAME = '_xafs'



def _xafsft(k, chi, group=None, kmin=0, kmax=20, kw=2,
           dk=1, dk2=None, window='kaiser',
           rmax_out=10, nfft=2048, kstep=0.05, larch=None):
    """
    calculate forward XAFS Fourier transform
    """
    if larch is None:
        raise Warning("cannot do xafsft -- larch broken?")

    ikmax = max(k)/kstep
    mk   = kstep * np.arange(nfft, dtype='f8')

    mchi = np.zeros(nfft)
    mchi[0:ikmax] = np.interp(mk[:ikmax], k, chi)
    mchi = (1.+0j) * mchi

    out = fftmod.fft(mchi * mk**kw) [:nfft/2]
    r   = np.arange(nfft/2) * np.pi/ (kstep * nfft)
    
    if larch.symtable.isgroup(group):
        setattr(group, 'r', r)
        setattr(group, 'chir',   out)
        setattr(group, 'chir_mag',  np.sqrt(out.real**2 + out.imag**2))
        setattr(group, 'chir_re', out.real)
        setattr(group, 'chir_im', out.imag)
    
    return
    


def registerLarchPlugin():
    return (MODNAME, {'xafsft': _xafsft})
