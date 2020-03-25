#!/usr/bin/env python
"""
Convert an Athena Project file to HDF5
"""

import os
import h5py
from silx.io.dictdump import dicttoh5
from larch.io.athena_project import AthenaProject
from larch.utils.logging import getLogger

_logger = getLogger("athena_to_hdf5", level="INFO")


def athena_to_hdf5(
    filename,
    fileout=None,
    overwrite=False,
    match=None,
    do_preedge=True,
    do_bkg=True,
    do_fft=True,
    use_hashkey=False,
    _larch=None,
):
    """Read Athena project file (.prj) and write to HDF5 (.h5)

    Arguments:
        filename (string): name of Athena Project file
        fileout (None or string): name of the output file [None -> filename_root.h5]
        overwrite (boolean): force overwrite if fileout exists [False]
        match (string): pattern to use to limit imported groups (see Note 1)
        do_preedge (bool): whether to do pre-edge subtraction [True]
        do_bkg (bool): whether to do XAFS background subtraction [True]
        do_fft (bool): whether to do XAFS Fast Fourier transform [True]
        use_hashkey (bool): whether to use Athena's hash key as the
                       group name instead of the Athena label [False]

    Returns:
        None, writes HDF5 file.

    Notes:
        1. There is currently a bug in h5py, track_order is ignored for the root group:
            https://github.com/h5py/h5py/issues/1471

    """
    aprj = AthenaProject(_larch=_larch)
    aprj.read(
        filename,
        match=match,
        do_preedge=do_preedge,
        do_bkg=do_bkg,
        do_fft=do_fft,
        use_hashkey=use_hashkey,
    )
    adict = aprj.as_dict()
    if fileout is None:
        froot = filename.split(".")[0]
        fileout = f"{froot}.h5"
    if os.path.isfile(fileout) and os.access(fileout, os.R_OK):
        _logger.info(f"{fileout} exists")
        _fileExists = True
        if overwrite is False:
            _logger.info(f"overwrite is {overwrite} -> nothing to do!")
            return
    else:
        _fileExists = False
    if overwrite and _fileExists:
        os.remove(fileout)
    h5out = h5py.File(fileout, mode="a", track_order=True)
    create_ds_args = {"track_order": True}
    dicttoh5(adict, h5out, create_dataset_args=create_ds_args)
    h5out.close()
    _logger.info(f"Athena project converted to {fileout}")


if __name__ == "__main__":
    # some tests while devel
    _curdir = os.path.dirname(os.path.realpath(__file__))
    _exdir = os.path.join(os.path.dirname(os.path.dirname(_curdir)), "examples", "pca")
    fnroot = "cyanobacteria"
    atpfile = os.path.join(_exdir, f"{fnroot}.prj")
    if 0:
        from larch import Interpreter

        aprj = AthenaProject(_larch=Interpreter())
        aprj.read(atpfile, do_bkg=False)  # there is currently a bug in do_bkg!
        adict = aprj.as_dict()
    if 0:
        athena_to_hdf5(atpfile, fileout=f"{fnroot}.h5", overwrite=True)
    pass
