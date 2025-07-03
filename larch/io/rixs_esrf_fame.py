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
from pathlib import Path
from typing import Union
from larch.io.specfile_reader import DataSourceSpecH5, _mot2array, _str2rng
from silx.io.dictdump import dicttoh5
from larch.utils.logging import getLogger

_logger = getLogger("io_rixs_bm16")
__author__ = "Mauro Rovezzi"
__version__ = "25.1.2"  #: this is the local version for this module only


def search_samples(
    datadir: Union[str, Path],
    ignore_names: list[str] = ["rack", "mount", "align", "bl_"],
) -> list[Path]:
    samples = []
    if isinstance(datadir, str):
        datadir = Path(datadir)
    search_dir = Path(datadir) / "RAW_DATA"
    if not search_dir.exists():
        errmsg = f"Cannot access: {search_dir}"
        _logger.error(errmsg)
        return samples
    fnames = sorted(search_dir.glob("*"), key=lambda x: x.stat().st_ctime)
    isamp = 0
    _logger.info("Samples:")
    for fname in fnames:
        samp = fname.name
        if ".h5" in samp.lower():
            continue
        if any(ignore_name in samp.lower() for ignore_name in ignore_names):
            continue
        _logger.info(f"- {isamp}: {samp}")
        samples.append(fname)
        isamp += 1
    return samples


def get_rixs_filenames(samplepath: Path) -> list[Path]:
    fnames = sorted(samplepath.glob("**/*RIXS*.h5", case_sensitive=False), key=lambda x: x.stat().st_ctime)
    _logger.info(f"{len(fnames)} RIXS planes:")
    for ifn, fname in enumerate(fnames):
        _logger.info(f"- {ifn}: {fname.name}")
    return fnames


def get_rixs_bm16(
    fname: Union[str, Path],
    scans: Union[list[int], str, bool, None] = None,
    sample_name: Union[str, None] = None,
    mode: str = "rixs",
    mot_axis2: str = "emi",
    counter_signal: str = "xpad_roi1",
    counter_mon: str = "p201_1_bkg_sub",
    out_dir: Union[str, Path, None] = None,
    save: bool = False,
) -> dict:
    """Build RIXS map as X,Y,Z 1D arrays

    Parameters
    ----------
    fname : str
        path string to the BLISS/HDF5 file
    scans : str or list of ints, optional [None -> all scans in the file]
        list of scans to load (the string is parsed by larch.io.specfile_reader._str2rng)
    sample_name : str, optional ['UNKNOWN_SAMPLE']
        name of the sample measured
    mode : str, optional ['rixs']
        RIXS acqusition mode (affects 'mot_axis2')
            - 'rixs' -> incoming energy scans
            - 'rixs_et' -> emitted energy scans
    mot_axis2 : str ['emi']
        name of the counter to use as second axis
    counter_signal : str ['xpad_roi1']
        name of the counter to use as signal
    counter_mon : str ['p201_1_bkg_sub']
        name of the counter to use as incoming beam monitor
    out_dir : str, optional
        path to save the data [None -> data_dir]
    save : bool
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
        'fname_in': str, full path raw data
        'fname_out': str, full path
        }
    """
    _writer = "get_rixs_bm16"
    _writer_version = "1.5.2"  #: used for reading back in RixsData.load_from_h5()
    _writer_timestamp = "{0:04d}-{1:02d}-{2:02d}_{3:02d}{4:02d}".format(
        *time.localtime()
    )
    if isinstance(fname, str):
        fname = Path(fname)
    data_dir = fname.parent
    _logger.debug(f"data_dir: {data_dir}")
    if out_dir is None:
        out_dir = data_dir
    ds = DataSourceSpecH5(str(fname))
    if sample_name is None:
        try:
            sample_name = ds.get_sample_name()
        except Exception:
            sample_name = "SAMPLE_UNKNOWN"

    mode = mode.lower()
    assert mode in ("rixs", "rixs_et"), "RIXS mode not valid"
    if mode == "rixs":
        scntype = "trigscan"
    else:
        scntype = "emiscan"
    if isinstance(scans, str):
        scans = _str2rng(scans)
    if scans is None:
        scans = [scn[0] for scn in ds.get_scans() if (".1" in scn[0] and scntype in scn[1])]
        _logger.debug(f"mode {mode} -> found {len(scans)} {scntype} to load")
    assert isinstance(scans, list), "scans should be a list"

    _counter = 0
    for scan in scans:
        try:
            ds.set_scan(scan)
            xscan, sig, lab, attrs = ds.get_curve(counter_signal, mon=counter_mon)
        except Exception as err:
            _logger.error(f"cannot load scan {scan}!")
            _logger.debug(f"--- [{type(err).__name__}] ---> {err}")
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
        _logger.debug(f"Loaded scan {scan}: {estep:.1f} eV")
    _logger.info(f"Loaded {_counter} scans")

    fnstr = fname.stem
    fnout = "{0}_rixs.h5".format(fnstr)
    fname_out = Path(out_dir, fnout)

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
        "data_dir": str(data_dir),
        "out_dir": str(out_dir),
        "fname_in": str(fname),
        "fname_out": str(fname_out),
    }

    if save:
        save_rixs(outdict)

    return outdict


def save_rixs(outdict, fname_out=None):
    if fname_out is None:
        fname_out = outdict["fname_out"]
    else:
        outdict["fname_out"] = fname_out
    dicttoh5(outdict, fname_out)
    _logger.info("RIXS saved to {0}".format(fname_out))


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


def get_rixs_bm16_spec(
    rixs_logfn,
    sample_name=None,
    out_dir=None,
    counter_signal="absF1",
    counter_norm=None,
    interp_ene_in=True,
    save=False,
):
    """Build RIXS map as X,Y,Z 1D arrays (version for Spec files - *DEPRECATED*)

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
    save : bool
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
        "_x": xcol * 1000,  # to eV
        "_y": ycol * 1000,  # to eV
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

    if save:
        fnstr = sfn.split("/")[-1].split(".")[0]
        fnout = "{0}_rixs.h5".format(fnstr)
        dicttoh5(outdict, os.path.join(out_dir, fnout))
        _logger.info("RIXS saved to {0}".format(fnout))

    return outdict


if __name__ == "__main__":
    pass
