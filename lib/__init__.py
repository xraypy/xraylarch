#!/usr/bin/env python

"""
  Larch: a scientific data processing macro language based on python
"""

#
import sys
## require that numpy be available right away!!
import numpy

major, minor = sys.version_info[0], sys.version_info[1]
if major < 2 or (major == 2 and minor < 6):
    raise EnvironmentError('requires python 2.6 or higher')

from .larchlib import (plugin_path, use_plugin_path, enable_plugins,
                       isNamedClass, LarchPluginException,
                       Make_CallArgs, ValidateLarchPlugin,
                       parse_group_args)
from .site_config import show_site_config
from .symboltable import Group, SymbolTable, isgroup
from .fitting import Minimizer, Parameter, isParameter, param_value
from .shell import shell
from .interpreter import Interpreter
from .inputText import InputText
from .utils import Closure, fixName, nativepath, get_homedir
from .version import __date__, __version__, make_banner

enable_plugins()
