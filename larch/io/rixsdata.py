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
_logger.setLevel("INFO")


def _tostr(arr):
    """Numpy array to string"""
    try:
        return np.array_str(arr)
    except Exception:
        return arr


def _restore_from_array(dictin):
    """restore str/float from a nested dictionary of numpy.ndarray (when using silx.io.dictdump.h5todict)

    Note: discussed here https://github.com/silx-kit/silx/issues/3633
    """
    for k, v in dictin.items():
        if isinstance(v, dict):
            _restore_from_array(v)
        else:
            if isinstance(v[()], np.str_):
                dictin[k] = np.array_str(v)
            if isinstance(v[()], (np.float64, np.float32)):
                dictin[k] = copy.deepcopy(v.item())


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

    def __init__(self, name=None, logger=None):
        """Constructor"""

        self.__name__ = "RixsData_{0}".format(hex(id(self)))
        self.name = name or self.__name__
        self.label = self.name

        self._logger = logger or _logger
        self._palette = CycleColors()
        self._no_save = ("_logger", "_palette")

        self.sample_name = "UnknownSample"
        self.counter_all, self.counter_signal, self.counter_norm = None, None, None
        self._x, self._y, self._z = None, None, None
        self.ene_in, self.ene_out, self.rixs_map = None, None, None
        self.ene_et, self.rixs_et_map = None, None
        self.ene_grid, self.ene_unit, self.grid_method = None, None, None
        self.line_cuts = {}
        self.datatype = "rixs"

    def set_energy_unit(self, unit=None):
        """set the energy unit to eV"""
        if unit is not None:
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

    def load_from_h5(self, filename):
        """Load RIXS from HDF5 file"""
        rxdict = h5todict(filename)
        _restore_from_array(rxdict)
        if not ("writer_version" in rxdict.keys()):
            self._logger.error("Key 'writer_version' not found")
            return
        if not ("1.5" in _tostr(rxdict["writer_version"])):
            self._logger.warning("Data format not understood")
            return
        self.load_from_dict(rxdict)
        self._logger.info("RIXS map loaded from file: {0}".format(filename))

    def load_from_ascii(self, filename, **kws):
        """load data from a 3 columns ASCII file assuming the format:

        e_in(eV), e_out(eV), signal

        """

        try:
            dat = np.loadtxt(filename)
            self.filename = filename
            self._logger.info("Loaded {0}".format(filename))
        except Exception:
            self._logger.error("Cannot load from {0}".format(filename))
            return

        self._x = dat[:, 0]
        self._y = dat[:, 1]
        self._z = dat[:, 2]

        self.set_energy_unit()
        self.reset()

    def save_to_h5(self, filename=None):
        """Dump dictionary representation to HDF5 file"""
        if filename is None:
            filename = f"{self.filename.split('.')[0]}.h5"
        save_dict = copy.deepcopy(self.__dict__)
        for dkey in self._no_save:
            try:
                del save_dict[dkey]
            except KeyError:
                continue
        dicttoh5(save_dict, filename, update_mode="replace")
        self._logger.info(f"{self.name} saved to {filename}")

    def crop(self, crop_area, et=None):
        """Crop the plane in a given range

        Parameters
        ----------

        crop_area : tuple
            (x1, y1, x2, y2) : floats
            x1 < x2 (ene_in)
            y1 < y2 (if yet=False: ene_out, else: ene_et)

        et: bool,
            if True: y1, y2 are given in energy transfer

        """
        self._crop_area = crop_area
        x1, y1, x2, y2 = crop_area
        assert x1 < x2, "wrong crop area, x1 >= x2"
        assert y1 < y2, "wrong crop area, y1 >= y2"

        if et is None:
            if y2 < np.max(self.ene_et):
                self._logger.debug("crop in energy transfer")
                et = True
            else:
                self._logger.debug("crop in emission energy")
                et = False

        _xystep = self.ene_grid or 0.1
        _method = self.grid_method or "linear"

        _nxpts = int((x2 - x1) / _xystep)
        _xcrop = np.linspace(x1, x2, num=_nxpts)

        if et:
            _etmin = y1
            _etmax = y2
            _ymin = x1 - _etmax
            _ymax = x2 - _etmin
            self._logger.debug(f"-> emission range: {_ymin:.2f}:{_ymax:.2f}")
        else:
            _ymin = y1
            _ymax = y2
            _etmin = x2 - _ymax
            _etmax = x1 - _ymin
            self._logger.debug(f"-> et range: {_etmin:.2f}:{_etmax:.2f}")

        _netpts = int((_etmax - _etmin) / _xystep)
        _nypts = int((_ymax - _ymin) / _xystep)
        _etcrop = np.linspace(_etmin, _etmax, num=_netpts)
        _ycrop = np.linspace(_ymin, _ymax, num=_nypts)


        _xx, _yy = np.meshgrid(_xcrop, _ycrop)
        _exx, _et = np.meshgrid(_xcrop, _etcrop)
        self._logger.info("Gridding data...")
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

    def reset(self, **grid_kws):
        """resets to initial data"""
        self._logger.info("resetting to initial data (grid RIXS plane and line cuts)")
        self.grid_rixs_from_col(**grid_kws)
        self.line_cuts = {}
        self.label = self.name
        self._palette = None
        self._palette = CycleColors()

    def grid_rixs_from_col(self, ene_grid=None, grid_method=None):
        """Grid RIXS map from XYZ columns"""
        if ene_grid is not None:
            self.ene_grid = ene_grid
        if grid_method is not None:
            self.grid_method = grid_method
        _xystep = self.ene_grid or 0.1
        _method = self.grid_method or "linear"
        self.ene_in, self.ene_out, self.rixs_map = gridxyz(
            self._x, self._y, self._z, xystep=_xystep, method=_method
        )
        self._et = self._x - self._y
        _, self.ene_et, self.rixs_et_map = gridxyz(
            self._x, self._et, self._z, xystep=_xystep, method=_method
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
            custom label, if None: label = 'mode_enecut'

        Return
        ------
            None -> adds dict(x:array, y:array, info:dict) to self.lcuts[cut_key]:dict, where

            info = {label: str,     #: 'mode_enecut'
                    mode: str,      #: as input
                    enecut: float,  #: energy cut given from the initial interpolation
                    datatype: str,  #: 'xas' or 'xes'
                    color: str,     #: color from a common palette
                    timestamp: str, #: time stamp
                    }
        """
        assert energy is not None, "The energy of the cut must be given"

        mode = mode.upper()

        if mode == "CEE":
            xc = self.ene_in
            iy = np.abs(self.ene_out - energy).argmin()
            enecut = self.ene_out[iy]
            yc = self.rixs_map[iy, :]
            datatype = "xas"
        elif mode == "CIE":
            xc = self.ene_out
            iy = np.abs(self.ene_in - energy).argmin()
            enecut = self.ene_in[iy]
            yc = self.rixs_map[:, iy]
            datatype = "xes"
        elif mode == "CET":
            xc = self.ene_in
            iy = np.abs(self.ene_et - energy).argmin()
            enecut = self.ene_et[iy]
            yc = self.rixs_et_map[iy, :]
            datatype = "xas"
        else:
            self._logger.error(f"wrong mode: {mode}")
            return

        if label is None:
            label = f"{mode}_{enecut:.1f}"

        info = dict(
            label=label,
            mode=mode,
            enecut=enecut,
            datatype=datatype,
            color=self._palette.get_color(),
            timestamp="{0:04d}-{1:02d}-{2:02d}_{3:02d}{4:02d}".format(
                *time.localtime()
            ),
        )

        cut_key = f"{mode}_{enecut*10:.0f}"
        self.line_cuts[cut_key] = dict(x=xc, y=yc, info=info)
        self._logger.info(f"added RIXS {mode} cut: '{label}'")

    def norm(self):
        """Simple map normalization to max-min"""
        self.rixs_map = self.rixs_map / (
            np.nanmax(self.rixs_map) - np.nanmin(self.rixs_map)
        )
        self._logger.info("rixs map normalized to max-min")


if __name__ == "__main__":
    pass
