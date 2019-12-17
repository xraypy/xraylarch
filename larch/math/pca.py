#!/usr/bin/env python
"""
linear combination fitting
"""
import os
import sys
import time

from itertools import combinations
from collections import OrderedDict

import numpy as np
from numpy.random import randint

try:
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


from .. import Group
from .utils import interp, index_of

from lmfit import minimize, Parameters

from .lincombo_fitting import get_arrays, get_label, groups2matrix


def nmf_train(groups, arrayname='norm', xmin=-np.inf, xmax=np.inf,
              solver='cd', beta_loss=2):
    """use a list of data groups to train a Non-negative model

    Arguments
    ---------
      groups      list of groups to use as components
      arrayname   string of array name to be fit (see Note 2) ['norm']
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]
      beta_loss   beta parameter for NMF [2]

    Returns
    -------
      group with trained NMF model, to be used with pca_fit

    Notes
    -----
     1.  The group members for the components must match each other
         in data content and array names.
     2.  arrayname can be one of `norm` or `dmude`
    """
    xdat, ydat = groups2matrix(groups, arrayname, xmin=xmin, xmax=xmax)

    ydat[np.where(ydat<0)] = 0
    opts = dict(n_components=len(groups), solver=solver)
    if solver == 'mu':
        opts.update(dict(beta_loss=beta_loss))
    ret = NMF(**opts).fit(ydat)
    labels = [get_label(g) for g  in groups]

    return Group(x=xdat, arrayname=arrayname, labels=labels, ydat=ydat,
                 components=ret.components_,
                 xmin=xmin, xmax=xmax, model=ret)


def pca_train_sklearn(groups, arrayname='norm', xmin=-np.inf, xmax=np.inf):
    """use a list of data groups to train a Principal Component Analysis

    Arguments
    ---------
      groups      list of groups to use as components
      arrayname   string of array name to be fit (see Note 2) ['norm']
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]

    Returns
    -------
      group with trained PCA or N model, to be used with pca_fit

    Notes
    -----
     1.  The group members for the components must match each other
         in data content and array names.
     2.  arrayname can be one of `norm` or `dmude`
    """
    xdat, ydat = groups2matrix(groups, arrayname, xmin=xmin, xmax=xmax)
    if not HAS_SKLEARN:
        raise ImportError("scikit-learn not installed")

    ret = PCA().fit(ydat)
    labels = [get_label(g) for g  in groups]

    return Group(x=xdat, arrayname=arrayname, labels=labels, ydat=ydat,
                 xmin=xmin, xmax=xmax, model=ret, mean=ret.mean_,
                 components=ret.components_,
                 variances=ret.explained_variance_ratio_)


def pca_athena(groups, arrayname='norm', subtract_mean=True,
               normalize=True, xmin=-np.inf, xmax=np.inf):
    xdat, data = groups2matrix(groups, arrayname, xmin=xmin, xmax=xmax)
    if subtract_mean:
        data = data - data.mean(axis=0)

    data = data.T
    data = data - data.mean(axis=0)
    if normalize:
        data = data / data.std(axis=0)

    cor = np.dot(data.T, data) / data.shape[0]
    evals, var = np.linalg.eigh(cor)
    iorder = np.argsort(evals)[::-1]
    evals = evals[iorder]
    evec = np.dot(data, var)[:, iorder]
    return evec, evals

def pca_train(groups, arrayname='norm', xmin=-np.inf, xmax=np.inf):
    """use a list of data groups to train a Principal Component Analysis

    Arguments
    ---------
      groups      list of groups to use as components
      arrayname   string of array name to be fit (see Note 2) ['norm']
      xmin        x-value for start of fit range [-inf]
      xmax        x-value for end of fit range [+inf]

    Returns
    -------
      group with trained PCA or N model, to be used with pca_fit

    Notes
    -----
     1.  The group members for the components must match each other
         in data content and array names.
     2.  arrayname can be one of `norm` or `dmude`
    """
    xdat, ydat = groups2matrix(groups, arrayname, xmin=xmin, xmax=xmax)
    labels = [get_label(g) for g  in groups]
    narr, nfreq = ydat.shape

    ymean = ydat.mean(axis=0)
    ynorm = ydat - ymean

    # normalize data to be centered at 0 with unit standard deviation
    ynorm = (ynorm.T - ynorm.mean(axis=1)) / ynorm.std(axis=1)
    eigval, eigvec_ = np.linalg.eigh(np.dot(ynorm.T, ynorm) / narr)
    eigvec = (np.dot(ynorm, -eigvec_)/narr).T
    eigvec, eigval = eigvec[::-1, :], eigval[::-1]

    variances = eigval/eigval.sum()

    # calculate IND statistic
    ind = None
    for r in range(narr-1):
        nr = narr - r - 1
        indval = np.sqrt(nfreq*eigval[r:].sum()/nr)/nr**2
        if ind is None:
            ind = [indval]
        ind.append(indval)
    ind = np.array(ind)

    nsig = np.argmin(ind)
    return Group(x=xdat, arrayname=arrayname, labels=labels, ydat=ydat,
                 xmin=xmin, xmax=xmax, mean=ymean, components=eigvec,
                 eigenvalues=eigval, variances=variances, ind=ind, nsig=nsig)

def pca_statistics(pca_model):
    """return PCA arrays of statistics IND and F

    For data of shape (p, n) (that is, p frequencies/energies, n spectra)

    For index r, and eigv = eigenvalues

      IND(r) =  sqrt( eigv[r:].sum() / (p*(n-r))) / (n-r)**2

      F1R(r) = eigv[r] / (p+1-r)*(n+1-r) / sum_i=r^n-1 (eigv[i] / ((p+1-i)*(n+1-i)))
    """
    p, n = pca_model.ydat.shape
    eigv = pca_model.eigenvalues
    ind, f1r = [], []
    for r in range(n-1):
        nr = n-r-1
        ind.append( np.sqrt(eigv[r:].sum()/ (p*nr))/nr**2)
        f1sum = 0
        for i in range(r, n):
            f1sum += eigv[i]/((p+1-i)*(n+1-i))
        f1sum = max(1.e-10, f1sum)
        f1r.append(eigv[r] / (max(1, (p+1-r)*(n-r+1)) * f1sum))

    pca_model.ind = np.array(ind)
    pca_model.f1r = np.array(f1r)

    return pca_model.ind, pca_model.f1r

def _pca_scale_resid(params, ydat=None, pca_model=None, comps=None):
    scale = params['scale'].value
    weights, chi2, rank, s = np.linalg.lstsq(comps, ydat*scale-pca_model.mean)
    yfit = (weights * comps).sum(axis=1) + pca_model.mean
    return (scale*ydat - yfit)


def pca_fit(group, pca_model, ncomps=None, rescale=True):
    """
    fit a spectrum from a group to a PCA training model from pca_train()

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
