#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities to work with 2D grids and interpolation
=================================================
"""
from __future__ import division, print_function

import warnings
import numpy as np
from scipy.interpolate import griddata

from larch.utils.logging import getLogger

_logger = getLogger("gridxyz")

### GLOBAL VARIABLES ###
MODNAME = "_math"


def gridxyz(xcol, ycol, zcol, xystep=None, method="linear"):
    """Grid (X, Y, Z) 1D data on a 2D regular mesh

    Parameters
    ----------
    xcol, ycol, zcol : numpy.ndarray
        1D arrays representing the map (z is the signal intensity)

    xystep : float or None (optional)
        the step size of the XY grid, if None -> 0.1

    method : str, optional ["cubic"]
        interpolation method
            - nearest
            - linear
            - cubic

    Returns
    -------
        xgrid, ygrid, zz : numpy.ndarray
            xgrid, ygrid : 1D arrays giving abscissa and ordinate of the map
            zz : 2D array with the gridded intensity map

    See also
    --------
        - MultipleScanToMeshPlugin in PyMca
    """
    if xystep is None:
        xystep = 0.1
        _logger.warning(
            f"'xystep' not given: using a default value of {xystep}")

    assert type(xystep) is float, "xystep should be float"
    # create the XY meshgrid and interpolate the Z on the grid
    nxpoints = int((xcol.max() - xcol.min()) / xystep)
    nypoints = int((ycol.max() - ycol.min()) / xystep)
    xgrid = np.linspace(xcol.min(), xcol.max(), num=nxpoints)
    ygrid = np.linspace(ycol.min(), ycol.max(), num=nypoints)
    xx, yy = np.meshgrid(xgrid, ygrid)

    _logger.info(f"Gridding data with {method=}")
    zz = griddata( (xcol, ycol),  zcol,
        (xgrid[None, :], ygrid[:, None]),
        method=method, fill_value=np.nan)

    return xgrid, ygrid, zz
