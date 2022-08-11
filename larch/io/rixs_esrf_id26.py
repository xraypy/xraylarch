#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RIXS data reader for beamline ID26 @ ESRF
=========================================

RIXS stands for Resonant Inelastic X-ray Scattering

**NOTE**: The current implementation is for RIXS files collected at ID26 in
Spec format, that is, before 2019. Currently, ESRF/BLISS format is used at
ID26. Updating this function to the new format should be straightforward by
providing an example of data, but is not yet done/supported.

"""
import os
import time
import numpy as np
from larch.io.specfile_reader import DataSourceSpecH5, _str2rng, _mot2array
from silx.io.dictdump import dicttoh5
from larch.utils.logging import getLogger

_logger = getLogger("io_rixs_id26")
_logger.setLevel("INFO")


def _parse_header(fname):
    """Get parsed header

    Return
    ------
    header : dict
    """
    raise NotImplementedError


def get_rixs_id26(
    fname,
    scans=None,
    sample_name=None,
    mode="rixs",
    mot_axis2="Spec.Energy",
    counter_signal="zap_det_dtc",
    counter_mon="arr_I02sum",
    interp_ene_in=True,
    out_dir=None,
    save_rixs=False,
):
    """Build RIXS map as X,Y,Z 1D arrays

    Parameters
    ----------

    fname : str
        path to the (Spec) data file (TODO: implement BLISS/HDF5)

    scans : str or list of strings or list of ints, optional [None -> all scans in the file]
        list of scans to load (the string is parsed by larch.io.specfile_reader._str2rng)

    sample_name : str, optional ['UNKNOWN_SAMPLE']
        name of the sample measured

    mode : str, optional ['rixs']
        RIXS acqusition mode (affects 'mot_axis2')
            - 'rixs' -> incoming energy scans
            - 'rixs_et' -> emitted energy scans

    mot_axis2 : str ['Spec.Energy']
        name of the counter to use as second axis

    counter_signal : str ['zap_det_dtc']
        name of the counter to use as signal

    counter_mon : str ['arr_I02sum']
        name of the counter to use as incoming beam monitor

    interp_ene_in: bool
        perform interpolation ene_in to the energy step of ene_out [True]

    out_dir : str, optional
        path to save the data [None -> data_dir]

    save_rixs : bool
        if True -> save outdict to disk (in 'out_dir')

    Returns
    -------

    outdict : dict
        {
        '_x': array, energy in
        '_y': array, energy out
        '_z': array, signal
        'mode': str
        'scans': list, scans
        'writer_name': str,
        'writer_version': str,
        'writer_timestamp': str,
        'counter_signal': str, counter_signal,
        'counter_mon': str, counter_mon,
        'mon_axis2': str, mot_axis2,
        'sample_name': str, sample_name,
        'ene_unit': "eV",
        'rixs_header': None,
        'data_dir': str, data_dir,
        'out_dir': str, out_dir,
        'fname_ine': str, full path raw data
        'fname_out': str, full path
        }
    """
    _writer = "get_rixs_id26"
    _writer_version = "1.5.2"  #: used for reading back in RixsData.load_from_h5()
    _writer_timestamp = "{0:04d}-{1:02d}-{2:02d}_{3:02d}{4:02d}".format(
        *time.localtime()
    )
    if sample_name is None:
        sample_name = "SAMPLE_UNKNOWN"

    data_dir = os.path.join(os.sep, *fname.split(os.sep)[1:-1])
    _logger.debug(f"data_dir: {data_dir}")
    if out_dir is None:
        out_dir = data_dir
    ds = DataSourceSpecH5(fname)

    if isinstance(scans, str):
        scans = _str2rng(scans)
    assert isinstance(scans, list), "scans should be a list"

    mode = mode.lower()
    assert mode in ("rixs", "rixs_et"), "RIXS mode not valid"

    _counter = 0
    for scan in scans:
        try:
            ds.set_scan(scan)
            xscan, sig, lab, attrs = ds.get_curve(counter_signal, mon=counter_mon)
        except Exception:
            _logger.error(f"cannot load scan {scan}!")
            continue
        # keV -> eV
        escan = xscan * 1000
        estep = ds.get_motor_position(mot_axis2) * 1000
        if mode == "rixs":
            x = escan
            y = _mot2array(estep, escan)
        if mode == "rixs_et":
            x = _mot2array(estep, escan)
            y = escan
        if _counter == 0:
            xcol = x
            ycol = y
            zcol = sig
        else:
            xcol = np.append(xcol, x)
            ycol = np.append(ycol, y)
            zcol = np.append(zcol, sig)
        _counter += 1
        _logger.info(f"Loaded scan {scan}: {estep:.1f} eV")

    outdict = {
        "_x": xcol,
        "_y": ycol,
        "_z": zcol,
        "mode": mode,
        "scans": scans,
        "writer_name": _writer,
        "writer_version": _writer_version,
        "writer_timestamp": _writer_timestamp,
        "counter_signal": counter_signal,
        "counter_mon": counter_mon,
        "mon_axis2": mot_axis2,
        "sample_name": sample_name,
        "ene_unit": "eV",
        "rixs_header": None,
        "data_dir": data_dir,
        "out_dir": out_dir,
    }

    if save_rixs:
        fnstr = fname.split("/")[-1].split(".")[0]
        fnout = "{0}_rixs.h5".format(fnstr)
        fname_out = os.path.join(out_dir, fnout)
        dicttoh5(outdict, fname_out)
        outdict["fname_in"] = fname
        outdict["fname_out"] = fname_out
        _logger.info("RIXS saved to {0}".format(fnout))

    return outdict


if __name__ == "__main__":
    pass
