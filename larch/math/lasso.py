#!/usr/bin/env python
"""
linear combination fitting
"""
import os
import sys

from collections import OrderedDict
from glob import glob

import numpy as np
from numpy.random import randint

from sklearn.linear_model import LassoLarsCV, LassoLars, LassoCV, Lasso

from .. import Group
from .utils import interp, index_of

from lmfit import minimize, Parameters

from .lincombo_fitting import get_arrays, get_label, groups2matrix

def lasso_train(groups, varname='lassoval', arrayname='norm',
                alpha=None, use_lars=True, fit_intercept=True,
                normalize=True, xmin=-np.inf, xmax=np.inf, _larch=None, **kws):

    """use a list of data groups to train a Lasso/LassoLars analysis

    Arguments
    ---------
      groups      list of groups to use as components
      varname     name of characteristic value to model ['lassoval']
      arrayname   string of array name to be fit (see Note 3) ['norm']
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]
      alpha       alpha parameter for LassoLars (See Note 4) [None]
      use_lars    bool to use LassoLars [True]

    Returns
    -------
      group with trained LassoLars model, to be used with lasso_fit

    Notes
    -----
     1.  The group members for the components must match each other
         in data content and array names.
     2.  all grouops must have an attribute (scalar value) for `varname`
     2.  arrayname can be one of `norm` or `dmude`
     4.  alphaa is the regularization parameter. if alpha is None it will
         be set using LassoLarsSCV
    """
    xdat, spectra = groups2matrix(groups, arrayname, xmin=xmin, xmax=xmax)
    groupnames = []
    ydat = []
    for g in groups:
        groupnames.append(getattr(g, 'filename',
                                  getattr(g, 'groupname', repr(g))))
        val = getattr(g, varname, None)
        if val is None:
            raise Value("group '%s' does not have attribute '%s'" % (g, varname))
        ydat.append(val)
    ydat = np.array(ydat)

    if alpha is None:
        cvfunc = LassoLarsCV if use_lars else LassoCV
        cvmod = cvfunc(fit_intercept=fit_intercept, normalize=normalize)
        cvmod.fit(spectra, ydat)
        alpha = cvmod.alpha_

    lfunc = LassoLars if use_lars else Lasso
    model = lfunc(alpha=alpha, fit_intercept=fit_intercept, normalize=normalize, **kws)
    out = model.fit(spectra, ydat)

    ypred = model.predict(spectra)

    rmse = np.sqrt(((ydat - ypred)**2).mean())

    return Group(x=xdat, spectra=spectra, ydat=ydat, ypred=ypred, alpha=alpha,
                 active=model.active_, coef=model.coef_, rmse=rmse,
                 model=model, varname=varname, arrayname=arrayname,
                 fit_intercept=fit_intercept, normalize=normalize,
                 groupnames=groupnames, keywords=kws)

def lasso_predict(group, lasso_model, _larch=None):
    """
    Predict the external value for a group based on a Lasso model

    Arguments
    ---------
      group         group with data to fit
      lasso_model   Lasso/LassoLars model as found from lasso_train()

    Returns
    -------
      predict value of external variable for the group
    """
    # get first nerate arrays and interpolate components onto the unknown x array
    xdat, spectra = get_arrays(group, lasso_model.arrayname)
    if xdat is None or ydat is None:
        raise ValueError("cannot get arrays for arrayname='%s'" % arrayname)

    spectra = interp(xdat, spectra, lasso_model.x, kind='cubic')
    return lasso_model.predict(spectra)
