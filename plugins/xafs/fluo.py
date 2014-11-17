import numpy as np

from larch import use_plugin_path, ValidateLarchPlugin

use_plugin_path('xray')
from xraydb_plugin import xray_line, xray_edge
from materials import material_mu

use_plugin_path('xafs')
from pre_edge import preedge

MODNAME = '_xray'

def sacorr_fluo(energy, mu, formula, elem, edge='K', anginp=45, angout=45,
                e0=None, pre1=None, pre2=-50, norm1=100, norm2=None,
                nnorm=1, _larch=None):
    """correct over-absorption (self-absorption) for fluorescene XAFS
    using the FLUO alogrithm of D. Haskel.

    Arguments
    ---------
      energy    array of energies
      mu        uncorrected fluorescence mu
      formula   string for sample stoichiometry
      elem      atomic symbol or Z of absorbing element
      edge      name of edge ('K', 'L3', ...) (default 'K')
      anginp    input angle in degrees  (default 45)
      angout    output angle in degrees  (default 45)

    Also supports many keywords to pre_edge(), which will be used to
    ensure consistent normalization.

    Returns
    --------
       mu_corr  corrected mu(E).

    """
    # generate normalized mu for correction
    preopts = dict(e0=e0, pre1=pre1, pre2=pre2, nnorm=nnorm,
                   norm1=norm1, norm2=norm2)

    preinp   = preedge(energy, mu, **preopts)
    mu_inp   = preinp['norm']

    anginp   = max(1.e-7, np.deg2rad(anginp))
    angout   = max(1.e-7, np.deg2rad(angout))

    # find edge energies and fluorescence line energy
    e_edge   = xray_edge(elem, edge, _larch=_larch)[0]
    e_fluor  = xray_line(elem, edge, _larch=_larch)[0]

    # calculate mu(E) for fluorescence energy, above, below edge
    energies = np.array([e_fluor, e_edge-1.0, e_edge+1.0])

    muvals   = material_mu(formula, energies, density=1, _larch=_larch)

    mu_fluor = muvals[0] * np.sin(anginp)/np.sin(angout)
    mu_below = muvals[1]
    mu_celem = muvals[2] - muvals[1]

    alpha    = (mu_fluor + mu_below)/mu_celem
    mu_corr  = mu_inp*alpha/(alpha + 1 - mu_inp)

    # normalize corrected data
    preout   = preedge(energy, mu_corr, **preopts)
    return preout['norm']

def registerLarchPlugin(): # must have a function with this name!
    return ('xafs', {'sacorr_fluo': sacorr_fluo})
