#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RIXS data reader for beamline BM16 @ ESRF
=========================================

.. note: RIXS stands for Resonant Inelastic X-ray Scattering

.. note: BM16 is FAME-UHD, French CRG beamline

"""
import os
import time
import numpy as np
from larch.io.specfile_reader import DataSourceSpecH5, _mot2array
from silx.io.dictdump import dicttoh5
from larch.utils.logging import getLogger

_logger = getLogger("io_rixs_bm16")


def _parse_header(fname):
    """Get parsed header for the RIXS_###.log file
    Return
    ------
    header : dict
    """
    with open(fname) as f:
        lines = f.read().splitlines()
    header_lines = [line[1:] for line in lines if line[0] == "#"]
    header = {}
    for line in header_lines:
        ls = line.split(": ")
        try:
            k, v = ls[0], ls[1]
        except IndexError:
            pass
        for s in ("START", "END", "STEP"):
            if s in k:
                v = float(v)
        header[k] = v
    return header


def get_rixs_bm16(
    rixs_logfn,
    sample_name=None,
    out_dir=None,
    counter_signal="absF1",
    counter_norm=None,
    interp_ene_in=True,
    save_rixs=False,
):
    """Build RIXS map as X,Y,Z 1D arrays
    Parameters
    ----------
    rixs_logfn : str
        path to the RIXS_###.log file
    sample_name : str, optional ['UNKNOWN_SAMPLE']
    out_dir : str, optional
        path to save the data [None -> data_dir]
    counter_signal : str
        name of the data column to use as signal
    counter_norm : str
        name of the data column to use as normaliztion
    interp_ene_in: bool
        perform interpolation ene_in to the energy step of ene_out [True]
    save_rixs : bool
        if True -> save outdict to disk (in 'out_dir')
    Returns
    -------
    outdict : dict
        {
        '_x': array, energy in
        '_y': array, energy out
        '_z': array, signal
        'writer_name': str,
        'writer_version': str,
        'writer_timestamp': str,
        'filename_all' : list,
        'filename_root': str,
        'name_sample': str,
        'name_scan': str,
        'counter_all': str,
        'counter_signal': str,
        'counter_norm': str,
        'ene_grid': float,
        'ene_unit': str,
        }
    """
    _writer = "get_rixs_bm16"
    _writer_version = "1.5.1"  #: used for reading back in RixsData.load_from_h5()
    _writer_timestamp = "{0:04d}-{1:02d}-{2:02d}_{3:02d}{4:02d}".format(
        *time.localtime()
    )
    header = _parse_header(rixs_logfn)
    if sample_name is None:
        try:
            sample_name = header["SAMPLE_NAME"]
        except Exception:
            sample_name = "UNKNOWN_SAMPLE"
    sfn = header["DATAFILE"]
    scntype = header["RIXS_SCAN_TYPE"]
    data_dir = os.path.join(os.sep, *sfn.split("/")[1:-1])
    if out_dir is None:
        out_dir = data_dir
    ds = DataSourceSpecH5(sfn)

    logobj = np.genfromtxt(rixs_logfn, delimiter=",", comments="#")
    scans = logobj[:, 0]  # list of scan numers
    enes = logobj[:, 1]

    _counter = 0
    for scan, estep in zip(scans, enes):
        scan = int(scan)
        try:
            ds.set_scan(scan)
            escan, sig, lab, attrs = ds.get_curve(counter_signal)
        except Exception:
            _logger.error(f"cannot load scan {scan}!")
            continue
        if scntype == "rixs_et":
            x = _mot2array(estep, escan)
            y = escan
        else:
            x = escan
            y = _mot2array(estep, escan)
        if _counter == 0:
            xcol = x
            ycol = y
            zcol = sig
        else:
            xcol = np.append(xcol, x)
            ycol = np.append(ycol, y)
            zcol = np.append(zcol, sig)
        _counter += 1
        _logger.info(f"Loaded scan {scan}: {estep} eV")

    outdict = {
        "_x": xcol * 1000, #to eV
        "_y": ycol * 1000, #to eV
        "_z": zcol,
        "writer_name": _writer,
        "writer_version": _writer_version,
        "writer_timestamp": _writer_timestamp,
        "counter_signal": counter_signal,
        "counter_norm": counter_norm,
        "sample_name": sample_name,
        "ene_unit": "eV",
        "rixs_header": header,
        "data_dir": data_dir,
        "out_dir": out_dir,
    }

    if save_rixs:
        fnstr = sfn.split("/")[-1].split(".")[0]
        fnout = "{0}_rixs.h5".format(fnstr)
        dicttoh5(outdict, os.path.join(out_dir, fnout))
        _logger.info("RIXS saved to {0}".format(fnout))

    return outdict


if __name__ == "__main__":
    pass
