#!/usr/bin/env python

"""
  Larch: a scientific data processing macro language based on python
"""
import os
import sys
import logging
import warnings
warnings.simplefilter('ignore')

logger = logging.getLogger()
logger.level = logging.WARNING
# note: may need to set CONDA env *before* loading numpy!
if os.name == 'nt':
    os.environ['CONDA_DLL_SEARCH_MODIFICATION_ENABLE'] = '1'

if (sys.version_info.major < 3 or sys.version_info.minor < 9):
    raise EnvironmentError('larch requires python 3.9 or higher')

# note: for HDF5 File / Filter Plugins to be useful, the
# hdf5plugin module needs to be imported before h5py
try:
   import hdf5plugin
except ImportError:
   pass

## limited imports
from .version import __date__, __version__, __release_version__
from .symboltable import Group, isgroup
from .larchlib import Make_CallArgs, parse_group_args, isNamedClass, Journal, Entry
from .interpreter import Interpreter
from . import utils
from . import site_config
