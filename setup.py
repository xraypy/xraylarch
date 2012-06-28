#!/usr/bin/env python

from distutils.core import setup, setup_keywords
import os, sys
import glob

from lib import site_configdata, site_config, version

required_modules = ('numpy', 'scipy')

recommended_modules = {'basic processing analysis': ('numpy', 'scipy'),
                       'graphics and plotting': ('wx',),
                       'plotting': ('matplotlib', 'wxmplot'),
                       'access to x-ray databases': ('sqlalchemy', ),
                       'read hdf5 files': ('h5py', ),
                       # 'using the EPICS control system': ('epics',)
                    }

failed = False
missing = []
print 'Checking dependencies....'
for desc, mods in recommended_modules.items():
    for mod in mods:
        try:
            x = __import__(mod)
        except ImportError:
            failed = failed or mod in required_modules
            missing.append('     %s:  needed for %s' % (mod, desc))

if failed:
    print '== Cannot Install Larch: =='
    print 'Missing dependencies: %s are REQUIRED' % (' and '.join(required_modules))
    print 'Please read INSTALL for further information.'
    sys.exit()


# read installation locations from lib/site_configdata.py
share_basedir = site_configdata.unix_installdir
user_basedir  = site_configdata.unix_userdir

# construct list of files to install besides the normal python modules
# this includes the larch executable files, and all the larch modules
# and plugins
data_files  = [('bin', ['larch', 'larch_gui'])]

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
    filelist = []
    for ext in ('py', 'txt', 'db', 'dat', 'rst', 'lar',
                'dll', 'dylib', 'so'):
        filelist.extend(glob.glob('%s/*.%s' % (pdir, ext)))
    for fname in filelist:
        if os.path.isdir(fname):
            print 'Warning -- not walking subdirectories for Plugins!!'
        else:
            pfiles.append(fname)
    data_files.append((os.path.join(share_basedir, pdir), pfiles))

# now we have all the data files, so we can run setup
setup(name = 'larch',
      version = version.__version__,
      author = 'Matthew Newville',
      author_email = 'newville@cars.uchicago.edu',
      license = 'Python',
      description = 'A scientific data processing language in python',
      package_dir = {'larch': 'lib'},
      packages = ['larch', 'larch.utils', 'larch.wxlib'],
      data_files  = data_files)

site_config.make_larch_userdirs()

if len(missing) > 0:
    print '=' * 65
    print ':Warning: Some recommended Python Packages are missing:'
    print '\n'.join(missing)
    print ' '
    print 'Some functionality will not work until these are installed.'
    print 'Please read INSTALL for further information.'
    print '=' * 65


