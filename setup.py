#!/usr/bin/env python

from __future__ import print_function
from distutils.core import setup
# from setuptools import setup

import time
import os
import sys
import site
import shutil
from glob import glob

DEBUG = False
cmdline_args = sys.argv[1:]

required_modules = ['numpy', 'scipy', 'lmfit', 'h5py', 'sqlalchemy', 'six', 'PIL']
graphics_modules = ['matplotlib', 'wx', 'wxmplot', 'wxutils', 'yaml']
xrd_modules = ['fabio','pyFAI','xrayutilities','CifFile', 'requests']

recommended_modules = {'basic analysis': required_modules,
                       'graphics and plotting': graphics_modules,
                       'xrd modules' : xrd_modules,
                       'color-enhanced error messages': ('termcolor', ),
                       'using the EPICS control system': ('epics', ),
                       'testing tools': ('nose', ),
                       }

# files that may be left from earlier installs) and should be removed
historical_cruft = []
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
                    wxversion.ensureMinimal('2.9')
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

##
## For Travis-CI, need to write a local site config file
##
if os.environ.get('TRAVIS_CI_TEST', '0') == '1':
    time.sleep(0.2)

from lib import version
# system-wide larchdir
larchdir = os.path.join(sys.exec_prefix, 'share', 'larch')

if DEBUG:
    print("##  Settings  (Debug mode) ## ")
    print(" larchdir: ",  larchdir)
    print(" sys.prefix: ",  sys.prefix)
    print(" sys.exec_prefix: ",  sys.exec_prefix)
    print(" cmdline_args: ",  cmdline_args)
    print("##   ")


# construct list of files to install besides the normal python modules
# this includes the larch executable files, and all the larch modules
# and plugins

larchico_dir = os.path.join(larchdir, 'icons')
larchmod_dir = os.path.join(larchdir, 'modules')

sysbin_dir = 'Scripts'
scripts    =  glob('bin/*')

mac_apps = []
_scripts = []
for s in scripts:
    if s.endswith('.app'):
        mac_apps.append(s)
    else:
        _scripts.append(s)
scripts = _scripts

if os.name != 'nt':
    _scripts = []
    sysbin_dir = 'bin'
    for s in scripts:
        if not s.endswith('.bat'):
            _scripts.append(s)
    scripts = _scripts

data_files = [(sysbin_dir,   scripts),
              (larchico_dir, glob('icons/*.ic*')),
              (larchmod_dir, glob('modules/*.lar') + glob('modules/*.py'))]

#dlls
dll_maindir = os.path.join(larchdir, 'dlls')
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
    dllfiles = glob('dlls/%s/*' % dx)
    data_files.append((dlldir, dllfiles))

plugin_dir = os.path.join(larchdir, 'plugins')
pluginfiles = []
pluginpaths = []
for fname in glob('plugins/*'):
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
        filelist.extend(glob('%s/*.%s' % (pdir, ext)))
    for fname in filelist:
        if os.path.isdir(fname):
            print('Warning -- not walking subdirectories for Plugins!!')
        else:
            pfiles.append(fname)
    data_files.append((os.path.join(larchdir, pdir), pfiles))


if (cmdline_args[0] == 'install' and
    sys.platform == 'darwin' and
    'Anaconda' in sys.version):
    for fname in scripts:
        fh = open(fname, 'r')
        lines = fh.readlines()
        fh.close()
        line0 = lines[0].strip()
        if not line0.startswith('#!/usr/bin/env pythonw'):
            fh = open(fname, 'w')
            fh.write('#!/usr/bin/env pythonw\n')
            fh.write("".join(lines[1:]))
            fh.close()
            print("Rewrote ", fname)


# now we have all the data files, so we can run setup
setup(name = 'xraylarch',
      version = version.__version__,
      author = 'Matthew Newville and the X-rayLarch Development Team',
      author_email = 'newville@cars.uchicago.edu',
      url          = 'http://xraypy.github.io/xraylarch/',
      download_url = 'http://xraypy.github.io/xraylarch/',
      requires = required_modules,
      license = 'BSD',
      description = 'Synchrotron X-ray data analysis in python',
      package_dir = {'larch': 'lib'},
      packages = ['larch', 'larch.utils', 'larch.wxlib',
                  'larch.fitting', 'larch.fitting.uncertainties'],
      data_files  = data_files,
      platforms = ['Windows', 'Linux', 'Mac OS X'],
      classifiers=['Intended Audience :: Science/Research',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Scientific/Engineering'],
     )


def remove_cruft(basedir, filelist):
    """remove files from base directory"""
    def remove_file(base, fname):
        fullname = os.path.join(base, fname)
        if os.path.exists(fullname):
            try:
                os.unlink(fullname)
            except:
                pass
    for fname in filelist:
        remove_file(basedir, fname)
        if fname.endswith('.py'):
            remove_file(basedir, fname+'c')
            remove_file(basedir, fname+'o')


if (cmdline_args[0] == 'install' and sys.platform == 'darwin' and
    'Anaconda' in sys.version):
    for fname in scripts:
        fh = open(fname, 'r')
        lines = fh.readlines()
        fh.close()
        line0 = lines[0].strip()
        if line0.startswith('#!/usr/bin/env pythonw'):
            fh = open(fname, 'w')
            fh.write('#!/usr/bin/env python\n')
            fh.write("".join(lines[1:]))
            fh.close()

def fix_permissions(dirname, stat=None):
    """
    set permissions on a list of directories to match
    those of the HOME directory
    """
    if stat is None:
        return
    def set_perms(fname):
        try:
            os.chown(fname, stat.st_uid, stat.st_gid)
            os.chmod(fname, stat.st_mode)
        except(AttributeError, OSError):
            pass

    for top, dirs, files in os.walk(dirname):
        set_perms(top)
        for d in dirs+files:
            set_perms(os.path.join(top, d))


if cmdline_args[0] == 'install':
    remove_cruft(larchdir, historical_cruft)

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
