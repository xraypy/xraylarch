import os
import ctypes
import numpy as np
from scipy.signal import convolve

import larch
from larch.larchlib import get_dll

from larch.math import as_ndarray
from xraydb import core_width, atomic_number

CLLIB = None

def f1f2(z, energies, width=None, edge=None):
    """Return anomalous scattering factors f1, f2 from Cromer-Liberman

    Look-up and return f1, f2 for an element and array of energies
    from Cromer-Liberman (Cowan-Brennan implementation)

    Parameters
    ----------
    z:         atomic number of element
    energies:  array of x-ray energies (in eV)
    width:     width used to convolve values with lorentzian profile
    edge:      x-ray edge ('K', 'L3', etc) used to lookup energy
               width for convolution.

    Returns:
    ---------
    f1, f2:    anomalous scattering factors

    """
    global CLLIB
    if CLLIB is None:
        CLLIB = get_dll('cldata')

    en = as_ndarray(energies)

    if not isinstance(z, int):
        z  = atomic_number(z)
        if z is None:
            return None

    if z > 92:
        print( 'Cromer-Liberman data not available for Z>92')
        return

    if edge is not None or width is not None:
        natwid = core_width(element=z, edge=edge)
        if width is None and natwid not in (None, []):
            width = natwid

    if width is not None: # will convolve!
        e_extra = int(width*80.0)
        estep = (en[1:] - en[:-1]).min()
        emin = min(en) - e_extra
        emax = max(en) + e_extra

        npts = 1 + abs(emax-emin+estep*0.02)/abs(estep)
        en   = np.linspace(emin, emax, int(npts))
        nk   = int(e_extra / estep)
        sig  = width/2.0
        lor  = (1./(1 + ((np.arange(2*nk+1)-nk*1.0)/sig)**2))/(np.pi*sig)
        scale = lor.sum()

    # create ctypes pointers for the C function
    npts   = len(en)
    p_z    = ctypes.pointer(ctypes.c_int(int(z)))
    p_npts = ctypes.pointer(ctypes.c_int(npts))
    p_en   = (npts*ctypes.c_double)()
    p_f1   = (npts*ctypes.c_double)()
    p_f2   = (npts*ctypes.c_double)()

    for i in range(npts):
        p_en[i] = en[i]

    nout = CLLIB.f1f2(p_z, p_npts, p_en, p_f1, p_f2)
    f1 = np.array([i for i in p_f1[:]])
    f2 = np.array([i for i in p_f2[:]])
    if width is not None: # do the convolution
        f1 = np.interp(energies, en, convolve(f1, lor)[nk:-nk])/scale
        f2 = np.interp(energies, en, convolve(f2, lor)[nk:-nk])/scale
    return (f1, f2)

if __name__ == '__main__':
    en = np.linspace(8000, 9200, 51)
    f1, f2 = f1f2(29, en)
    print( en, f1, f2)
