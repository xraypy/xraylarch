from lmfit import Parameter, Parameters, minimize

from larch import Group, isgroup, parse_group_args

from larch.utils import index_of
from larch_plugins.xray import xray_edge, xray_line, f1_chantler, f2_chantler, f1f2
from larch_plugins.xafs import set_xafsGroup, find_e0, preedge

import numpy as np
from scipy.special import erfc

MAXORDER = 6

def match_f2(p, en=0, mu=1, f2=1, e0=0, em=0, weight=1, theta=1, order=None,
             leexiang=False):
    """
    Objective function for matching mu(E) data to tabulated f''(E) using the MBACK
    algorithm and, optionally, the Lee & Xiang extension.
    """
    pars = p.valuesdict()
    eoff  = en - e0

    norm = p['a']*erfc((en-em)/p['xi']) + p['c0'] # erfc function + constant term of polynomial
    for i in range(order):        # successive orders of polynomial
        j = i+1
        attr = 'c%d' % j
        if attr in p:
            norm += p[attr] * eoff**j
    func = (f2 + norm - p['s']*mu) * theta / weight
    if leexiang:
        func = func / p['s']*mu
    return func


def mback(energy, mu=None, group=None, order=3, z=None, edge='K', e0=None, emin=None, emax=None,
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
    if return_f1:
        group.f1=f1

    em = xray_line(z, edge.upper(), _larch=_larch)[0] # erfc centroid

    params = Parameters()
    params.add(name='s',  value=1,  vary=True)  # scale of data
    params.add(name='xi', value=50, vary=fit_erfc, min=0) # width of erfc
    params.add(name='a',  value=0,   vary=False)  # amplitude of erfc
    if fit_erfc:
        params['a'].value = 1
        params['a'].vary  = True

    for i in range(order): # polynomial coefficients
        params.add(name='c%d' % i, value=0, vary=True)

    out = minimize(match_f2, params, method='leastsq',
                   gtol=1.e-5, ftol=1.e-5, xtol=1.e-5, epsfcn=1.e-5,
                   kws = dict(en=energy, mu=mu, f2=f2, e0=e0, em=em,
                              order=order, weight=weight, theta=theta, leexiang=leexiang))

    opars = out.params.valuesdict()
    eoff = energy - e0

    norm_function = opars['a']*erfc((energy-em)/opars['xi']) + opars['c0']
    for i in range(order):
        j = i+1
        attr = 'c%d' % j
        if attr in opars:
            norm_function  += opars[attr]* eoff**j

    group.e0 = e0
    group.fpp = opars['s']*mu - norm_function
    group.mback_params = opars
    tmp = Group(energy=energy, mu=group.f2-norm_function, e0=0)

    # calculate edge step from f2 + norm_function: should be very smooth
    pre_f2 = preedge(energy, group.f2+norm_function, e0=e0, nnorm=2, nvict=0)
    group.edge_step = pre_f2['edge_step'] / opars['s']

    pre_fpp = preedge(energy, mu, e0=e0, nnorm=2, nvict=0)

    group.norm = (mu -  pre_fpp['pre_edge']) / group.edge_step


def registerLarchPlugin(): # must have a function with this name!
    return ('_xafs', { 'mback': mback })
