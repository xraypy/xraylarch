#!/usr/bin/env python

"""
  Larch: a scientific data processing macro language based on python
"""

#
import sys
import numpy
import matplotlib
try:
    matplotlib.use('WXAgg')
except:
    pass

major, minor = sys.version_info[0], sys.version_info[1]
if not ((major == 2 and minor == 7) or
        (major == 3 and minor > 4)):
    raise EnvironmentError('larch requires python 2.7 or 3.5 or higher')


from .larchlib import (plugin_path, use_plugin_path, enable_plugins,
                       isNamedClass, LarchPluginException,
                       Make_CallArgs, ValidateLarchPlugin,
                       parse_group_args)
from .site_config import show_site_config
from .symboltable import Group, SymbolTable, isgroup
from .shell import shell
from .inputText import InputText
from .utils import fixName, nativepath, get_homedir
from .version import __date__, __version__, make_banner
from .interpreter import Interpreter
from .fitting import Minimizer, Parameter, isParameter, param_value, param_group, minimize

enable_plugins()
