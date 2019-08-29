#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RIXS data object
================
"""
import numpy as np
from scipy.interpolate import griddata
from silx.io.dictdump import (dicttoh5, h5todict)

from larch.math.gridxyz import gridxyz
from larch.utils.logging import getLogger
_logger = getLogger('rixsdata')  #: module logger


def _tostr(arr):
    """Numpy array to string"""
    return arr.tostring().decode()


class RixsData(object):
    """RIXS plane object"""

    #: loaded from dictionary/HDF5 -> self.load_from_h5()
    sample_name = 'Unknown'
    counter_all, counter_signal, counter_norm = None, None, None
    _x, _y, _z = None, None, None
    ene_in, ene_out, rixs_map = None, None, None
    ene_et, rixs_et_map = None, None
    ene_grid, ene_unit = None, None

    #: setted by self.crop()
    ene_in_crop, ene_out_crop, rixs_map_crop = None, None, None

    grid_method = 'nearest'
    grid_lib = 'scipy'

    _plotter = None

    def __init__(self, name=None, logger=None):
        """Constructor"""

        self.__name__ = name or 'RixsData_{0}'.format(hex(id(self)))
        self._logger = logger or _logger

    def _init_axis_labels(self, unit=None):
        try:
            unit.decode()
        except AttributeError:
            pass
        self.ene_in_label = 'Incoming energy ({0})'.format(unit)
        self.ene_out_label = 'Emitted energy ({0})'.format(unit)
        self.ene_et_label = 'Energy transfer ({0})'.format(unit)

    def load_from_dict(self, rxdict):
        """Load RIXS data from a dictionary

        Parameters
        ----------
        rxdict : dict
            Minimal required structure
            {
             'writer_version': '1.5',
             'sample_name': str,
             '_x': 1D array,
             '_y': 1D array,
             '_z': 1D array,
            }

        Return
        ------
        None, set attributes: self.*
        """
        self.__dict__.update(rxdict)
        self._init_axis_labels(unit=_tostr(self.ene_unit))
        self.grid_rixs_from_col()

    def load_from_h5(self, fname):
        """Load RIXS from HDF5 file"""
        rxdict = h5todict(fname)
        if not ('writer_version' in rxdict.keys()):
            self._logger.error("Key 'writer_version' not found")
            return
        if not (_tostr(rxdict['writer_version']) == '1.5'):
            self._logger.warning('Data format not understood')
            return
        rxdict['sample_name'] = _tostr(rxdict['sample_name'])
        self.load_from_dict(rxdict)
        self._logger.info("RIXS map loaded from file: {0}".format(fname))

    def save_to_h5(self, fname):
        """Dump dictionary representation to HDF5 file"""
        dicttoh5(self.__dict__)
        self._logger.info("RixsData saved to {0}".format(fname))

    def crop(self, crop_area, yet=False):
        """Crop the plane in a given range

        Parameters
        ----------
        crop_area : tuple
            (x1, y1, x2, y2) : floats
            x1 < x2 (ene_in)
            y1 < y2 (if yet=False: ene_out, else: ene_et)
        yet: bool
            if True: y1, y2 are given in energy transfer [False]
        """
        self._crop_area = crop_area
        x1, y1, x2, y2 = crop_area
        _xystep = self.ene_grid or 0.1
        _method = self.grid_method or 'nearest'

        _nxpts = int((x2-x1)/_xystep)
        _xcrop = np.linspace(x1, x2, num=_nxpts)

        if yet:
            _netpts = int((y2-y1)/_xystep)
            _ymin = x2-y2
            _ymax = x1-y1
            _nypts = int((_ymax-_ymin)/_xystep)
            _etcrop = np.linspace(y1, y2, num=_netpts)
            _ycrop = np.linspace(_ymin, _ymax, num=_nypts)
        else:
            _nypts = int((y2-y1)/_xystep)
            _etmin = x1-y2
            _etmax = x2-y1
            _netpts = int((_etmax-_etmin)/_xystep)
            _etcrop = np.linspace(_etmin, _etmax, num=_netpts)
            _ycrop = np.linspace(y1, y2, num=_nypts)

        _xx, _yy = np.meshgrid(_xcrop, _ycrop)
        _exx, _et = np.meshgrid(_xcrop, _etcrop)
        _logger.info("Gridding data...")
        _zzcrop = griddata((self._x, self._y), self._z, (_xx, _yy), method=_method)
        _ezzcrop = griddata((self._x, self._x-self._y), self._z, (_exx, _et), method=_method)

        self.ene_in_crop = _xcrop
        self.ene_out_crop = _ycrop
        self.ene_et_crop = _etcrop
        self.rixs_map_crop = _zzcrop
        self.rixs_et_map_crop = _ezzcrop

    def grid_rixs_from_col(self):
        """Grid RIXS map from XYZ"""
        _lib = self.grid_lib or 'scipy'
        _method = self.grid_method or 'nearest'
        _xystep = self.ene_grid or 0.1
        self.ene_in, self.ene_out, self.rixs_map = gridxyz(self._x,
                                                           self._y,
                                                           self._z,
                                                           xystep=_xystep,
                                                           lib=_lib,
                                                           method=_method)
        self._et = self._x - self._y
        _, self.ene_et, self.rixs_et_map = gridxyz(self._x, self._et, self._z,
                                                   xystep=_xystep,
                                                   lib=_lib,
                                                   method=_method)

    def norm(self):
        """Simple map normalization to max-min"""
        self.rixs_map_norm = self.rixs_map/(np.nanmax(self.rixs_map)-np.nanmin(self.rixs_map))


if __name__ == '__main__':
    pass
