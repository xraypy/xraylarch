#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RIXS data reader for beamline 13-ID-E @ APS
===========================================

.. note: RIXS stands for Resonant Inelastic X-ray Scattering

.. note: 13-ID-E is GSECARS-CAT

"""
import os
import time
import glob
import numpy as np

from silx.io.dictdump import dicttoh5

from larch.utils.logging import getLogger
_logger = getLogger('io_rixs_gsecars')


def _parse_header(fname):
    """Get parsed header

    Return
    ------
    header : dict
        {
        'columns': list of strings,
        'Analyzer.Energy': float,
        }
    """
    with open(fname) as f:
        lines = f.read().splitlines()
    header_lines = [line[2:] for line in lines if line[0] == '#']
    header = {}
    for line in header_lines:
        if 'Analyzer.Energy' in line:
            ene_line = line.split(' ')
            break
        else:
            ene_line = ['Analyzer.Energy:', '0', '', '||', '', '13XRM:ANA:Energy.VAL']  #: expected line
    header['Analyzer.energy'] = float(ene_line[1])
    header['columns'] = header_lines[-1].split('\t')
    return header


def get_rixs_13ide(sample_name, scan_name, rixs_no='001', data_dir='.',
                   out_dir=None, counter_signal='ROI1', counter_norm=None, interp_ene_in=True, save_rixs=False):
    """Build RIXS map as X,Y,Z 1D arrays

    Parameters
    ----------
    sample_name : str
    scan_name : str
    rixs_no : str, optional
        length 3 string, ['001']
    data_dir : str, optional
        path to the data ['.']
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
    _writer = 'get_rixs_13ide'
    _writer_version = "1.5.1"  #: used for reading back in RixsData.load_from_h5()
    _writer_timestamp = '{0:04d}-{1:02d}-{2:02d}_{3:02d}{4:02d}'.format(*time.localtime())

    if out_dir is None:
        out_dir = data_dir
    fnstr = "{0}_{1}".format(scan_name, sample_name)
    grepstr = "{0}*.{1}".format(fnstr, rixs_no)
    fnames = glob.glob(os.path.join(data_dir, grepstr))
    enes = np.sort(np.array([_parse_header(fname)['Analyzer.energy'] for fname in fnames]))
    estep = round(np.average(enes[1:]-enes[:-1]), 2)

    fname0 = fnames[0]
    header = _parse_header(fname0)
    cols = header['columns']
    ix = cols.index('Energy') or 0
    iz = cols.index(counter_signal)
    i0 = cols.index(counter_norm)

    if interp_ene_in:
        dat = np.loadtxt(fname0)
        x0 = dat[:, ix]
        xnew = np.arange(x0.min(), x0.max()+estep, estep)

    for ifn, fname in enumerate(fnames):
        dat = np.loadtxt(fname)
        x = dat[:, ix]
        y = np.ones_like(x) * enes[ifn]
        if counter_norm is not None:
            z = dat[:, iz] / dat[:, i0]
        else:
            z = dat[:, iz]
        if interp_ene_in:
            y = np.ones_like(xnew) * enes[ifn]
            z = np.interp(xnew, x, z)
            x = xnew
        if ifn == 0:
            _xcol = x
            _ycol = y
            _zcol = z
        else:
            _xcol = np.append(x, _xcol)
            _ycol = np.append(y, _ycol)
            _zcol = np.append(z, _zcol)
        _logger.info("Loaded scan {0}: {1} eV".format(ifn+1, enes[ifn]))

    outdict = {
        '_x': _xcol,
        '_y': _ycol,
        '_z': _zcol,
        'writer_name': _writer,
        'writer_version': _writer_version,
        'writer_timestamp': _writer_timestamp,
        'filename_root': fnstr,
        'filename_all': fnames,
        'counter_all': cols,
        'counter_signal': counter_signal,
        'counter_norm': counter_norm,
        'sample_name': sample_name,
        'scan_name': scan_name,
        'ene_grid': estep,
        'ene_unit': 'eV',
        }

    if save_rixs:
        fnout = "{0}_rixs.h5".format(fnstr)
        dicttoh5(outdict, os.path.join(out_dir, fnout))
        _logger.info("RIXS saved to {0}".format(fnout))

    return outdict


if __name__ == '__main__':
    pass
