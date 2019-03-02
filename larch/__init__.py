#!/usr/bin/env python

"""
  Larch: a scientific data processing macro language based on python
"""
import os
import sys
import numpy
import warnings
warnings.simplefilter('ignore')

if (sys.version_info.major < 3 or sys.version_info.minor < 5):
    raise EnvironmentError('larch requires python 3.5 or higher')

# note: for HDF5 File / Filter Plugins to be useful, the
# hdf5plugin module needs to be imported before h5py
try:
    import hdf5plugin
except ImportError:
    pass

# note: for lmfit 0.9.12 and earlier or any other import that does
#    import matplotlib.pyplot as plt
# we have to set the matplotlib backend before import lmfit / pyplot
import matplotlib
import warnings
try:
    import wx
except ImportError:
    pass

with warnings.catch_warnings():
    warnings.filterwarnings('error')
    try:
        matplotlib.use("WXAgg")
    except:
        pass

from .version import __date__, __version__, make_banner
from .site_config import show_site_config
from .symboltable import Group, SymbolTable, isgroup
from .larchlib import (plugin_path, use_plugin_path, enable_plugins,
                       isNamedClass, LarchPluginException, Make_CallArgs,
                       ValidateLarchPlugin, parse_group_args)

from .shell import shell
from .inputText import InputText
from .utils import fixName, nativepath, get_homedir
from .interpreter import Interpreter

from .fitting import (Minimizer, Parameter, isParameter, param_value,
                      param_group, minimize)

from . import math
from . import apps
from .apps import (run_gse_mapviewer, run_gse_dtcorrect, run_xas_viewer,
                   run_xrfdisplay, run_xrfdisplay_epics, run_xrd1d_viewer,
                   run_xrd2d_viewer, run_gse_dtcorrect, run_feff8l,
                   run_larch_server, run_larch)

enable_plugins()
