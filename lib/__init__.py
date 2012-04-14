#!/usr/bin/env python2.6

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
from .shell import shell
from .interpreter import Interpreter
from .inputText import InputText
from .utils import Closure, fixName
from .version import __date__, __version__
