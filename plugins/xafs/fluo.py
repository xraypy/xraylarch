import numpy as np

from larch import ValidateLarchPlugin, Make_CallArgs, parse_group_args
from larch_plugins.xray import xray_line, xray_edge, material_mu
from larch_plugins.xafs import preedge, set_xafsGroup

MODNAME = '_xafs'

@ValidateLarchPlugin
def fluo_corr(energy, mu, formula, elem, group=None, edge='K', anginp=45,
              angout=45,  _larch=None, **pre_kws):
    """correct over-absorption (self-absorption) for fluorescene XAFS
    using the FLUO alogrithm of D. Haskel.

    Arguments
    ---------
      energy    array of energies
      mu        uncorrected fluorescence mu
      formula   string for sample stoichiometry
      elem      atomic symbol or Z of absorbing element
      group     output group [default None]
      edge      name of edge ('K', 'L3', ...) [default 'K']
      anginp    input angle in degrees  [default 45]
      angout    output angle in degrees  [default 45]

    Additional keywords will be passed to pre_edge(), which will be used
    to ensure consistent normalization.

    Returns
    --------
       None, writes `mu_corr` and `norm_corr` (normalized `mu_corr`)
       to output group.

    Notes
    -----
       Support First Argument Group convention, requiring group
       members 'energy' and 'mu'
    """
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='fluo_corr')

    # generate normalized mu for correction
    preinp   = preedge(energy, mu, **pre_kws)
    mu_inp   = preinp['norm']

    anginp   = max(1.e-7, np.deg2rad(anginp))
    angout   = max(1.e-7, np.deg2rad(angout))

    # find edge energies and fluorescence line energy
    e_edge   = xray_edge(elem, edge, _larch=_larch)[0]
    e_fluor  = xray_line(elem, edge, _larch=_larch)[0]

    # calculate mu(E) for fluorescence energy, above, below edge
    energies = np.array([e_fluor, e_edge-10.0, e_edge+10.0])
    muvals   = material_mu(formula, energies, density=1, _larch=_larch)

    mu_fluor = muvals[0] * np.sin(anginp)/np.sin(angout)
    mu_below = muvals[1]
    mu_celem = muvals[2] - muvals[1]

    alpha    = (mu_fluor + mu_below)/mu_celem
    mu_corr  = mu_inp*alpha/(alpha + 1 - mu_inp)
    preout   = preedge(energy, mu_corr, **pre_kws)

    if group is not None:
        group = set_xafsGroup(group, _larch=_larch)
        group.mu_corr = mu_corr
        group.norm_corr = preout['norm']

def registerLarchPlugin():
    return (MODNAME, {'fluo_corr': fluo_corr})
