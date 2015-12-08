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
                       isNamedClass, LarchPluginException)
from .site_config import show_site_config
from .symboltable import Group, SymbolTable, isgroup
from .fitting import Minimizer, Parameter, isParameter, param_value
from .shell import shell
from .interpreter import Interpreter
from .inputText import InputText
from .utils import Closure, fixName, nativepath, get_homedir
from .version import __date__, __version__, make_banner

def ValidateLarchPlugin(fcn):
    """function decorator to ensure that _larch is included in keywords,
    and that it is a valid Interpeter"""
    errmsg = "plugin function '%s' needs a valid '_larch' argument"

    def wrapper(*args, **keywords):
        "ValidateLarchPlugin"
        if ('_larch' not in keywords or
            ('Interpreter' not in keywords['_larch'].__class__.__name__)):
            raise LarchPluginException(errmsg % fcn.__name__)
        return fcn(*args, **keywords)
    wrapper.__doc__ = fcn.__doc__
    wrapper.__name__ = fcn.__name__
    wrapper._larchfunc_ = fcn
    wrapper.__filename__ = fcn.__code__.co_filename
    wrapper.__dict__.update(fcn.__dict__)
    return wrapper

enable_plugins()
