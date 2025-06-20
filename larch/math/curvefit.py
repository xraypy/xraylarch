#!/usr/bin/env python
"""
  general curve-fitting
"""
import time
from string import printable
from copy import deepcopy
import numpy as np
from lmfit import Parameters, Minimizer, Model
from lmfit.models import (LorentzianModel, GaussianModel, VoigtModel,
                          ConstantModel, LinearModel, QuadraticModel,
                          StepModel)

from xraydb import guess_edge, xray_edge, core_width

from larch import Group, isgroup
from larch.larchlib import Make_CallArgs, parse_group_args

from . import index_of, index_nearest, remove_nans2,  peak_indices

from larch.fitting import dict2params


@Make_CallArgs(["x", "y"])
def curvefit_setup(x, y=None, group=None, xmin=None, xmax=None):
    """set up larch Group for curve fitting

    Arguments:
       xdat (ndarray or group): array of x-values, or group (see note 1)
       ydat (ndarray or None):  array of y-vales, or None
       group (group or None): output group
       xmin: (float or None)  low x-value for fit
       xmax: (float or None)  high x-value for fit

    A group named `curvefit` will be created in the output group, containing:

       .xdat, .ydat

    Notes:
        1. Supports :ref:`First Argument Group` convention, requiring group members `x` and `y`
    """
    xdat, ydat, group = parse_group_args(x, members=('xdat', 'ydat'), defaults=(y,), group=group,
                                   fcn_name='curvefit_setup')

    if len(xdat.shape) > 1:
        xdat = xdat.squeeze()
    if len(ydat.shape) > 1:
        ydat = ydat.squeeze()

    dat_xmin, dat_xmax = min(xdat), max(xdat)

    if xmin > xmax:
        xmin, xmax = xmax, xmin

    delx = 1.e-13 + min(np.diff(xdat))/5.0

    imin = index_of(xdat, xmin+delx)
    imax = index_of(xdat, xmax+delx)

    xdat = xdat[imin:imax+1]
    ydat = ydat[imin:imax+1]

    if not hasattr(group, 'curvefit'):
        group.curvefit = Group(xdat=xdat, ydat=ydat, xmin=xmin, xmax=xmax)
    else:
        group.curvefit.xdat = xdat*1.0
        group.curvefit.ydat = ydat*1.0
        group.curvefit.xmin = xmin
        group.curvefit.xmax = xmax

    group.curvefit.xplot = xdat
    group.curvefit.yplot = ydat
    return

def curvefit_run(group, model, params, user_options=None):
    """do curve fitting - must be done after setting up the fit
    returns a group with curvefit data, including `result`, the lmfit ModelResult

    """
    curvefit = getattr(group, 'curvefit', None)
    if curvefit is None:
        raise ValueError("must run curvefit_setup() for a group before doing fit")

    if not isinstance(model, Model):
        raise ValueError("curvefit mode must be an lmfit.Model")

    if isinstance(params, dict):
        params = dict2params(params)

    if not isinstance(params, Parameters):
        raise ValueError("params must be an lmfit.Parameters")

    if not hasattr(curvefit, 'fit_history'):
        curvefit.fit_history = []

    fit = Group()

    for k in ('xdat', 'ydat', 'y_std', 'user_options'):
        if hasattr(curvefit, k):
            setattr(fit, k, deepcopy(getattr(curvefit, k)))

    if user_options is not None:
        fit.user_options = user_options

    fit.init_fit     = model.eval(params, x=curvefit.xdat)
    fit.init_ycomps  = model.eval_components(params=params, x=curvefit.xdat)

    y_mean = abs(curvefit.ydat).mean()
    y_std = getattr(group, 'y_std', 1.0)
    if isinstance(y_std, np.ndarray):
        ysmin = 1.e-13*y_mean
        y_std[np.where(y_std<ysmin)] = ysmin
    elif y_std < 0:
        y_std = 1.0

    fit.result = model.fit(curvefit.ydat, params=params, x=curvefit.xdat,  weights=1.0/y_std)
    fit.ycomps = model.eval_components(params=fit.result.params, x=curvefit.xdat)
    fit.label = 'Fit %i' % (1+len(curvefit.fit_history))

    label = now  = time.strftime("%b-%d %H:%M")
    fit.timestamp = time.strftime("%Y-%b-%d %H:%M")
    fit.label = label


    fitlabels = [fhist.label for fhist in curvefit.fit_history]
    if label in fitlabels:
        count = 1
        while label in fitlabels:
            label = f'{now:s}_{printable[count]:s}'
            count +=1
        fit.label = label

    curvefit.fit_history.insert(0, fit)
    return fit
