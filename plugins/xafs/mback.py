
from larch import Group, Parameter, isgroup, Minimizer, parse_group_args

from larch_plugins.math import index_of
from larch_plugins.xray import xray_edge, xray_line, f1_chantler, f2_chantler, f1f2
from larch_plugins.xafs import set_xafsGroup, find_e0

import numpy as np
from scipy.special import erfc

MAXORDER = 6

def match_f2(p):
    """
    Objective function for matching mu(E) data to tabulated f''(E) using the MBACK
    algorithm and, optionally, the Lee & Xiang extension.
    """
    s      = p.s.value
    a      = p.a.value
    em     = p.em.value
    xi     = p.xi.value
    c0     = p.c0.value
    eoff   = p.en - p.e0.value

    norm = a*erfc((p.en-em)/xi) + c0 # erfc function + constant term of polynomial
    for i in range(MAXORDER):        # successive orders of polynomial
        j = i+1
        attr = 'c%d' % j
        if hasattr(p, attr):
            norm = norm + getattr(getattr(p, attr), 'value') * eoff**j
    func = (p.f2 + norm - s*p.mu) * p.theta / p.weight
    if p.leexiang:
        func = func / s*p.mu
    return func


def mback(energy, mu, group=None, order=3, z=None, edge='K', e0=None, emin=None, emax=None,
          whiteline=None, leexiang=False, tables='chantler', fit_erfc=False, return_f1=False,
          _larch=None):
    """
    Match mu(E) data for tabulated f''(E) using the MBACK algorithm and,
    optionally, the Lee & Xiang extension

    Arguments:
      energy, mu:    arrays of energy and mu(E)
      order:         order of polynomial [3]
      group:         output group (and input group for e0)
      z:             Z number of absorber
      edge:          absorption edge (K, L3)
      e0:            edge energy
      emin:          beginning energy for fit
      emax:          ending energy for fit
      whiteline:     exclusion zone around white lines
      leexiang:      flag to use the Lee & Xiang extension
      tables:        'chantler' (default) or 'cl'
      fit_erfc:      True to float parameters of error function
      return_f1:     True to put the f1 array in the group

    Returns:
      group.f2:      tabulated f2(E)
      group.f1:      tabulated f1(E) (if return_f1 is True)
      group.fpp:     matched data
      group.mback_params:  Group of parameters for the minimization

    References:
      * MBACK (Weng, Waldo, Penner-Hahn): http://dx.doi.org/10.1086/303711
      * Lee and Xiang: http://dx.doi.org/10.1088/0004-637X/702/2/970
      * Cromer-Liberman: http://dx.doi.org/10.1063/1.1674266
      * Chantler: http://dx.doi.org/10.1063/1.555974
    """
    order=int(order)
    if order < 1: order = 1 # set order of polynomial
    if order > MAXORDER: order = MAXORDER

    ### implement the First Argument Group convention
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='mback')
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    group = set_xafsGroup(group, _larch=_larch)

    if e0 is None:              # need to run find_e0:
        e0 = xray_edge(z, edge, _larch=_larch)[0]
    if e0 is None:
        e0 = group.e0
    if e0 is None:
        find_e0(energy, mu, group=group)


    ### theta is an array used to exclude the regions <emin, >emax, and
    ### around white lines, theta=0.0 in excluded regions, theta=1.0 elsewhere
    (i1, i2) = (0, len(energy)-1)
    if emin is not None: i1 = index_of(energy, emin)
    if emax is not None: i2 = index_of(energy, emax)
    theta = np.ones(len(energy)) # default: 1 throughout
    theta[0:i1]  = 0
    theta[i2:-1] = 0
    if whiteline:
        pre     = 1.0*(energy<e0)
        post    = 1.0*(energy>e0+float(whiteline))
        theta   = theta * (pre + post)
    if edge.lower().startswith('l'):
        l2      = xray_edge(z, 'L2', _larch=_larch)[0]
        l2_pre  = 1.0*(energy<l2)
        l2_post = 1.0*(energy>l2+float(whiteline))
        theta   = theta * (l2_pre + l2_post)


    ## this is used to weight the pre- and post-edge differently as
    ## defined in the MBACK paper
    weight1 = 1*(energy<e0)
    weight2 = 1*(energy>e0)
    weight  = np.sqrt(sum(weight1))*weight1 + np.sqrt(sum(weight2))*weight2


    ## get the f'' function from CL or Chantler
    if tables.lower() == 'chantler':
        f1 = f1_chantler(z, energy, _larch=_larch)
        f2 = f2_chantler(z, energy, _larch=_larch)
    else:
        (f1, f2) = f1f2(z, energy, edge=edge, _larch=_larch)
    group.f2=f2
    if return_f1: group.f1=f1

    n = edge
    if edge.lower().startswith('l'): n = 'L'
    params = Group(s      = Parameter(1, vary=True, _larch=_larch),     # scale of data
                   xi     = Parameter(50, vary=fit_erfc, min=0, _larch=_larch), # width of erfc
                   em     = Parameter(xray_line(z, n, _larch=_larch)[0], vary=False, _larch=_larch), # erfc centroid
                   e0     = Parameter(e0, vary=False, _larch=_larch),   # abs. edge energy
                   ## various arrays need by the objective function
                   en     = energy,
                   mu     = mu,
                   f2     = group.f2,
                   weight = weight,
                   theta  = theta,
                   leexiang = leexiang,
                   _larch = _larch)
    if fit_erfc:
        params.a = Parameter(1, vary=True,  _larch=_larch) # amplitude of erfc
    else:
        params.a = Parameter(0, vary=False, _larch=_larch) # amplitude of erfc

    for i in range(order): # polynomial coefficients
        setattr(params, 'c%d' % i, Parameter(0, vary=True, _larch=_larch))

    fit = Minimizer(match_f2, params, _larch=_larch, toler=1.e-5)
    fit.leastsq()

    eoff = energy - params.e0.value
    normalization_function = params.a.value*erfc((energy-params.em.value)/params.xi.value) + params.c0.value
    for i in range(MAXORDER):
        j = i+1
        attr = 'c%d' % j
        if hasattr(params, attr):
            normalization_function  = normalization_function + getattr(getattr(params, attr), 'value') * eoff**j

    group.fpp = params.s*mu - normalization_function
    group.mback_params = params


def registerLarchPlugin(): # must have a function with this name!
    return ('_xafs', { 'mback': mback })
