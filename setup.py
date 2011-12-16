#!/usr/bin/env python

from distutils.core import setup, setup_keywords

import os
import glob
from lib import site_configdata

share_basedir = site_configdata.unix_installdir
if os.name == 'nt':
    share_basedir = site_configdata.win_installdir

data_files  = [('bin', ['larch', 'larch_nographics', 'larch_gui'])]


mod_dir = os.path.join(share_basedir, 'modules')
modfiles = glob.glob('modules/*.lar') + glob.glob('modules/*.py')

data_files.append((mod_dir, modfiles))

plugin_dir = os.path.join(share_basedir, 'plugins')
pluginfiles = []
pluginpaths = []
for fname in glob.glob('plugins/*'):
    if os.path.isdir(fname):
        pluginpaths.append(fname)
    else:
        pluginfiles.append(fname)

data_files.append((plugin_dir, pluginfiles))

for pdir in pluginpaths:
    pfiles = []
    for fname in glob.glob('%s/*.py' % pdir):
        if os.path.isdir(fname):
            print "SUBDIR  !! Need to Walk!"
        else:
            pfiles.append(fname)

    data_files.append((os.path.join(share_basedir, pdir), pfiles))


setup(name = 'larch',
      version = '0.9.5',
      author = 'Matthew Newville',
      author_email = 'newville@cars.uchicago.edu',
      license = 'Python',
      description = 'A data processing language for python',
      package_dir = {'larch': 'lib'},
      packages = ['larch', 'larch.wx'],
      data_files  = data_files)
