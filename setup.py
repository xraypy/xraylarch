#!/usr/bin/env python
"""
Setup.py for xraylarch
"""
from __future__ import print_function
from distutils.core import setup

import time
import os
import sys
import site
import platform
from glob import glob

DEBUG = False
cmdline_args = sys.argv[1:]
INSTALL =  len(cmdline_args)> 0 and (cmdline_args[0] == 'install')


_version__ = None
with open(os.path.join('lib', 'version.py'), 'r') as version_file:
    lines = version_file.readlines()
    for line in lines:
        line = line[:-1]
        if line.startswith('__version__'):
            key, vers = [w.strip() for w in line.split('=')]
            __version__ = vers.replace("'",  "").replace('"',  "").strip()


##
## Dependencies: required and recommended modules

required_modules = {'numpy': 'numpy',
                    'scipy': 'scipy',
                    'matplotlib': 'matplotlib',
                    'h5py': 'h5py',
                    'sqlalchemy': 'sqlalchemy',
                    'requests': 'requests',
                    'six' : 'six',
                    'psutil': 'psutil',
                    'peakutils': 'peakutils',
                    'PIL' : 'pillow',
                    'asteval': 'asteval',
                    'lmfit': 'lmfit',
                    'termcolor': 'termcolor'}


graphics_modules = {'wx': 'wxPython',
                    'wxmplot': 'wxmplot',
                    'wxutils': 'wxutils'}

xrd_modules  = {'pyFAI': 'pyFAI', 'CifFile' : 'PyCifRW',
                'fabio': 'fabio'}

tomo_modules = {'tomopy': 'tomopy',
                'skimage': 'scikit-image'}

epics_modules = {'epics': 'pyepics'}
scan_modules = {'epicsscan': 'epicsscan', 'psycopg2': 'psycopg2'}

testing_modules = {'nose': 'nose', 'pytest': 'pytest'}

all_modules = (('basic analysis', required_modules),
           ('graphics and plotting', graphics_modules),
           ('xrd modules', xrd_modules),
           ('tomography modules', tomo_modules),
           ('connecting to the EPICS control system', epics_modules),
            # ('scanning with EpicsScan', scan_modules),
           ('testing tools',  testing_modules))


# files that may be left from earlier install(s) and should be removed
historical_cruft = ['plugins/xrd/xrd_hkl.py',
                    'plugins/xrd/xrd_util.py',
                    'plugins/xrd/xrd_xutil.py']

modules_imported = {}
missing = []


try:
    import matplotlib
    matplotlib.use('WXAgg')
except:
    pass
print( 'Checking dependencies....')
for desc, mods in all_modules:
    for impname, modname in mods.items():
        if impname not in modules_imported:
            modules_imported[modname] = False
        try:
            x = __import__(impname)
            modules_imported[modname] = True
        except ImportError:
            s = (modname + ' '*25)[:25]
            missing.append('     %s %s' % (s, desc))
missing_reqs = []
for mod in modules_imported:
    if mod in required_modules and not modules_imported[mod]:
        missing_reqs.append(mod)

if len(missing_reqs) > 0:
    print('\n=== Cannot Install Larch, these REQUIRED Modules are missing: ')
    print(' %s' % (', '.join(missing_reqs)))
    print(' ')
    print(' Please read INSTALL for further information.')
    print(' ')
    sys.exit()


## For Travis-CI, need to write a local site config file
##
if os.environ.get('TRAVIS_CI_TEST', '0') == '1':
    time.sleep(0.2)


##

isdir = os.path.isdir
pjoin = os.path.join
pexists = os.path.exists


# system-wide larch directory
larchdir = pjoin(sys.exec_prefix, 'share', 'larch')

##
## determine this platform for dlls and exes

nbits = platform.architecture()[0].replace('bit', '')

uname  = 'linux'
libfmt = 'lib%s.so'
bindir = 'bin'
pyexe = pjoin(bindir, 'python')

if os.name == 'nt':
    uname  = 'win'
    libfmt = '%s.dll'
    bindir = 'Scripts'
    pyexe = 'python.exe'
elif sys.platform == 'darwin':
    uname  = 'darwin'
    libfmt = 'lib%s.dylib'

uname = "%s%s" % (uname, nbits)

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

scripts  =  glob('bin/*')
if not uname.startswith('win'):
    scripts = [s for s in scripts if not s.endswith('.bat')]

scripts.extend(glob("%s/*" % pjoin('exes', uname)))

larch_mods = glob('modules/*.lar') + glob('modules/*.py')
larch_icos = glob('icons/*.ic*')

larch_dlls = glob("%s/*" % pjoin('dlls', uname))

data_files = [(bindir,  scripts),
              (pjoin(larchdir, 'icons'),       larch_icos),
              (pjoin(larchdir, 'modules'),     larch_mods),
              (pjoin(larchdir, 'dlls', uname), larch_dlls)]

plugin_dir = pjoin(larchdir, 'plugins')
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
    data_files.append((pjoin(larchdir, pdir), pfiles))


# now we have all the data files, so we can run setup
setup(name = 'xraylarch',
      version = __version__,
      author = 'Matthew Newville and the X-rayLarch Development Team',
      author_email = 'newville@cars.uchicago.edu',
      url          = 'http://xraypy.github.io/xraylarch/',
      download_url = 'http://xraypy.github.io/xraylarch/',
      requires = list(required_modules.keys()),
      license = 'BSD',
      description = 'Synchrotron X-ray data analysis in python',
      package_dir = {'larch': 'lib'},
      packages = ['larch', 'larch.utils', 'larch.wxlib', 'larch.fitting'],
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
        fullname = pjoin(base, fname)
        if os.path.exists(fullname):
            print( " removing %s " %  fullname)
            try:
                os.unlink(fullname)
            except:
                pass

    for fname in filelist:
        remove_file(basedir, fname)
        if fname.endswith('.py'):
            remove_file(basedir, fname+'c')
            remove_file(basedir, fname+'o')


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
            set_perms(pjoin(top, d))

def fix_darwin_dylibs():
    """
    fix dynamic libs on Darwin with install_name_tool
    """
    olddir    = '/usr/local/gfortran/lib'
    newdir    = sys.prefix
    larchdlls = 'share/larch/dlls/darwin64'

    dylibs = ('libgcc_s.1.dylib','libquadmath.0.dylib', 'libgfortran.3.dylib',
              'libfeff6.dylib', 'libcldata.dylib', 'libfeff8lpath.dylib',
              'libfeff8lpotph.dylib')

    exes = ('feff6l', 'feff8l_ff2x', 'feff8l_genfmt', 'feff8l_pathfinder',
            'feff8l_pot', 'feff8l_rdinp', 'feff8l_xsph')

    fixcmd = '/usr/bin/install_name_tool -change'

    cmds = []
    for ename in exes:
        ename = pjoin(newdir, 'bin', ename)
        for dname in dylibs:
            old = pjoin(olddir, dname)
            new = pjoin(newdir, larchdlls, dname)
            cmds.append("%s %s %s %s" % (fixcmd, old, new, ename))

    for ename in dylibs:
        ename = pjoin(newdir, larchdlls, ename)
        for dname in dylibs:
            old = pjoin(olddir, dname)
            new = pjoin(newdir, larchdlls, dname)
            cmds.append("%s %s %s %s" % (fixcmd, old, new, ename))

    for cmd in cmds:
        os.system(cmd)

if INSTALL:
    remove_cruft(larchdir, historical_cruft)

# final install:
#   create desktop icons
#   fix dynamic libraries
if INSTALL and (uname.startswith('darwin') or uname.startswith('win')):
    cmd ="%s %s" % (pjoin(sys.exec_prefix, pyexe),
                    pjoin(sys.exec_prefix, bindir, 'larch_makeicons'))
    os.system(cmd)

    if uname.startswith('darwin'):
        fix_darwin_dylibs()

if len(missing) > 0:
    dl = "#%s#" % ("="*75)
    msg = """%s
 Warning: Some optional Python Packages were not found. Some functionality
 will not be available without these packages:

     Package Name              Needed for
     ----------------          ----------------------------------
%s
     ----------------          ----------------------------------

 If you need some of these capabilities, you can install them with
    `pip install <Package Name>` or `conda install <Package Name>`

 See the Optional Modules section of doc/installation.rst for more details.
%s"""
    print(msg % (dl, '\n'.join(missing), dl))
