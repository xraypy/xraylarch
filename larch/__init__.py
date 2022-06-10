#!/usr/bin/env python

"""
  Larch: a scientific data processing macro language based on python
"""
import os
import sys
import logging
import time
import warnings
warnings.simplefilter('ignore')

# note: may need to set CONDA env *before* loading numpy!
if os.name == 'nt':
    os.environ['CONDA_DLL_SEARCH_MODIFICATION_ENABLE'] = '1'

if (sys.version_info.major < 3 or sys.version_info.minor < 5):
    raise EnvironmentError('larch requires python 3.6 or higher')

import numpy
import matplotlib
import lmfit

logger = logging.getLogger()
logger.level = logging.ERROR + 1

# note: for HDF5 File / Filter Plugins to be useful, the
# hdf5plugin module needs to be imported before h5py
try:
    import hdf5plugin
except ImportError:
    pass

# we set the matplotlib backend before import lmfit / pyplot
#    import matplotlib.pyplot as plt
try:
    import wx
    with warnings.catch_warnings():
        warnings.filterwarnings('error')
        matplotlib.use("WXAgg")
except ImportError:
    pass


## be careful here: it is easy to have cicrular imports!

from .version import __date__, __version__, __release_version__
from .symboltable import Group, isgroup
from .larchlib import Make_CallArgs, parse_group_args, isNamedClass, Journal, Entry
from .fitting import Parameter, isParameter, param_value, ParameterGroup

# from . import builtins
from .inputText import InputText
from .interpreter import Interpreter
from . import larchlib
from . import utils
from . import site_config
from .site_config import show_site_config
# # from . import fitting, math, io


# try:
#     from . import apps
#     from . import shell
# except ImportError as e:
#     logger.warning(f"Larchs apps and shell are missing some dependencies: {e}")

logger.level = logging.INFO

# from . import apps import (run_gse_mapviewer, run_gse_dtcorrect, run_xas_viewer,
#                    run_xrfdisplay, run_xrfdisplay_epics, run_xrd1d_viewer,
#                    run_xrd2d_viewer, run_gse_dtcorrect, run_feff8l,
#                    run_larch_server, run_larch)
