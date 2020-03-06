#!/usr/bin/env python
"""
  XAFS MBACK normalization algorithms.
"""
import numpy as np
from scipy.special import erfc

from xraydb import (xray_edge, xray_line, xray_lines,
                    f1_chantler, f2_chantler, guess_edge,
                    atomic_number, atomic_symbol)
from lmfit import Parameter, Parameters, minimize

from larch import Group, isgroup, parse_group_args

from larch.math import index_of, index_nearest, remove_dups, remove_nans2

from .xafsutils import set_xafsGroup
from .pre_edge import find_e0, preedge


MAXORDER = 6

def find_xray_line(z, edge):
    """
    Finds most intense X-ray emission line energy for a given element and edge.
    """
    intensity = 0
    line      = ''
    for key, value in xray_lines(z).items() :
        if value.initial_level == edge.upper():
            if value.intensity > intensity:
                intensity = value.intensity
                line      = key
    return xray_line(z, line[:-1])

def match_f2(p, en=0, mu=1, f2=1, e0=0, em=0, weight=1, theta=1, order=None,
             leexiang=False):
    """
    Objective function for matching mu(E) data to tabulated f''(E) using the MBACK
    algorithm and, optionally, the Lee & Xiang extension.
    """
    pars = p.valuesdict()
    eoff  = en - e0

    norm = p['a']*erfc((en-em)/p['xi']) + p['c0'] # erfc function + constant term
    for i in range(order):                        # successive orders of polynomial
        attr = 'c%d' % (i + 1)
        if attr in p:
            norm += p[attr] * eoff**(i + 1)
    func = (f2 + norm - p['s']*mu) * theta / weight
    if leexiang:
        func = func / p['s']*mu
    return func


def mback(energy, mu=None, group=None, z=None, edge='K', e0=None, pre1=None, pre2=-50,
          norm1=100, norm2=None, order=3, leexiang=False, tables='chantler', fit_erfc=False,
          return_f1=False, _larch=None):
    """
    Match mu(E) data for tabulated f''(E) using the MBACK algorithm and,
    optionally, the Lee & Xiang extension

    Arguments
    ----------
      energy:     array of x-ray energies, in eV.
      mu:         array of mu(E).
      group:      output group.
	  z:          atomic number of the absorber.
	  edge:       x-ray absorption edge (default 'K')
      e0:         edge energy, in eV.  If None, it will be determined here.
      pre1:       low E range (relative to e0) for pre-edge region.
      pre2:       high E range (relative to e0) for pre-edge region.
      norm1:      low E range (relative to e0) for post-edge region.
      norm2:      high E range (relative to e0) for post-edge region.
      order:      order of the legendre polynomial for normalization.
	              (default=3, min=0, max=5).
      leexiang:   boolean (default False)  to use the Lee & Xiang extension.
      tables:     tabulated scattering factors: 'chantler' [deprecated]
      fit_erfc:   boolean (default False) to fit parameters of error function.
      return_f1:  boolean (default False) to include the f1 array in the group.


    Returns
    -------
      None

    The following attributes will be written to the output group:
      group.f2:            tabulated f2(E).
      group.f1:            tabulated f1(E) (if 'return_f1' is True).
      group.fpp:           mback atched spectrum.
	  group.edge_step:     edge step of spectrum.
	  group.norm:          normalized spectrum.
      group.mback_params:  group of parameters for the minimization.

    Notes:
        Chantler tables is now used, with Cromer-Liberman no longer supported.
    References:
      * MBACK (Weng, Waldo, Penner-Hahn): http://dx.doi.org/10.1086/303711
      * Lee and Xiang: http://dx.doi.org/10.1088/0004-637X/702/2/970
      * Cromer-Liberman: http://dx.doi.org/10.1063/1.1674266
      * Chantler: http://dx.doi.org/10.1063/1.555974
    """
    order = max(min(order, MAXORDER), 0)

    ### implement the First Argument Group convention
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='mback')
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    if _larch is not None:
        group = set_xafsGroup(group, _larch=_larch)

    energy = remove_dups(energy)
    if e0 is None or e0 < energy[1] or e0 > energy[-2]:
        e0 = find_e0(energy, mu, group=group)

    print(e0)
    ie0 = index_nearest(energy, e0)
    e0 = energy[ie0]

    pre1_input = pre1
    norm2_input = norm2

    if pre1 is None:  pre1  = min(energy) - e0
    if norm2 is None: norm2 = max(energy) - e0
    if norm2 < 0:     norm2 = max(energy) - e0 - norm2
    pre1  = max(pre1,  (min(energy) - e0))
    norm2 = min(norm2, (max(energy) - e0))

    if pre1 > pre2:
        pre1, pre2 = pre2, pre1
    if norm1 > norm2:
        norm1, norm2 = norm2, norm1

    p1 = index_of(energy, pre1+e0)
    p2 = index_nearest(energy, pre2+e0)
    n1 = index_nearest(energy, norm1+e0)
    n2 = index_of(energy, norm2+e0)
    if p2 - p1 < 2:
        p2 = min(len(energy), p1 + 2)
    if n2 - n1 < 2:
        p2 = min(len(energy), p1 + 2)

    ## theta is a boolean array indicating the
	## energy values considered for the fit.
    ## theta=1 for included values, theta=0 for excluded values.
    theta            = np.zeros_like(energy, dtype='int')
    theta[p1:(p2+1)] = 1
    theta[n1:(n2+1)] = 1

    ## weights for the pre- and post-edge regions, as defined in the MBACK paper (?)
    weight            = np.ones_like(energy, dtype=float)
    weight[p1:(p2+1)] = np.sqrt(np.sum(weight[p1:(p2+1)]))
    weight[n1:(n2+1)] = np.sqrt(np.sum(weight[n1:(n2+1)]))

    ## get the f'' function from CL or Chantler
    f1 = f1_chantler(z, energy)
    f2 = f2_chantler(z, energy)
    group.f2 = f2
    if return_f1:
        group.f1 = f1

    em = find_xray_line(z, edge).energy # erfc centroid

    params = Parameters()
    params.add(name='s',  value=1.0,  vary=True)  # scale of data
    params.add(name='xi', value=50.0, vary=False, min=0) # width of erfc
    params.add(name='a',  value=0.0, vary=False)  # amplitude of erfc
    if fit_erfc:
        params['a'].vary  = True
        params['a'].value = 0.5
        params['xi'].vary  = True

    for i in range(order+1): # polynomial coefficients
        params.add(name='c%d' % i, value=0, vary=True)

    out = minimize(match_f2, params, method='leastsq',
                   gtol=1.e-5, ftol=1.e-5, xtol=1.e-5, epsfcn=1.e-5,
                   kws = dict(en=energy, mu=mu, f2=f2, e0=e0, em=em,
                              order=order, weight=weight, theta=theta, leexiang=leexiang))

    opars = out.params.valuesdict()
    eoff = energy - e0

    norm_function = opars['a']*erfc((energy-em)/opars['xi']) + opars['c0']
    for i in range(order):
        attr = 'c%d' % (i + 1)
        if attr in opars:
            norm_function  += opars[attr]* eoff**(i + 1)

    group.e0 = e0
    group.fpp = opars['s']*mu - norm_function
    # calculate edge step and normalization from f2 + norm_function
    pre_f2 = preedge(energy, group.f2+norm_function, e0=e0, pre1=pre1,
	         pre2=pre2, norm1=norm1, norm2=norm2, nnorm=2, nvict=0)
    group.edge_step = pre_f2['edge_step'] / opars['s']
    group.norm = (opars['s']*mu -  pre_f2['pre_edge']) / pre_f2['edge_step']
    group.mback_details = Group(params=opars, pre_f2=pre_f2,
                                f2_scaled=opars['s']*f2,
                                norm_function=norm_function)



def f2norm(params, en=1, mu=1, f2=1, weights=1):

    """
    Objective function for matching mu(E) data to tabulated f''(E)
    """
    p = params.valuesdict()
    model = (p['offset'] + p['slope']*en + f2) * p['scale']
    return weights * (model - mu)


def mback_norm(energy, mu=None, group=None, z=None, edge='K', e0=None,
               pre1=None, pre2=None, norm1=None, norm2=None, nnorm=None, nvict=1,
               _larch=None):
    """
    simplified version of MBACK to Match mu(E) data for tabulated f''(E)
    for normalization

    Arguments:
      energy, mu:  arrays of energy and mu(E)
      group:       output group (and input group for e0)
      z:           Z number of absorber
      e0:          edge energy
      pre1:        low E range (relative to E0) for pre-edge fit
      pre2:        high E range (relative to E0) for pre-edge fit
      norm1:       low E range (relative to E0) for post-edge fit
      norm2:       high E range (relative to E0) for post-edge fit
      nnorm:       degree of polynomial (ie, nnorm+1 coefficients will be
                   found) for post-edge normalization curve fit to the
                   scaled f2. Default=1 (linear)

    Returns:
      group.norm_poly:     normalized mu(E) from pre_edge()
      group.norm:          normalized mu(E) from this method
      group.mback_mu:      tabulated f2 scaled and pre_edge added to match mu(E)
      group.mback_params:  Group of parameters for the minimization

    References:
      * MBACK (Weng, Waldo, Penner-Hahn): http://dx.doi.org/10.1086/303711
      * Chantler: http://dx.doi.org/10.1063/1.555974
    """
    ### implement the First Argument Group convention
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='mback')
    if len(energy.shape) > 1:
        energy = energy.squeeze()
    if len(mu.shape) > 1:
        mu = mu.squeeze()

    if _larch is not None:
        group = set_xafsGroup(group, _larch=_larch)
    group.norm_poly = group.norm*1.0

    if z is not None:              # need to run find_e0:
        e0_nominal = xray_edge(z, edge).energy
    if e0 is None:
        e0 = getattr(group, 'e0', None)
        if e0 is None:
            find_e0(energy, mu, group=group)
            e0 = group.e0

    atsym = None
    if z is None or z < 2:
        atsym, edge = guess_edge(group.e0)
        z = atomic_number(atsym)
    if atsym is None and z is not None:
        atsym = atomic_symbol(z)

    if getattr(group, 'pre_edge_details', None) is None:  # pre_edge never run
        preedge(energy, mu, pre1=pre1, pre2=pre2, nvict=nvict,
                norm1=norm1, norm2=norm2, e0=e0, nnorm=nnorm)

    mu_pre = mu - group.pre_edge
    f2 = f2_chantler(z, energy)

    weights = np.ones(len(energy))*1.0

    if norm2 is None:
        norm2 = max(energy) - e0

    if norm2 < 0:
        norm2 = max(energy) - e0  - norm2

    # avoid l2 and higher edges
    if edge.lower().startswith('l'):
        if edge.lower() == 'l3':
            e_l2 = xray_edge(z, 'L2').energy
            norm2 = min(norm2,  e_l2-e0)
        elif edge.lower() == 'l2':
            e_l2 = xray_edge(z, 'L1').energy
            norm2 = min(norm2,  e_l1-e0)

    ipre2 = index_of(energy, e0+pre2)
    inor1 = index_of(energy, e0+norm1)
    inor2 = index_of(energy, e0+norm2) + 1


    weights[ipre2:] = 0.0
    weights[inor1:inor2] = np.linspace(0.1, 1.0, inor2-inor1)

    params = Parameters()
    params.add(name='slope',   value=0.0,    vary=True)
    params.add(name='offset',  value=-f2[0], vary=True)
    params.add(name='scale',   value=f2[-1], vary=True)

    out = minimize(f2norm, params, method='leastsq',
                   gtol=1.e-5, ftol=1.e-5, xtol=1.e-5, epsfcn=1.e-5,
                   kws = dict(en=energy, mu=mu_pre, f2=f2, weights=weights))

    p = out.params.valuesdict()

    model = (p['offset'] + p['slope']*energy + f2) * p['scale']

    group.mback_mu = model + group.pre_edge

    pre_f2 = preedge(energy, model, nnorm=nnorm, nvict=nvict, e0=e0,
                     pre1=pre1, pre2=pre2, norm1=norm1, norm2=norm2)

    step_new = pre_f2['edge_step']

    group.edge_step_poly  = group.edge_step
    group.edge_step_mback = step_new
    group.norm_mback = mu_pre / step_new


    group.mback_params = Group(e0=e0, pre1=pre1, pre2=pre2, norm1=norm1,
                               norm2=norm2, nnorm=nnorm, fit_params=p,
                               fit_weights=weights, model=model, f2=f2,
                               pre_f2=pre_f2, atsym=atsym, edge=edge)

    if (abs(step_new - group.edge_step)/(1.e-13+group.edge_step)) > 0.75:
        print("Warning: mback edge step failed....")
    else:
        group.edge_step = step_new
        group.norm       = group.norm_mback
