import numpy as np

from xraydb import xray_line, xray_edge, material_mu
from larch import  parse_group_args
from .xafsutils import set_xafsGroup
from .pre_edge import preedge

def fluo_corr(energy, mu, formula, elem, group=None, edge='K', line='Ka', anginp=45,
              angout=45, _larch=None, **pre_kws):
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
      line      name of line ('K', 'Ka', 'La', ...) [default 'Ka']
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
    # gather pre-edge options
    pre_opts = {'e0': None, 'nnorm': 1, 'nvict': 0,
                'pre1': None, 'pre2': -30,
                'norm1': 100, 'norm2': None}
    if hasattr(group, 'pre_edge_details'):
        uopts = getattr(group.pre_edge_details, 'call_args', {})
        for attr in pre_opts:
            if attr in uopts:
                pre_opts[attr] = uopts[attr]
    pre_opts.update(pre_kws)
    pre_opts['step'] = None
    pre_opts['nvict'] = 0

    # generate normalized mu for correction
    preinp   = preedge(energy, mu, **pre_opts)

    ang_corr = (np.sin(max(1.e-7, np.deg2rad(anginp))) /
                np.sin(max(1.e-7, np.deg2rad(angout))))

    # find edge energies and fluorescence line energy
    e_edge  = xray_edge(elem, edge).energy
    e_fluor = xray_line(elem, line).energy

    # calculate mu(E) for fluorescence energy, above, below edge

    muvals = material_mu(formula, np.array([e_fluor, e_edge-10.0,
                                            e_edge+10.0]), density=1)

    alpha   = (muvals[0]*ang_corr + muvals[1])/(muvals[2] - muvals[1])
    mu_corr = mu*alpha/(alpha + 1 - preinp['norm'])
    preout  = preedge(energy, mu_corr, **pre_opts)
    if group is not None:
        if _larch is not None:
            group = set_xafsGroup(group, _larch=_larch)
        group.mu_corr = mu_corr
        group.norm_corr = preout['norm']
