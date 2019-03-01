#!/usr/bin/env python
"""
linear combination fitting
"""
import os
import sys
import time

from itertools import combinations
from collections import OrderedDict
from glob import glob

import numpy as np
from numpy.random import randint

from sklearn.decomposition import PCA

from .. import Group
from .utils import interp, index_of

from lmfit import minimize, Parameters

from .lincombo_fitting import get_arrays, get_label

def pca_train(groups, arrayname='norm', xmin=-np.inf, xmax=np.inf):
    """use a list of data groups to train a Principal Component Analysis model

    Arguments
    ---------
      groups      list of groups to use as components
      arrayname   string of array name to be fit (see Note 2) ['norm']
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]

    Returns
    -------
      group with trained PCA model, to be used with pca_fit

    Notes
    -----
     1.  The group members for the components must match each other
         in data content and array names.
     2.  arrayname can be one of `norm` or `dmude`
    """

    # get first nerate arrays and interpolate components onto the unknown x array
    xdat, ydat = get_arrays(groups[0], arrayname)
    if xdat is None or ydat is None:
        raise ValueError("cannot get arrays for arrayname='%s'" % arrayname)

    imin, imax = None, None
    if xmin is not None:
        imin = index_of(xdat, xmin)
    if xmax is not None:
        imax = index_of(xdat, xmax) + 1

    xdat = xdat[slice(imin, imax)]
    ydat = ydat[slice(imin, imax)]

    # gather the rest of the components
    ydat = [ydat]
    for g in groups[1:]:
        x, y = get_arrays(g, arrayname)
        ydat.append(interp(x, y, xdat, kind='cubic'))
    ydat = np.array(ydat)

    ret = PCA().fit(ydat)
    labels = [get_label(g) for g  in groups]
    return Group(x=xdat, arrayname=arrayname, labels=labels, ydat=ydat,
                 xmin=xmin, xmax=xmax, pcamodel=ret, mean=ret.mean_,
                 components=ret.components_,
                 variances=ret.explained_variance_ratio_)


def _pca_scale_resid(params, ydat=None, pca_model=None, comps=None):
    scale = params['scale'].value
    weights, chi2, rank, s = np.linalg.lstsq(comps, ydat*scale-pca_model.mean)
    yfit = (weights * comps).sum(axis=1) + pca_model.mean
    return (scale*ydat - yfit)


def pca_fit(group, pca_model, ncomps=None, rescale=True, _larch=None):
    """
    fit a spectrum from a group to a pca training model from pca_train()

    Arguments
    ---------
      group       group with data to fit
      pca_model   PCA model as found from pca_train()
      ncomps      number of components to included
      rescale     whether to allow data to be renormalized (True)

    Returns
    -------
      None, the group will have a subgroup name `pca_result` created
            with the following members:

          x          x or energy value from model
          ydat       input data interpolated onto `x`
          yfit       linear least-squares fit using model components
          weights    weights for PCA components
          chi_square goodness-of-fit measure
          pca_model  the input PCA model

    """
    # get first nerate arrays and interpolate components onto the unknown x array
    xdat, ydat = get_arrays(group, pca_model.arrayname)
    if xdat is None or ydat is None:
        raise ValueError("cannot get arrays for arrayname='%s'" % arrayname)

    ydat = interp(xdat, ydat, pca_model.x, kind='cubic')

    params = Parameters()
    params.add('scale', value=1.0, vary=True, min=0)

    if ncomps is None:
        ncomps=len(pca_model.components)
    comps = pca_model.components[:ncomps].transpose()

    if rescale:
        weights, chi2, rank, s = np.linalg.lstsq(comps, ydat-pca_model.mean)
        yfit = (weights * comps).sum(axis=1) + pca_model.mean

        result = minimize(_pca_scale_resid, params, method='leastsq',
                          gtol=1.e-5, ftol=1.e-5, xtol=1.e-5, epsfcn=1.e-5,
                          kws = dict(ydat=ydat, comps=comps, pca_model=pca_model))
        scale = result.params['scale'].value
        ydat *= scale
        weights, chi2, rank, s = np.linalg.lstsq(comps, ydat-pca_model.mean)
        yfit = (weights * comps).sum(axis=1) + pca_model.mean

    else:
        weights, chi2, rank, s = np.linalg.lstsq(comps, ydat-pca_model.mean)
        yfit = (weights * comps).sum(axis=1) + pca_model.mean
        scale = 1.0

    group.pca_result = Group(x=pca_model.x, ydat=ydat, yfit=yfit,
                             pca_model=pca_model, chi_square=chi2[0],
                             data_scale=scale, weights=weights)
    return


def registerLarchPlugin():
    return ('_math', {'pca_train': pca_train,
                      'pca_fit': pca_fit})
