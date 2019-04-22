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

from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.linear_model import LassoLarsCV, LassoLars, LassoCV, Lasso


from .. import Group
from .utils import interp, index_of

from lmfit import minimize, Parameters

from .lincombo_fitting import get_arrays, get_label, groups2matrix

def pls_train(groups, varname='valence', arrayname='norm', scale=True,
              cv_folds=None, cv_repeats=None, skip_cv=False,
              xmin=-np.inf, xmax=np.inf, _larch=None, **kws):

    """use a list of data groups to train a Partial Least Squares model

    Arguments
    ---------
      groups      list of groups to use as components
      varname     name of characteristic value to model ['valence']
      arrayname   string of array name to be fit (see Note 3) ['norm']
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]
      scale       bool to scale data [True]
      cv_folds    None or number of Cross-Validation folds (Seee Note 4) [None]
      cv_repeats  None or number of Cross-Validation repeats (Seee Note 4) [None]
      skip_cv     bool to skip doing Cross-Validation [None]

    Returns
    -------
      group with trained PSLResgession, to be used with pls_predic

    Notes
    -----
     1.  The group members for the components must match each other
         in data content and array names.
     2.  all grouops must have an attribute (scalar value) for `varname`
     3.  arrayname can be one of `norm` or `dmude`
     4.  Cross-Validation:  if cv_folds is None, sqrt(len(groups)) will be used
            (rounded to integer).  if cv_repeats is None, sqrt(len(groups))-1
            will be used (rounded).
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

    nvals = len(groups)

    kws.update(dict(scale=scale))
    model = PLSRegression(n_components=1, **kws)

    rmse_cv = None
    if not skip_cv:
        if cv_folds is None:
            cv_folds = int(round(np.sqrt(nvals)))
        if  cv_repeats is None:
            cv_repeats = int(round(np.sqrt(nvals)) - 1)

        resid = []
        cv = RepeatedKFold(n_splits=cv_folds, n_repeats=cv_repeats)
        for ctrain, ctest in cv.split(range(nvals)):
            model.fit(spectra[ctrain, :], ydat[ctrain])
            ypred = model.predict(spectra[ctest, :])[:, 0]
            resid.extend((ypred - ydat[ctest]).tolist())
        resid = np.array(resid)
        rmse_cv = np.sqrt( (resid**2).mean() )

    # final fit without cross-validation
    out = model.fit(spectra, ydat)

    ypred = model.predict(spectra)[:, 0]

    rmse = np.sqrt(((ydat - ypred)**2).mean())

    return Group(x=xdat, spectra=spectra, ydat=ydat, ypred=ypred,
                 coefs=model.x_weights_[:, 0],
                 cv_folds=cv_folds, cv_repeats=cv_repeats, rmse_cv=rmse_cv,
                 rmse=rmse, model=model, varname=varname,
                 arrayname=arrayname, scale=scale, groupnames=groupnames,
                 keywords=kws)



def lasso_train(groups, varname='valence', arrayname='norm', alpha=None,
                use_lars=True, fit_intercept=True, normalize=True,
                cv_folds=None, cv_repeats=None, skip_cv=False,
                xmin=-np.inf, xmax=np.inf, _larch=None, **kws):

    """use a list of data groups to train a Lasso/LassoLars model

    Arguments
    ---------
      groups      list of groups to use as components
      varname     name of characteristic value to model ['valence']
      arrayname   string of array name to be fit (see Note 3) ['norm']
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]
      alpha       alpha parameter for LassoLars (See Note 5) [None]
      use_lars    bool to use LassoLars instead of Lasso [True]
      cv_folds    None or number of Cross-Validation folds (Seee Note 4) [None]
      cv_repeats  None or number of Cross-Validation repeats (Seee Note 4) [None]
      skip_cv     bool to skip doing Cross-Validation [None]

    Returns
    -------
      group with trained LassoLars model, to be used with lasso_predict
    Notes
    -----
     1.  The group members for the components must match each other
         in data content and array names.
     2.  all grouops must have an attribute (scalar value) for `varname`
     3.  arrayname can be one of `norm` or `dmude`
     4.  Cross-Validation:  if cv_folds is None, sqrt(len(groups)) will be used
            (rounded to integer).  if cv_repeats is None, sqrt(len(groups))-1
            will be used (rounded).
     5.  alpha is the regularization parameter. if alpha is None it will
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

    nvals = len(groups)

    kws.update(dict(fit_intercept=fit_intercept, normalize=normalize))
    creator = LassoLars if use_lars else Lasso
    model = None

    rmse_cv = None
    if not skip_cv:
        if cv_folds is None:
            cv_folds = int(round(np.sqrt(nvals)))
        if  cv_repeats is None:
            cv_repeats = int(round(np.sqrt(nvals)) - 1)

        cv = RepeatedKFold(n_splits=cv_folds, n_repeats=cv_repeats)
        if alpha is None:
            alpha = LassoLarsCV(cv=cv, max_n_alphas=1e7,
                                max_iter=1e7, eps=1.e-12, **kws).alpha_

        model = creator(alpha=alpha, **kws)
        resid = []
        for ctrain, ctest in cv.split(range(nvals)):
            model.fit(spectra[ctrain, :], ydat[ctrain])
            ypred = model.predict(spectra[ctest, :])
            resid.extend((ypred - ydat[ctest]).tolist())
        resid = np.array(resid)
        rmse_cv = np.sqrt( (resid**2).mean() )

    if alpha is None:
        cvmod = creator(**kws)
        cvmod.fit(spectra, ydat)
        alpha = cvmod.alpha_

    if model is None:
        model = creator(alpha=alpha, **kws)

    # final fit without cross-validation
    out = model.fit(spectra, ydat)

    ypred = model.predict(spectra)

    rmse = np.sqrt(((ydat - ypred)**2).mean())

    return Group(x=xdat, spectra=spectra, ydat=ydat, ypred=ypred,
                 alpha=alpha, active=model.active_, coefs=model.coef_,
                 cv_folds=cv_folds, cv_repeats=cv_repeats,
                 rmse_cv=rmse_cv, rmse=rmse, model=model, varname=varname,
                 arrayname=arrayname, fit_intercept=fit_intercept,
                 normalize=normalize, groupnames=groupnames, keywords=kws)


def _predict(group, model):
    """internal use """
    # generate arrays and interpolate components onto the unknown x array
    xdat, ydat = get_arrays(group, model.arrayname)
    if xdat is None or ydat is None:
        raise ValueError("cannot get arrays for arrayname='%s'" % arrayname)

    spectra = interp(xdat, ydat, model.x, kind='cubic')
    spectra.shape = (1, len(spectra))
    return model.model.predict(spectra)[0]

def lasso_predict(group, model, _larch=None):
    """
    Predict the external value for a group based on a Lasso model

    Arguments
    ---------
      group   group with data to fit
      model   Lasso/LassoLars model as found from lasso_train()

    Returns
    -------
      predict value of external variable for the group
    """
    if not model.__repr__().startswith('Lasso'):
        raise ValueError("pls_predict needs a Lasso training model")
    return _predict(group, model)

def pls_predict(group, model, _larch=None):
    """
    Predict the external value for a group based on a PLS model

    Arguments
    ---------
      group    group with data to fit
      model    PLS model as found from pls_train()

    Returns
    -------
      predict value of external variable for the group
    """
    if not model.__repr__().startswith('PLS'):
        raise ValueError("pls_predict needs a PLS training model")
    return _predict(group, model)
