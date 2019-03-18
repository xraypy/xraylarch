#!/usr/bin/env python
"""
Splines for fitting to data within Larch

"""
from scipy.interpolate import splrep, splev

from .. import Group, isgroup
from ..fitting import Parameter, isParameter


def spline_rep(x, y, group=None, name='spl1'):
    """create a spline representation for an (x, y) data set to be
    evaluated with spline_eval(), with

        pars = spline_rep(x, y)

        pars = group()
        spline_rep(x, y, group=pars)

        ynew = spline_eval(xnew, pars)

    arguments:
    ------------
      x       1-d array for x
      y       1-d array for y
      name    name for spline params and subgroup ['spl1']
      group   optional group to use to hold spline parameters

    returns:
    --------
      group containing spline representation, which will include
      len(x)+2 parameters (named 'spl1_c0' ... 'spl1_cN+1') and
      a subgroup 'spl1_details'

    notes:
    ------

    in order to hold multiple splines in a single parameter group,
    the ``name`` argument must be different for each spline
    representation, and passed to spline_eval()
    """
    if group is None:
        group = Group()

    knots, coefs, order = splrep(x, y)
    dgroup = Group(knots=knots, order=order, coefs=coefs)
    setattr(group, "{:s}_details".format(name), dgroup)

    for i, val in enumerate(coefs[2:-2]):
        pname = "{:s}_c{:d}".format(name, i)
        p = Parameter(value=val, name=pname, vary=True)
        setattr(group, pname, p)
    return group

def spline_eval(x, group, name='spl1'):
    """evaluate spline at specified x values

    arguments:
    ------------
      x       input 1-d array for absicca
      group   Group containing spline representation,
              as defined by spline_rep()
      name    name for spline params and subgroups ['spl1']

    returns:
    --------
      1-d array with interpolated values
    """
    sgroup = getattr(group, "{:s}_details".format(name), None)
    if sgroup is None or not isgroup(sgroup):
        raise Warning("spline_eval: subgroup '{:s}' not found".format(name))

    knots = getattr(sgroup, 'knots')
    order = getattr(sgroup, 'order')
    coefs = getattr(sgroup, 'coefs')
    for i, val in enumerate(coefs[2:-2]):
        pname = "{:s}_c{:d}".format(name, i)
        cval = getattr(group, pname, None)
        if cval is None:
            raise Warning("spline_eval: param'{:s}' not found".format(pname))
        if isParameter(cval):
            cval = cval.value
        coefs[2+i] = cval
    setattr(sgroup, 'coefs', coefs)
    return splev(x, [knots, coefs, order])
