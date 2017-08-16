#!/usr/bin/env python

from __future__ import print_function
import time
import os
import sys
import site

modules = ['numpy', 'scipy', 'matplotlib', 'h5py', 'sqlalchemy',
           'wx', 'wxmplot', 'wxutils',
           'lmfit', 'epics', 
           'PIL', 'skimage', 'pandas', 'termcolor', 'colorama']

for modname in modules:
    try:
        mod = __import__(modname)
        try:
            version = mod.__version__
        except AttributeError:
            version = 'unknown version'
        except:
            version = 'error get version'
    except ImportError:
        version = 'not installed'
    except:
        version = 'error importing'

    print("%s: %s  (%s)" % (modname, version, mod.__file__))
