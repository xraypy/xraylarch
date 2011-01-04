#!/usr/bin/env python


import distutils
from distutils.core import setup, Extension

import glob

modfiles = glob.glob('modules/*.lar') + glob.glob('modules/*.py')

setup(name = 'larch',
      version = '0.9.5',
      author = 'Matthew Newville',
      author_email = 'newville@cars.uchicago.edu',
      license = 'Python',
      description = 'A data processing language for python',
      package_dir = {'larch': 'lib'},
      packages = ['larch','larch.plugins',
                  'larch.wx', 'larch.mplot'],
      data_files  = [('bin',['larch', 'wxlarch']),
                     ('share/larch/modules', modfiles)],)
