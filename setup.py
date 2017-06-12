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

try:
    from setuptools.command.build_py import build_py as _build_py
except ImportError:
    from distutils.command.build_py import build_py as _build_py

import version

DEBUG = False
cmdline_args = sys.argv[1:]
INSTALL =  (cmdline_args[0] == 'install')
PROJECT="larch"

# ########## #
# version.py #
# ########## #
class build_py(_build_py):
    """
    Enhanced build_py which copies version.py to <PROJECT>.version.py
    """
    def find_package_modules(self, package, package_dir):
        modules = _build_py.find_package_modules(self, package, package_dir)
        if package == PROJECT:
            modules.append((PROJECT, 'version', 'version.py'))
        return modules


##
## Dependencies: required and recommended modules
##

required_modules = ['numpy', 'scipy', 'lmfit', 'h5py', 'sqlalchemy', 'six',
                    'PIL', 'requests']
graphics_modules = ['matplotlib', 'wx', 'wxmplot', 'wxutils']

xrd_modules = ['pyFAI','CifFile', 'fabio']

recommended_modules = {'basic analysis': required_modules,
                       'graphics and plotting': graphics_modules,
                       'xrd modules' : xrd_modules,
                       'color-enhanced error messages': ('termcolor', ),
                       'using the EPICS control system': ('epics', ),
                       'testing tools': ('nose', ),
                       }

# files that may be left from earlier install(s) and should be removed
historical_cruft = ['plugins/xrd/xrd_hkl.py',
                    'plugins/xrd/xrd_util.py',
                    'plugins/xrd/xrd_xutil.py']

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
is_anaconda = 'Anaconda' in sys.version

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


altered_py_scripts = []
if INSTALL and is_anaconda and uname.startswith('darwin'):
    for fname in scripts:
        fh = open(fname, 'r')
        try:
            lines = fh.readlines()
        except:
            lines = ['binary file?']
        fh.close()
        line0 = lines[0].strip()
        if (line0.startswith('#!/usr/bin/env python')
            and 'pythonw' not in line0):
            fh = open(fname, 'w')
            fh.write('#!/usr/bin/env pythonw\n')
            fh.write("".join(lines[1:]))
            fh.close()
            altered_py_scripts.append(fname)


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
      packages = ['larch', 'larch.utils', 'larch.wxlib', 'larch.fitting'],
      data_files  = data_files,
      platforms = ['Windows', 'Linux', 'Mac OS X'],
      classifiers=['Intended Audience :: Science/Research',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Scientific/Engineering'],
      cmdclass=dict(build_py=build_py,)
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

if INSTALL and is_anaconda and uname.startswith('darwin'):
    for fname in altered_py_scripts:
        fh = open(fname, 'r')
        try:
            lines = fh.readlines()
        except:
            lines = ['binary file?']
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
    exes   = ('feff6l',)
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

if deps_ok and not os.path.exists('.deps'):
    f = open('.deps', 'w')
    f.write('1\n')
    f.close()

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
    msg = """
#==============================================================#
#=== Warning: Some recommended Python Packages are missing:
%s

Some functionality will not work until these are installed.
See INSTALL for further information.
#==============================================================#"""
    print(msg %  '\n'.join(missing))
