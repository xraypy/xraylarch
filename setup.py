#!/usr/bin/env python

from distutils.core import setup, setup_keywords

deps = ('wx', 'epics', 'numpy', 'matplotlib')

setup(name = 'epicsapp_stepscan',
      version = '0.2',
      author = 'Matthew Newville',
      author_email = 'newville@cars.uchicago.edu',
      license = 'BSD',
      description = 'Epics Step Scanner',
      package_dir = {'epicsapps.stepscan': 'lib',
                     'epicsapps': 'base'},
      packages = ['epicsapps', 'epicsapps.stepscan'],
      data_files  = [('bin', ['pyepics_stepscan.py'])])


errmsg = 'WARNING: pyepics_stepscan requires Python module "%s"'
for mod in deps:
    try:
        a = __import__(mod)
    except ImportError:
        print errmsg % mod
