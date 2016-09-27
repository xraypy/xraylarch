#!/usr/bin/env python
# XAS spectral decovolution
#

import numpy as np
from scipy.signal import deconvolve
from larch import ValidateLarchPlugin, parse_group_args

from larch_plugins.math import (gaussian, lorentzian, _interp,
                                index_of, index_nearest, remove_dups)
from larch_plugins.xafs import set_xafsGroup

MODNAME = '_xafs'

@ValidateLarchPlugin
def xas_deconvolve(energy, norm=None, group=None, form='gaussian',
                   esigma=1.0, eshift=0.0, _larch=None):
    """XAS spectral deconvolution

    This function de-convolves a normalized mu(E) spectra with a
    peak shape, enhancing separation of XANES features.

    This can be unstable -- Use results with caution!

    Arguments
    ----------
    energy:   array of x-ray energies, in eV or group
    norm:     array of normalized mu(E)
    group:    output group
    form:     form of deconvolution function. One of
              'gaussian' (default) or 'lorentzian'
    esigma    energy sigma to pass to gaussian() or lorentzian()
              [in eV, default=1.0]
    eshift    energy shift to apply to result. [in eV, default=0]

    Returns
    -------
    None
       The array 'deconv' will be written to the output group.

    Notes
    -----
       Support See First Argument Group convention, requiring group
       members 'energy' and 'norm'
    """
    if _larch is None:
        raise Warning("cannot deconvolve -- larch broken?")

    energy, mu, group = parse_group_args(energy, members=('energy', 'norm'),
                                         defaults=(norm,), group=group,
                                         fcn_name='xas_deconv')
    eshift = eshift + 0.5 * esigma

    en  = remove_dups(energy)
    en  = en - en[0]
    estep = max(0.001, 0.001*int(min(en[1:]-en[:-1])*1000.0))
    npts = 1  + int(max(en) / estep)

    x = np.arange(npts)*estep
    y = _interp(en, mu, x, kind='linear', _larch=_larch)

    kernel = gaussian
    if form.lower().startswith('lor'):
        kernel = lorentzian

    yext = np.concatenate((y, np.arange(len(y))*y[-1]))
    ret, err = deconvolve(yext, kernel(x, 0, esigma))
    nret = min(len(x), len(ret))

    ret = ret[:nret]*yext[nret-1]/ret[nret-1]
    out = _interp(x+eshift, ret, en, kind='linear', _larch=_larch)

    group = set_xafsGroup(group, _larch=_larch)
    group.deconv = out

def registerLarchPlugin():
    return (MODNAME, {'xas_deconvolve': xas_deconvolve})
