
from larch import (Group, Parameter, isParameter, isgroup, param_value, use_plugin_path, isNamedClass, Interpreter, Minimizer)
use_plugin_path('math')
from mathutils import _interp, index_of
use_plugin_path('xray')
from cromer_liberman import f1f2
from xraydb_plugin import xray_edge, xray_line, f2_chantler
use_plugin_path('std')
from grouputils import parse_group_args
use_plugin_path('xafs')
from xafsutils import set_xafsGroup
from pre_edge import find_e0, pre_edge

import numpy as np
from scipy.special import erfc
from math import pi

MAXORDER = 6

def match_f2(p):
    """Match mu(E) data for tabulated f"(E) using the MBACK algorithm or the Lee & Xiang extension"""
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
    if p.form.lower() == 'lee':
        func = func / s*p.mu
    return func


def mback(energy, mu, order=3, group=None, z=None, edge='K', e0=None, emin=None, emax=None,
          whiteline=None, form='mback', tables='cl', fit_erfc=False, pre_edge_kws=None, _larch=None):
    """
    Match mu(E) data for tabulated f"(E) using the MBACK algorithm or the Lee & Xiang extension

      energy, mu:    arrays of energy and mu(E)
      order:         order of polynomial [3]
      group:         output group (and input group for e0)
      z:             Z number of absorber
      edge:          absorption edge (K, L3)
      e0:            edge energy
      emin:          beginning energy for fit
      emax:          ending energy for fit
      whiteline:     exclusion zone around white lines
      form:          'mback' or 'lee'
      tables:        'cl' or 'chantler'
      fit_erfc:      True to float parameters of error function
      pre_edge_kws:  dictionary containing keyword arguments to pass to pre_edge()
    """
    if order < 1: order = 1 # set order of polynomial
    if order > MAXORDER: order = MAXORDER

    ### ---------------------------------------------------------------------
    ### implement the First Argument Group convention
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='mback')
    group = set_xafsGroup(group, _larch=_larch)

    if e0 is None and isgroup(group, 'e0'):
        e0 = group.e0+3
    if e0 is None:
        # need to run pre_edge:
        pre_kws = dict(nnorm=3, nvict=0, pre1=None,
                       pre2=-50., norm1=100., norm2=None)
        if pre_edge_kws is not None:
            pre_kws.update(pre_edge_kws)
        pre_edge(energy, mu, group=group, _larch=_larch, **pre_kws)
        if e0 is None:
            e0 = group.e0+3
    ### ---------------------------------------------------------------------


    ### ---------------------------------------------------------------------
    ### theta is an array used to exclude the regions <emin, >emax, and
    ### around white lines
    (i1, i2) = (0, len(energy)-1)
    if emin != None: i1 = index_of(energy, emin)
    if emax != None: i2 = index_of(energy, emax)
    theta = np.ones(len(energy)) # default: 1 throughout
    theta[0:i1] = 0
    theta[i2:-1] = 0
    if edge.lower().startswith('l'):
        l2 = xray_edge(z, 'L2', _larch=_larch)[0]
        if whiteline:
            theta_pre  = 1*(energy<e0)
            theta_post = 1*(energy>e0+float(whiteline))
            theta = theta * (theta_pre + theta_post)

            l2_pre  = 1*(energy<l2)
            l2_post = 1*(energy>l2+float(whiteline))
            l2theta = l2_pre + l2_post
            theta = theta * l2theta
    ### ---------------------------------------------------------------------

    ## this is used to weight the pre- and post-edge differently as
    ## defined in the MBACK paper
    weight1 = 1*(energy<e0)
    weight2 = 1*(energy>e0)
    weight  = np.sqrt(sum(weight1))*weight1 + np.sqrt(sum(weight2))*weight2

    ## get the f'' function from CL or Chantler
    if tables.lower() == 'chantler':
        f2 = f2_chantler(z, energy, _larch=_larch)
    else:
        (f1, f2) = f1f2(z, energy, edge=edge, _larch=_larch)
    group.f2 = f2

    n = edge
    if edge.lower().startswith('l'): n = 'L'
        
    params = Group(s      = Parameter(1, vary=True, _larch=_larch),     # scale of data
                   a      = Parameter(1, vary=fit_erfc, _larch=_larch), # amplitude of erfc
                   xi     = Parameter(1, vary=fit_erfc, _larch=_larch), # width of erfc
                   em     = Parameter(xray_line(z, n, _larch=_larch)[0], vary=False, _larch=_larch), # erfc centroid
                   e0     = Parameter(e0, vary=False, _larch=_larch),   # abs. edge energy
                   en     = energy,
                   mu     = mu,
                   f2     = f2,
                   weight = weight,
                   theta  = theta,
                   form   = form,
                   _larch = _larch)

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
    
    group.mback = params.s*mu - normalization_function
    group.mback_params = params


def registerLarchPlugin(): # must have a function with this name!
    return ('_xafs', { 'mback': mback })
    
