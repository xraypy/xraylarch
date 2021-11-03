#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Deglitch utilities
=====================

"""
import logging
import numpy as np

_logger = logging.getLogger(__name__)


def remove_spikes_medfilt1d(y_spiky, backend="silx", kernel_size=3, threshold=0.1):
    """Remove spikes in a 1D array using medfilt from silx.math

    Parameters
    ----------
    y_spiky : array
        spiky data

    backend : str, optional
        library to use as backend
        - 'silx' -> from silx.math.medianfilter import medfilt1d
        - 'pymca' -> from PyMca5.PyMcaMath.PyMcaSciPy.signal import medfilt1d
        - 'pandas' : TODO

    kernel_size : int, optional
        kernel size where to calculate median, must be odd [3]

    threshold : float, optional
        relative difference between filtered and spiky data [0.1]

    Returns
    -------
    array
        filtered array
    """
    ynew = np.zeros_like(y_spiky)
    if not (kernel_size % 2):
        kernel_size += 1
        _logger.warning("'kernel_size' must be odd -> adjusted to %d", kernel_size)
    if backend == "silx":
        return remove_spikes_silx(y_spiky, kernel_size=kernel_size, threshold=threshold)
    elif backend == "pymca":
        return remove_spikes_silx(y_spiky, kernel_size=kernel_size, threshold=threshold)
    elif backend == "pandas":
        return remove_spikes_pandas(y_spiky, window=kernel_size, threshold=threshold)
    else:
        _logger.warning("backend for medfilt1d not found! -> returning zeros")
        return ynew


def remove_spikes_silx(y_spiky, kernel_size=3, threshold=0.1):
    """Remove spikes in a 1D array using medfilt from silx.math

    Parameters
    ----------
    y_spiky : array
        spiky data

    kernel_size : int, optional
        kernel size where to calculate median, must be odd [3]

    threshold : float, optional
        difference between filtered and spiky data relative [0.1]

    Returns
    -------
    array
        filtered array
    """
    ynew = np.zeros_like(y_spiky)
    try:
        from silx.math.medianfilter import medfilt1d
    except ImportError:
        _logger.warning("medfilt1d (from SILX) not found! -> returning zeros")
        return ynew
    y_filtered = medfilt1d(
        y_spiky, kernel_size=kernel_size, conditional=True, mode="nearest", cval=0
    )
    diff = y_filtered - y_spiky
    rel_diff = diff / y_filtered
    ynew = np.where(abs(rel_diff) > threshold, y_filtered, y_spiky)
    return ynew


def remove_spikes_pymca(y_spiky, kernel_size=9, threshold=0.66):
    """Remove spikes in a 1D array using medfilt from PyMca5.PyMcaMath.PyMcaScipy.signal

    Parameters
    ----------
    y_spiky : array
        spiky data

    kernel_size : int, optional
        kernel size where to calculate median, should be odd [9]

    threshold : float, optional
        difference between filtered and spiky data in sigma units [0.66]

    Returns
    -------
    array
        filtered array
    """
    ynew = np.zeros_like(y_spiky)
    try:
        from PyMca5.PyMcaMath.PyMcaSciPy.signal import medfilt1d
    except ImportError:
        _logger.warning("medfilt1d (from PyMca5) not found! -> returning zeros")
        return ynew
    y_filtered = medfilt1d(y_spiky, kernel_size)
    diff = y_filtered - y_spiky
    mean = diff.mean()
    sigma = (y_spiky - mean) ** 2
    sigma = np.sqrt(sigma.sum() / float(len(sigma)))
    ynew = np.where(abs(diff) > threshold * sigma, y_filtered, y_spiky)
    return ynew


def remove_spikes_pandas(y, window=3, threshold=3):
    """remove spikes using pandas

    Taken from `https://ocefpaf.github.io/python4oceanographers/blog/2015/03/16/outlier_detection/`_

    .. note:: this will not work in pandas > 0.17 one could simply do
              `df.rolling(3, center=True).median()`; also
              df.as_matrix() is deprecated, use df.values instead

    Parameters
    ----------
    y : array 1D
    window : int (optional)
        window in rolling median [3]
    threshold : int (optional)
        number of sigma difference with original data

    Return
    ------
    ynew : array like x/y
    """
    ynew = np.zeros_like(y)
    try:
        import pandas as pd
    except ImportError:
        _logger.error("pandas not found! -> returning zeros")
        return ynew
    df = pd.DataFrame(y)
    try:
        yf = (
            pd.rolling_median(df, window=window, center=True)
            .fillna(method="bfill")
            .fillna(method="ffill")
        )
        diff = yf.as_matrix() - y
        mean = diff.mean()
        sigma = (y - mean) ** 2
        sigma = np.sqrt(sigma.sum() / float(len(sigma)))
        ynew = np.where(abs(diff) > threshold * sigma, yf.as_matrix(), y)
    except Exception:
        yf = (
            df.rolling(window, center=True)
            .median()
            .fillna(method="bfill")
            .fillna(method="ffill")
        )

        diff = yf.values - y
        mean = diff.mean()
        sigma = (y - mean) ** 2
        sigma = np.sqrt(sigma.sum() / float(len(sigma)))
        ynew = np.where(abs(diff) > threshold * sigma, yf.values, y)

        # ynew = np.array(yf.values).reshape(len(x))
    return ynew
