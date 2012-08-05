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

from .symboltable import Group, SymbolTable
from .fitting import Minimizer, Parameter, isParameter, param_value
from .shell import shell
from .larchlib import plugin_path
from .interpreter import Interpreter
from .inputText import InputText
from .utils import Closure, fixName
from .version import __date__, __version__
