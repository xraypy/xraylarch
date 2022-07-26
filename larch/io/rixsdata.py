#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RIXS data object
================
"""
import numpy as np
import copy
import time
from itertools import cycle
from scipy.interpolate import griddata
from silx.io.dictdump import dicttoh5, h5todict

from larch.math.gridxyz import gridxyz
from larch.xafs.xafsutils import guess_energy_units
from larch.utils.logging import getLogger

_logger = getLogger(__name__)  #: module logger


def _tostr(arr):
    """Numpy array to string"""
    try:
        return np.array_str(arr)
    except Exception:
        return arr


class CycleColors:
    """Utility for setting the line colors of the RIXS map cuts"""

    DEFAULT_PALETTE = (
        "#1F77B4",
        "#AEC7E8",
        "#FF7F0E",
        "#FFBB78",
        "#2CA02C",
        "#98DF8A",
        "#D62728",
        "#FF9896",
        "#9467BD",
        "#C5B0D5",
        "#8C564B",
        "#C49C94",
        "#E377C2",
        "#F7B6D2",
        "#7F7F7F",
        "#C7C7C7",
        "#BCBD22",
        "#DBDB8D",
        "#17BECF",
        "#9EDAE5",
    )

    def __init__(self) -> None:
        self.colors = cycle(self.DEFAULT_PALETTE)

    def get_color(self) -> None:
        return next(self.colors)


class RixsData(object):
    """RIXS plane object"""

    #: loaded from dictionary/HDF5 -> self.load_from_h5()
    sample_name = "Unknown"
    counter_all, counter_signal, counter_norm = None, None, None
    _x, _y, _z = None, None, None
    ene_in, ene_out, rixs_map = None, None, None
    ene_et, rixs_et_map = None, None
    ene_grid, ene_unit = None, None

    #: line cuts
    lcuts = []

    grid_method = "nearest"
    grid_lib = "scipy"

    datatype = 'rixs'

    _palette = CycleColors()
    _no_save = ("_logger", "_palette")

    def __init__(self, name=None, logger=None):
        """Constructor"""

        self.__name__ = "RixsData_{0}".format(hex(id(self)))
        self.name = name or self.__name__
        self.label = self.name
        self._logger = logger or _logger

    def set_energy_unit(self, unit=None):
        """set the energy unit to eV"""
        self.ene_unit = unit
        if self.ene_unit is None:
            self.ene_unit = guess_energy_units(self._x)
        if self.ene_unit == "keV":
            self._logger.info(f"Energy unit is {self.ene_unit} -> converting to eV")
            self._x *= 1000
            self._y *= 1000
            self.ene_grid = 0.1
            self.reset()
            self.ene_unit = "eV"
        assert (
            self.ene_unit == "eV"
        ), f"energy unit is {self.set_energy_unit} -> must be eV"

    def load_from_dict(self, rxdict):
        """Load RIXS data from a dictionary

        Parameters
        ----------
        rxdict : dict
            Minimal required structure
            {
             'writer_version': '1.5.0',
             'sample_name': str,
             '_x': 1D array,  #: energy in
             '_y': 1D array,  #: energy out
             '_z': 1D array,  #: signal
            }

        Return
        ------
        None, set attributes: self.*
        """
        self.__dict__.update(rxdict)
        self.set_energy_unit()
        self.grid_rixs_from_col()

    def load_from_h5(self, fname):
        """Load RIXS from HDF5 file"""
        rxdict = h5todict(fname)
        if not ("writer_version" in rxdict.keys()):
            self._logger.error("Key 'writer_version' not found")
            return
        if not ("1.5" in _tostr(rxdict["writer_version"])):
            self._logger.warning("Data format not understood")
            return
        rxdict["sample_name"] = _tostr(rxdict["sample_name"])
        self.load_from_dict(rxdict)
        self._logger.info("RIXS map loaded from file: {0}".format(fname))

    def load_from_ascii(self, fname, **kws):
        """load data from a 3 columns ASCII file assuming the format:

        e_in(eV), e_out(eV), signal

        """

        try:
            self.dat = np.loadtxt(fname)
            self._logger.info("Loaded {0}".format(fname))
        except Exception:
            self._logger.error("Cannot load from {0}".format(fname))
            return

        self._x = self.dat[:, 0]
        self._y = self.dat[:, 1]
        self._z = self.dat[:, 2]

        self.set_energy_unit()
        self.reset()

    def save_to_h5(self, fname, **dicttoh5_kws):
        """Dump dictionary representation to HDF5 file"""
        save_dict = copy.deepcopy(self.__dict__)
        for dkey in self._no_save:
            del save_dict[dkey]
        dicttoh5(save_dict, fname, **dicttoh5_kws)
        self._logger.info(f"{self.name} saved to {fname}")

    def crop(self, crop_area, yet=False):
        """Crop the plane in a given range

        Parameters
        ----------

        crop_area : tuple
            (x1, y1, x2, y2) : floats
            x1 < x2 (ene_in)
            y1 < y2 (if yet=False: ene_out, else: ene_et)

        yet: bool, optional [False]
            if True: y1, y2 are given in energy transfer

        """
        self._crop_area = crop_area
        x1, y1, x2, y2 = crop_area
        assert x1 < x2, "wrong crop area, x1 >= x2"
        assert y1 < y2, "wrong crop area, y1 >= y2"
        _xystep = self.ene_grid or 0.1
        _method = self.grid_method or "nearest"

        _nxpts = int((x2 - x1) / _xystep)
        _xcrop = np.linspace(x1, x2, num=_nxpts)

        if yet:
            _netpts = int((y2 - y1) / _xystep)
            _ymin = x2 - y2
            _ymax = x1 - y1
            _nypts = int((_ymax - _ymin) / _xystep)
            _etcrop = np.linspace(y1, y2, num=_netpts)
            _ycrop = np.linspace(_ymin, _ymax, num=_nypts)
        else:
            _nypts = int((y2 - y1) / _xystep)
            _etmin = x1 - y2
            _etmax = x2 - y1
            _netpts = int((_etmax - _etmin) / _xystep)
            _etcrop = np.linspace(_etmin, _etmax, num=_netpts)
            _ycrop = np.linspace(y1, y2, num=_nypts)

        _xx, _yy = np.meshgrid(_xcrop, _ycrop)
        _exx, _et = np.meshgrid(_xcrop, _etcrop)
        _logger.info("Gridding data...")
        _zzcrop = griddata((self._x, self._y), self._z, (_xx, _yy), method=_method)
        _ezzcrop = griddata(
            (self._x, self._x - self._y), self._z, (_exx, _et), method=_method
        )

        self.ene_in = _xcrop
        self.ene_out = _ycrop
        self.ene_et = _etcrop
        self.rixs_map = _zzcrop
        self.rixs_et_map = _ezzcrop
        self.label = f"{self.name} [{self._crop_area}]"

    def reset(self):
        """resets to initial data"""
        self.grid_rixs_from_col()
        self.lcuts = []
        self.label = self.name
        self._palette = None
        self._palette = CycleColors()

    def grid_rixs_from_col(self):
        """Grid RIXS map from XYZ columns"""
        _lib = self.grid_lib or "scipy"
        _method = self.grid_method or "nearest"
        _xystep = self.ene_grid or 0.1
        self.ene_in, self.ene_out, self.rixs_map = gridxyz(
            self._x, self._y, self._z, xystep=_xystep, lib=_lib, method=_method
        )
        self._et = self._x - self._y
        _, self.ene_et, self.rixs_et_map = gridxyz(
            self._x, self._et, self._z, xystep=_xystep, lib=_lib, method=_method
        )
        self.ene_grid = _xystep

    def cut(self, energy=None, mode="CEE", label=None):
        """cut the RIXS plane at a given energy

        Parameters
        ----------
        energy : float
            energy of the cut

        mode : str
            defines the way to cut the plane:
                - "CEE" (constant emission energy)
                - "CIE" (constant incident energy)
                - "CET" (constant energy transfer)

        label : str, optional [None]
            custom label, if None: label = 'mode@ecut'

        Return
        ------
            None -> adds (xc:array, yc:array, info:dict) to self.lcuts:list, where

            info = {label: str,     #: 'mode@encut'
                    mode: str,      #: as input
                    enecut: float,  #: energy cut given from the initial interpolation
                    }
        """
        assert energy is not None, "The energy of the cut must be given"

        mode = mode.upper()

        if mode == "CEE":
            x = self.ene_in
            iy = np.abs(self.ene_out - energy).argmin()
            enecut = self.ene_out[iy]
            y = self.rixs_map[iy, :]
        elif mode == "CIE":
            x = self.ene_out
            iy = np.abs(self.ene_in - energy).argmin()
            enecut = self.ene_in[iy]
            y = self.rixs_map[:, iy]
        elif mode == "CET":
            x = self.ene_in
            iy = np.abs(self.ene_et - energy).argmin()
            enecut = self.ene_et[iy]
            y = self.rixs_et_map[iy, :]

        if label is None:
            label = f"{mode}@{enecut:.1f}"

        self._logger.info(f"added RIXS cut: {label}")
        info = dict(
            label=label,
            mode=mode,
            enecut=enecut,
            color=self._palette.get_color(),
            timestamp="{0:04d}-{1:02d}-{2:02d}_{3:02d}{4:02d}".format(
                *time.localtime()
            ),
        )

        self.lcuts.append((x, y, info))

    def norm(self):
        """Simple map normalization to max-min"""
        self.rixs_map_norm = self.rixs_map / (
            np.nanmax(self.rixs_map) - np.nanmin(self.rixs_map)
        )


if __name__ == "__main__":
    pass
