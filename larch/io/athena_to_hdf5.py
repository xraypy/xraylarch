#!/usr/bin/env python
"""
Convert an Athena Project file to HDF5
"""

import os
import h5py
import numpy as np
from larch import Group
from larch.io.athena_project import read_athena

from larch.utils.logging import getLogger
_logger = getLogger("athena_to_hdf5", level="DEBUG")


def athena_to_hdf5(filename, fileout=None, overwrite=False, **kws):
    """Read Athena project file (.prj) and write to HDF5 (.h5)

    Arguments:
        filename (string): name of Athena Project file
        fileout (None or string): name of the output file
        overwrite (boolean): force overwrite if fileout exists
        **kws: keyword arguments passed to :func:`larch.io.athena_project.read_athena`

    Returns:
        None
    """
    adict = read_athena(filename, **kws).__dict__

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
    _logger.debug("/")
    for gname, grp in adict["_athena_groups"].items():
        grp = grp.__dict__
        h5g = h5out.create_group(gname)
        _logger.debug(f"+- {gname}")
        for sgname, sgval in grp.items():
            if isinstance(sgval, np.ndarray):
                h5g.create_dataset(sgname, data=sgval)
                _logger.debug(f"|  - {sgname}")
            if isinstance(sgval, Group):
                pardict = sgval.__dict__
                _ = pardict.pop("__name__")
                if not sgname == "athena_params":
                    h5sg = h5g.create_group(sgname)
                    _logger.debug(f"|  +- {sgname}")
                for parname, parval in pardict.items():
                    if sgname == "athena_params":
                        continue
                    _pname = parname
                    _pval = parval
                    h5sg.create_dataset(_pname, data=_pval)
                    _logger.debug(f"|  |  - {_pname}")

    h5out.close()
    _logger.info(f"Athena project converted to {fileout}")

if __name__ == "__main__":
    pass
