#!/usr/bin/env python
"""
merge groups, interpolating if necessary
"""
import os
import numpy as np
from larch import Group
from larch.math import interp, interp1d, index_of, remove_dups
from larch.utils.logging import getLogger

_logger = getLogger("larch.io.mergegroups")

def merge_groups(grouplist, master=None, xarray='energy', yarray='mu',
                 kind='cubic', trim=True, calc_yerr=True):
    """merge arrays from a list of groups.

    Arguments
    ---------
     grouplist   list of groups to merge
     master      group to use for common x arrary [None -> 1st group]
     xarray      name of x-array for merge ['energy']
     yarray      name of y-array for merge ['mu']
     kind        interpolation kind ['cubic']
     trim        whether to trim to the shortest energy range [True]
     calc_yerr   whether to use the variance in the input as yerr [True]

    Returns
    --------
     group with x-array and y-array containing merged data.

    """
    if master is None:
        master = grouplist[0]

    xout = remove_dups(getattr(master, xarray))
    xmins = [min(xout)]
    xmaxs = [max(xout)]
    yvals = []

    for g in grouplist:
        x = getattr(g, xarray)
        y = getattr(g, yarray)
        yvals.append(interp(x, y, xout, kind=kind))
        xmins.append(min(x))
        xmaxs.append(max(x))

    yvals = np.array(yvals)
    yave = yvals.mean(axis=0)
    ystd = yvals.std(axis=0)

    xout_increasing = len(np.where(np.diff(np.argsort(xout))!=1)[0]) == 0
    if trim and xout_increasing:
        xmin = min(xmins)
        xmax = min(xmaxs)
        ixmin = index_of(xout, xmin)
        ixmax = index_of(xout, xmax)
        xout = xout[ixmin:ixmax]
        yave = yave[ixmin:ixmax]
        ystd = ystd[ixmin:ixmax]

    grp = Group()
    setattr(grp, xarray, xout)
    setattr(grp, yarray, yave)
    setattr(grp, yarray + '_std', ystd)

    if kind == 'cubic' and xout_increasing:
        y0 = getattr(master, yarray)
        # if the derivative gets much worse, use linear interpolation
        if max(np.diff(yave)) > 50*max(np.diff(y0)):
            grp = merge_groups(grouplist, master=master, xarray=xarray,
                               yarray=yarray, trim=trim,
                               calc_yerr=calc_yerr, kind='linear')
    return grp

def imin(arr, debug=False):
    """index of minimum value"""
    _im = np.argmin(arr)
    if debug:
        _logger.debug("Check: {0} = {1}".format(np.min(arr), arr[_im]))
    return _im


def imax(arr, debug=False):
    """index of maximum value"""
    _im = np.argmax(arr)
    if debug:
        _logger.debug("Check: {0} = {1}".format(np.max(arr), arr[_im]))
    return _im


def lists_to_matrix(data, axis=None, **kws):
    """Convert two lists of 1D arrays to a 2D matrix

    Parameters
    ----------
    data : list of lists of 1D arrays
        [
            [x1, ... xN]
            [z1, ... zN]
        ]
    axis : None or array 1D, optional
        a reference axis used for the interpolation [None -> xdats[0]]
    **kws : optional
        keyword arguments for scipy.interpolate.interp1d()

    Returns
    -------
    axis, outmat : arrays
    """
    assert len(data) == 2, "'data' should be a list of two lists"
    xdats, zdats = data
    assert isinstance(xdats, list), "'xdats' not a list"
    assert isinstance(zdats, list), "'zdats' not a list"
    assert len(xdats) == len(zdats), "lists of data not of the same length"
    assert all(isinstance(z, np.ndarray) for z in zdats), "data in list must be arrays"
    if axis is None:
        axis = xdats[0]
    assert isinstance(axis, np.ndarray), "axis must be array"
    if all(z.size == axis.size for z in zdats):
        #: all same size
        return axis, np.array(zdats)
    else:
        #: interpolate
        outmat = np.zeros((len(zdats), axis.size))
        for idat, (xdat, zdat) in enumerate(zip(xdats, zdats)):
            fdat = interp1d(xdat, zdat, **kws)
            znew = fdat(axis)
            outmat[idat] = znew
        return axis, outmat


def curves_to_matrix(curves, axis=None, **kws):
    """Convert a list of curves to a 2D data matrix

    Parameters
    ----------
    curves : list of lists
        Curves format is the following:
        [
            [x1, y1, label1, info1],
            ...
            [xN, yN, labelN, infoN]
        ]
    axis : None or array 1D, optional
        a reference axis used for the interpolation [None -> curves[0][0]]
    **kws : optional
        keyword arguments for func:`scipy.interpolate.interp1d`

    Returns
    -------
    axis, outmat : arrays
    """
    assert isinstance(curves, list), "'curves' not a list"
    assert all(
        (isinstance(curve, list) and len(curve) == 4) for curve in curves
    ), "curves should be lists of four elements"
    if axis is None:
        axis = curves[0][0]
    assert isinstance(axis, np.ndarray), "axis must be array"
    outmat = np.zeros((len(curves), axis.size))
    for icurve, curve in enumerate(curves):
        assert len(curve) == 4, "wrong curve format, should contain four elements"
        x, y, label, info = curve
        try:
            assert isinstance(x, np.ndarray), "not array!"
            assert isinstance(y, np.ndarray), "not array!"
        except AssertionError:
            _logger.error(
                "[curve_to_matrix] Curve %d (%s) not containing arrays -> ADDING ZEROS",
                icurve,
                label,
            )
            continue
        if (x.size == axis.size) and (y.size == axis.size):
            #: all same length
            outmat[icurve] = y
        else:
            #: interpolate
            fdat = interp1d(x, y, **kws)
            ynew = fdat(axis)
            outmat[icurve] = ynew
            _logger.debug("[curve_to_matrix] Curve %d (%s) interpolated", icurve, label)
    return axis, outmat


def sum_arrays_1d(data, axis=None, **kws):
    """Sum list of 1D arrays or curves by interpolation on a reference axis

    Parameters
    ----------
    data : lists of lists
    data_fmt : str
        define data format
        - "curves" -> :func:`curves_to_matrix`
        - "lists" -> :func:`curves_to_matrix`

    Returns
    -------
    axis, zsum : 1D arrays
    """
    data_fmt = kws.pop("data_fmt", "curves")
    if data_fmt == "curves":
        ax, mat = curves_to_matrix(data, axis=axis, **kws)
    elif data_fmt == "lists":
        ax, mat = lists_to_matrix(data, axis=axis, **kws)
    else:
        raise NameError("'data_fmt' not understood")
    return ax, np.sum(mat, 0)


def avg_arrays_1d(data, axis=None, weights=None, **kws):
    """Average list of 1D arrays or curves by interpolation on a reference axis

    Parameters
    ----------
    data : lists of lists
    data_fmt : str
        define data format
        - "curves" -> :func:`curves_to_matrix`
        - "lists" -> :func:`lists_to_matrix`
    weights : None or array
        weights for the average

    Returns
    -------
    axis, zavg : 1D arrays
        np.average(zdats)
    """
    data_fmt = kws.pop("data_fmt", "curves")
    if data_fmt == "curves":
        ax, mat = curves_to_matrix(data, axis=axis, **kws)
    elif data_fmt == "lists":
        ax, mat = lists_to_matrix(data, axis=axis, **kws)
    else:
        raise NameError("'data_fmt' not understood")
    return ax, np.average(mat, axis=0, weights=weights)


def merge_arrays_1d(data, method="average", axis=None, weights=None, **kws):
    """Merge a list of 1D arrays by interpolation on a reference axis

    Parameters
    ----------
    data : lists of lists
    data_fmt : str
        define data format
        - "curves" -> :func:`curves_to_matrix`
        - "lists" -> :func:`curves_to_matrix`
    axis : None or array 1D, optional
        a reference axis used for the interpolation [None -> xdats[0]]
    method : str, optional
        method used to merge, available methods are:
            - "average" : uses np.average()
            - "sum" : uses np.sum()
    weights : None or array 1D, optional
        used if method == "average"

    Returns
    -------
    axis, zmrg : 1D arrays
        merge(zdats)
    """
    if method == "sum":
        return sum_arrays_1d(data, axis=axis, **kws)
    elif method == "average":
        return avg_arrays_1d(data, axis=axis, weights=weights, **kws)
    else:
        raise NameError("wrong 'method': %s" % method)


def rebin_piecewise_constant(x1, y1, x2):
    """Rebin histogram values y1 from old bin edges x1 to new edges x2.

    Code taken from: https://github.com/jhykes/rebin/blob/master/rebin.py

    It follows the procedure described in Figure 18.13 (chapter 18.IV.B.
    Spectrum Alignment, page 703) of Knoll [1]

    References
    ----------
    [1] Glenn Knoll, Radiation Detection and Measurement, third edition,
        Wiley, 2000.

    Parameters
    ----------
     - x1 : m+1 array of old bin edges.
     - y1 : m array of old histogram values.
            This is the total number in each bin, not an average.
     - x2 : n+1 array of new bin edges.

    Returns
    -------
     - y2 : n array of rebinned histogram values.
    """
    x1 = np.asarray(x1)
    y1 = np.asarray(y1)
    x2 = np.asarray(x2)

    # the fractional bin locations of the new bins in the old bins
    i_place = np.interp(x2, x1, np.arange(len(x1)))

    cum_sum = np.r_[[0], np.cumsum(y1)]

    # calculate bins where lower and upper bin edges span
    # greater than or equal to one original bin.
    # This is the contribution from the 'intact' bins (not including the
    # fractional start and end parts.
    whole_bins = np.floor(i_place[1:]) - np.ceil(i_place[:-1]) >= 1.0
    start = cum_sum[np.ceil(i_place[:-1]).astype(int)]
    finish = cum_sum[np.floor(i_place[1:]).astype(int)]

    y2 = np.where(whole_bins, finish - start, 0.0)

    bin_loc = np.clip(np.floor(i_place).astype(int), 0, len(y1) - 1)

    # fractional contribution for bins where the new bin edges are in the same
    # original bin.
    same_cell = np.floor(i_place[1:]) == np.floor(i_place[:-1])
    frac = i_place[1:] - i_place[:-1]
    contrib = frac * y1[bin_loc[:-1]]
    y2 += np.where(same_cell, contrib, 0.0)

    # fractional contribution for bins where the left and right bin edges are in
    # different original bins.
    different_cell = np.floor(i_place[1:]) > np.floor(i_place[:-1])
    frac_left = np.ceil(i_place[:-1]) - i_place[:-1]
    contrib = frac_left * y1[bin_loc[:-1]]

    frac_right = i_place[1:] - np.floor(i_place[1:])
    contrib += frac_right * y1[bin_loc[1:]]

    y2 += np.where(different_cell, contrib, 0.0)

    return y2


def reject_outliers(data, m=5.189, return_ma=False):
    """Reject outliers

    Modified from: https://stackoverflow.com/questions/11686720/is-there-a-numpy-builtin-to-reject-outliers-from-a-list
    See also: https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d / (mdev if mdev else 1.0)
    mask = s < m
    if return_ma:
        imask = s > m
        return np.ma.masked_array(data=data, mask=imask)
    else:
        return data[mask]
