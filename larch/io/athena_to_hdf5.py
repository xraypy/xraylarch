#!/usr/bin/env python
"""
Convert an Athena Project file to HDF5
"""

import os
import h5py
import numpy as np
from silx.io.dictdump import dicttoh5
from larch import Group
from larch.io.athena_project import read_athena, AthenaProject

from larch.utils.logging import getLogger

_logger = getLogger("athena_to_hdf5", level="DEBUG")


def athena_to_hdf5(filename, fileout=None, overwrite=False, **kws):
    """Read Athena project file (.prj) and write to HDF5 (.h5)

    Arguments:
        filename (string): name of Athena Project file
        fileout (None or string): name of the output file [None -> filename_root.h5]
        overwrite (boolean): force overwrite if fileout exists [False]
        **kws: keyword arguments (see :func:`larch.io.athena_project.read_athena`)

    Notes:
        There is currently a bug in h5py, track_order is ignored for the root group:

        https://github.com/h5py/h5py/issues/1471

    Returns:
        None
    """
    match = kws.get("match", None)
    do_preedge = kws.get("do_preedge", None)
    do_bkg = kws.get("do_bkg", True)
    do_fft = kws.get("do_fft", True)
    use_hashkey = kws.get("use_hashkey", False)
    _larch = kws.get("_larch", None)

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
    #    _logger.debug("/")
    #    for gname, grp in adict["_athena_groups"].items():
    #        grp = grp.__dict__
    #        h5g = h5out.create_group(gname)
    #        _logger.debug(f"+- {gname}")
    #        for sgname, sgval in grp.items():
    #            if isinstance(sgval, np.ndarray):
    #                h5g.create_dataset(sgname, data=sgval)
    #                _logger.debug(f"|  - {sgname}")
    #            if isinstance(sgval, Group):
    #                pardict = sgval.__dict__
    #                _ = pardict.pop("__name__")
    #                if not sgname == "athena_params":
    #                    h5sg = h5g.create_group(sgname)
    #                    _logger.debug(f"|  +- {sgname}")
    #                for parname, parval in pardict.items():
    #                    if sgname == "athena_params":
    #                        continue
    #                    _pname = parname
    #                    _pval = parval
    #                    h5sg.create_dataset(_pname, data=_pval)
    #                    _logger.debug(f"|  |  - {_pname}")

    create_ds_args = {
        "track_order": True,
        "compression": "gzip",
        "shuffle": True,
        "fletcher32": True,
    }
    dicttoh5(adict, h5out, create_dataset_args=create_ds_args)
    h5out.close()
    _logger.info(f"Athena project converted to {fileout}")


if __name__ == "__main__":
    # some tests while devel
    _curdir = os.path.dirname(os.path.realpath(__file__))
    _exdir = os.path.join(os.path.dirname(os.path.dirname(_curdir)), "examples", "pca")
    fnroot = "cyanobacteria"
    atpfile = os.path.join(_exdir, f"{fnroot}.prj")
    if 1:
        from larch import Interpreter

        aprj = AthenaProject(_larch=Interpreter())
        aprj.read(atpfile, do_bkg=False)  # there is currently a bug in do_bkg!
        adict = aprj.as_dict()
    if 0:
        athena_to_hdf5(atpfile, fileout=f"{fnroot}.h5", overwrite=True)
    pass
