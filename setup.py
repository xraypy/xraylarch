#!/usr/bin/env python

from distutils.core import setup
import os, sys
import glob

from lib import site_configdata, site_config, version

required_modules = ('numpy', 'scipy', 'docutils', 'wx', 'matplotlib', 'wxmplot')

recommended_modules = {'basic processing analysis': ('numpy', 'scipy', 'docutils'),
                       'graphics and plotting': ('wx',),
                       'plotting': ('matplotlib', 'wxmplot'),
                       'access to x-ray databases': ('sqlalchemy', ),
                       'read hdf5 files': ('h5py', ),
                       'propogate uncertainties': ('uncertainties', ),
                       'using the EPICS control system': ('epics',)
                    }

modules_imported = {}
missing = []
deps_ok = False
if os.path.exists('.deps'):
    try:
        f = open('.deps', 'r').readlines()
        deps_ok = int(f[0].strip()) == 1
    except:
        pass

if not deps_ok:
    print( 'Checking dependencies....')
    for desc, mods in recommended_modules.items():
        for mod in mods:
            if mod not in modules_imported:
                modules_imported[mod] = False
            try:
                x = __import__(mod)
                modules_imported[mod] = True
            except ImportError:
                missing.append('     %s:  needed for %s' % (mod, desc))
    missing_reqs = []
    for mod in modules_imported:
        if mod in required_modules and not modules_imported[mod]:
            missing_reqs.append(mod)
            
    if len(missing_reqs) > 0:
        print('== Cannot Install Larch: Required Modules are Missing ==')
        isword = 'is'
        if len(missing_reqs) > 1: isword = 'are'
        print(' %s %s REQUIRED' % (' and '.join(missing_reqs), isword) )
        print(' ')
        print(' Please read INSTALL for further information.')
        print(' ')

        sys.exit()
    deps_ok = len(missing) == 0
print '=============================='
############
# read installation locations from lib/site_configdata.py
share_basedir = site_configdata.unix_installdir
user_basedir  = site_configdata.unix_userdir
# windows
if os.name == 'nt':
    share_basedir = site_configdata.win_installdir
    user_basedir = site_configdata.win_userdir

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
            print('Warning -- not walking subdirectories for Plugins!!')
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
      packages = ['larch', 'larch.utils', 'larch.fitting', 'larch.wxlib'],
      data_files  = data_files)

site_config.make_larch_userdirs()

if deps_ok and not os.path.exists('.deps'):
    f = open('.deps', 'w')
    f.write('1\n')
    f.close()

if len(missing) > 0:
    print( '=' * 65)
    print( '== Warning: Some recommended Python Packages are missing ==')
    print( '\n'.join(missing))
    print( ' ')
    print( 'Some functionality will not work until these are installed.')
    print( 'Please read INSTALL for further information.')
    print( '=' * 65)


