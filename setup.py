#!/usr/bin/env python

import distutils
from distutils.core import setup, Extension

import os
import glob
from lib import site_configdata

share_basedir = site_configdata.unix_installdir
if os.name == 'nt':
    share_basedir = site_configdata.win_installdir

mod_dir = os.path.join(share_basedir, 'modules')


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
      data_files  = [('bin',['larch', 'larch_wx', 'larch_gui']),
                     (mod_dir, modfiles)],)
