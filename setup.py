#!/usr/bin/env python

from distutils.core import setup, setup_keywords

deps = ('wx', 'epics', 'numpy', 'matplotlib')

setup(name = 'stepscan',
      version = '0.2',
      author = 'Matthew Newville',
      author_email = 'newville@cars.uchicago.edu',
      license = 'BSD',
      description = 'Epics Step Scanning library and applications',
      package_dir = {'epicsscan': 'lib'},
      packages = ['epicsscan', 'epicsscan.server', 'epicsscan.gui'],
      data_files  = [('bin', ['bin/stepscan.py'])])

errmsg = 'WARNING: epics.stepscan requires Python module "%s"'
for mod in deps:
    try:
        a = __import__(mod)
    except ImportError:
        print errmsg % mod
