#!/usr/bin/env python

from __future__ import print_function
from distutils.core import setup

import os
import sys
import site
import glob

DEBUG = False
cmdline_args = sys.argv[1:]

required_modules = ('numpy', 'scipy')
recommended_modules = {'basic analysis': required_modules,
                       'graphical interface and plotting': ('wx', 'wxutils'),
                       'color-enhanced error messages': ('termcolor', ),
                       'plotting': ('matplotlib', 'wxmplot'),
                       'accessing x-ray databases': ('sqlalchemy', ),
                       'readng hdf5 files': ('h5py', ),
                       'using the EPICS control system': ('epics', ),
                       }

# files that may be in share_basedir (from earlier installs)
# and should be removedn
historical_cruft = ['plugins/wx/wxutils.py']

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
            if mod == 'wx':
                try:
                    import wxversion
                    wxversion.ensureMinimal('2.8')
                except:
                    pass
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

from lib import site_configdata, site_config, version


############
# read installation locations from lib/site_configdata.py
share_basedir = site_configdata.unix_installdir
user_basedir  = site_configdata.unix_userdir
# windows
if os.name == 'nt':
    share_basedir = site_configdata.win_installdir
    user_basedir = site_configdata.win_userdir

if os.environ.get('TRAVIS_CI_TEST', '0') == '1':
    share_basedir=os.path.expanduser('~/share/larch')


if DEBUG:
    print("##  Settings  (Debug mode) ## ")
    print(" share_basedir: ",  share_basedir)
    print(" user_basedir: ",  user_basedir)
    print(" sys.prefix: ",  sys.prefix)
    print(" sys.exec_prefix: ",  sys.exec_prefix)
    print(" site.USER_BASE: ",  site.USER_BASE)
    print(" site.USER_SITE: ",  site.USER_SITE)
    print(" cmdline_args: ",  cmdline_args)
    print("##   ")


# construct list of files to install besides the normal python modules
# this includes the larch executable files, and all the larch modules
# and plugins

data_files  = [('bin', glob.glob('bin/*'))]

mod_dir = os.path.join(share_basedir, 'modules')
modfiles = glob.glob('modules/*.lar') + glob.glob('modules/*.py')
data_files.append((mod_dir, modfiles))

#dlls
dll_maindir = os.path.join(share_basedir, 'dlls')
archs = []
if os.name == 'nt':
    archs.extend(['win32', 'win64'])
else:
    if sys.platform.lower().startswith('linux'):
        archs.extend(['linux32', 'linux64'])
    elif sys.platform.lower().startswith('darwin'):
        archs.append('darwin')

for dx in archs:
    dlldir = os.path.join(dll_maindir, dx)
    dllfiles = glob.glob('dlls/%s/*' % dx)
    data_files.append((dlldir, dllfiles))

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
      url          = 'http://xraypy.github.io/xraylarch/',
      download_url = 'http://xraypy.github.io/xraylarch/',
      requires = ('numpy', 'scipy', 'matplotlib'),
      license = 'BSD',
      description = 'Synchrotron X-ray data analysis in python',
      package_dir = {'larch': 'lib'},
      packages = ['larch', 'larch.utils', 'larch.wxlib',
                  'larch.fitting', 'larch.fitting.uncertainties'],
      data_files  = data_files)

site_config.make_larch_userdirs()

def remove_cruft(basedir, filelist):
    """remove files from base directory"""
    def remove_file(base, fname):
        fullname = os.path.join(base, fname)
        if os.path.exists(fullname):
            print(" Unlink ", fullname)
            try:
                os.unlink(fullname)
            except:
                pass
    for fname in filelist:
        remove_file(basedir, fname)
        if fname.endswith('.py'):
            remove_file(basedir, fname+'c')
            remove_file(basedir, fname+'o')


def fix_permissions(*dirnames):
    """
    set permissions on a list of directories to match
    thoseof the HOME directory
    """
    try:
        home = os.environ['HOME']
    except:
        return
    stat =  os.stat(home)
    def own(nam, mode=0o750):
        try:
            os.chown(nam, stat.st_uid, stat.st_gid)
            os.chmod(nam, mode)
        except(AttributeError, OSError):
            pass
    for dname in (dirnames):
        folder = os.path.join(home, '.%s' % dname)
        for top, dirs, files in os.walk(folder):
            own(top)
            for d in dirs:
                own(os.path.join(top, d))
            for d in files:
                own(os.path.join(top, d), mode=0o640)

fix_permissions('matplotlib', 'larch')
if cmdline_args[0] == 'install':
    remove_cruft(share_basedir, historical_cruft)

if deps_ok and not os.path.exists('.deps'):
    f = open('.deps', 'w')
    f.write('1\n')
    f.close()

if len(missing) > 0:
    msg = """
#==============================================================#
#=== Warning: Some recommended Python Packages are missing:
%s

Some functionality will not work until these are installed.
See INSTALL for further information.
#==============================================================#"""
    print(msg %  '\n'.join(missing))
