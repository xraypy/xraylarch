#!/usr/bin/env python
"""
Setup.py for xraylarch
"""
from __future__ import print_function
from setuptools import setup

import time
import os
import sys
import site
import platform
from glob import glob
import shutil
import subprocess

DEBUG = False
cmdline_args = sys.argv[1:]
INSTALL =  len(cmdline_args)> 0 and (cmdline_args[0] == 'install')


nbits = platform.architecture()[0].replace('bit', '')
uname = sys.platform.lower()
if os.name == 'nt':
    uname = 'win'
if uname.startswith('linux'):
    uname = 'linux'

_version__ = None
with open(os.path.join('larch', 'version.py'), 'r') as version_file:
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
                    'pyshortcuts': 'pyshortcuts',
                    'peakutils': 'peakutils',
                    'PIL' : 'pillow',
                    'asteval': 'asteval',
                    'uncertainties': 'uncertainties',
                    'lmfit': 'lmfit',
                    'yaml': 'pyyaml',
                    'termcolor': 'termcolor'}


graphics_modules = {'wx': 'wxPython', 'wxmplot': 'wxmplot', 'wxutils':'wxutils'}

xrd_modules  = {'pyFAI': 'pyFAI', 'CifFile' : 'PyCifRW', 'fabio': 'fabio',
                'dioptas': 'Dioptas'}

tomo_modules = {'tomopy': 'tomopy', 'skimage': 'scikit-image'}

epics_modules = {'epics': 'pyepics'}
scan_modules = {'epicsscan': 'epicsscan', 'psycopg2': 'psycopg2'}

spec_modules = {'silx': 'silx'}
pca_modules = {'sklearn': 'scikit-learn'}

testing_modules = {'nose': 'nose', 'pytest': 'pytest'}

all_modules = (('basic analysis', required_modules),
               ('graphics and plotting', graphics_modules),
               ('xrd modules', xrd_modules),
               ('tomography modules', tomo_modules),
               ('connecting to the EPICS control system', epics_modules),
               ('reading Spec files', spec_modules),
               ('PCA and machine learning', pca_modules),
               ('testing tools',  testing_modules))


compiled_exes = ('feff6l', 'feff8l_ff2x', 'feff8l_genfmt',
                 'feff8l_pathfinder', 'feff8l_pot', 'feff8l_rdinp',
                 'feff8l_xsph')

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

## For Travis-CI, need to write a local site config file
##
if os.environ.get('TRAVIS_CI_TEST', '0') == '1':
    time.sleep(0.2)


isdir = os.path.isdir
pjoin = os.path.join
psplit = os.path.split
pexists = os.path.exists

# system-wide larch directory
larchdir = pjoin(sys.exec_prefix, 'share', 'larch')

## determine this platform for dlls and exes
nbits = platform.architecture()[0].replace('bit', '')

libfmt = 'lib%s.so'
exefmt = "%s"
bindir = 'bin'
pyexe = pjoin(bindir, 'python')

if uname == 'darwin':
    libfmt = 'lib%s.dylib'
elif uname == 'win':
    libfmt = '%s.dll'
    exefmt = "%s.exe"
    bindir = 'Scripts'
    pyexe = 'python.exe'

sname = "%s%s" % (uname, nbits)

if DEBUG:
    print("##  Settings  (Debug mode) ## ")
    print(" larchdir: ",  larchdir)
    print(" sys.prefix: ",  sys.prefix)
    print(" sys.exec_prefix: ",  sys.exec_prefix)
    print(" cmdline_args: ",  cmdline_args)
    print("##   ")


# construct list of files to install besides the normal python modules
# this includes the larch executable files, and all the larch plugins

data_files = [(pjoin(larchdir, 'icons'),       glob('icons/*.ic*')),
              (pjoin(larchdir, 'dlls', sname), glob("%s/*" % pjoin('dlls', sname)))]


scripts = ['larch', 'larch_server', 'feff8l', 'xas_viewer',
           'gse_mapviewer', 'gse_dtcorrect', 'xrd1d_viewer','xrd2d_viewer',
           'dioptas', 'xrfdisplay', 'xrfdisplay_epics']

larch_apps = ['{0:s} = larch.apps:run_{0:s}'.format(n) for n in scripts]

plugin_dir = pjoin(larchdir, 'plugins')
pluginfiles = []
pluginpaths = []
for fname in glob('plugins/*'):
    if isdir(fname):
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
        if isdir(fname):
            print('Warning -- not walking subdirectories for Plugins!!')
        else:
            pfiles.append(fname)
    data_files.append((pjoin(larchdir, pdir), pfiles))

# Get all required packages from requirements.txt:
with open('requirements.txt', 'r') as f:
    requirements = f.readlines()


# now we have all the data files, so we can run setup
setup(name = 'xraylarch',
      version = __version__,
      author = 'Matthew Newville and the X-rayLarch Development Team',
      author_email = 'newville@cars.uchicago.edu',
      url          = 'http://xraypy.github.io/xraylarch/',
      download_url = 'http://xraypy.github.io/xraylarch/',
      license = 'BSD',
      description = 'Synchrotron X-ray data analysis in python',
      packages = ['larch', 'larch.utils', 'larch.wxlib', 'larch.fitting'],
      install_requires=requirements,
      data_files  = data_files,
      entry_points = {'console_scripts' : larch_apps},
      platforms = ['Windows', 'Linux', 'Mac OS X'],
      classifiers=['Intended Audience :: Science/Research',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Scientific/Engineering'],
      )


def remove_cruft():
    """remove files that may be left from earlier installs"""
    cruft = {'plugins': ['xrd/xrd_hkl.py',
                         'xrd/xrd_util.py',
                         'xrd/xrd_xutil.py'],
             'bin': ['larch_makeicons', 'larch_gui', 'larch_client',
                     'gse_scanviewer']}

    def remove_file(base, fname):
        fullname = pjoin(base, fname)
        if pexists(fullname):
            try:
                os.unlink(fullname)
            except:
                pass

    for category, flist in cruft.items():
        if category == 'plugins':
            basedir = pjoin(larchdir, 'plugins')
            for fname in flist:
                remove_file(basedir, fname)
                if fname.endswith('.py'):
                    remove_file(basedir, fname+'c')
                    remove_file(basedir, fname+'o')

        if category == 'bin':
            basedir = pjoin(sys.exec_prefix, bindir)
            for fname in flist:
                remove_file(basedir, fname)
                if fname.endswith('.py'):
                    remove_file(basedir, fname+'c')
                    remove_file(basedir, fname+'o')

def remove_distutils_sitepackage():
    """rename site-packages/larch folder that may be
    left over from earlier installs using distutils"""
    for spath in site.getsitepackages():
        lpath = os.path.join(spath, 'larch')
        if os.path.exists(lpath) and os.path.isdir(lpath):
            dest = lpath + '_outdated'
            if os.path.exists(dest):
                shutil.rmtree(dest)
            try:
                shutil.move(lpath, dest)
            except:
                pass

def copy_compiled_exes():
    for exename in compiled_exes:
        exe = exefmt % exename
        src = os.path.abspath(pjoin('exes', sname, exe))
        dest = os.path.abspath(pjoin(sys.prefix, bindir, exe))
        shutil.copy(src, dest)
        os.chmod(dest, 493)


def fix_darwin_dylibs():
    """
    fix dynamic libs on Darwin with install_name_tool
    """
    olddir    = '/usr/local/gfortran/lib'
    larchdlls = 'share/larch/dlls/darwin64'
    newdir    = pjoin(sys.prefix, larchdlls)

    dylibs = ('libgcc_s.1.dylib','libquadmath.0.dylib', 'libgfortran.3.dylib',

              'libfeff6.dylib', 'libcldata.dylib', 'libfeff8lpath.dylib',
              'libfeff8lpotph.dylib')

    fixcmd = '/usr/bin/install_name_tool -change'

    cmds = []

    for ename in compiled_exes:
        ename = pjoin(sys.prefix, bindir, ename)
        for dname in dylibs:
            old = pjoin(olddir, dname)
            new = pjoin(newdir, dname)
            cmds.append("%s %s %s %s" % (fixcmd, old, new, ename))

    for ename in dylibs:
        ename = pjoin(newdir, ename)
        for dname in dylibs:
            old = pjoin(olddir, dname)
            new = pjoin(newdir, dname)
            cmds.append("%s %s %s %s" % (fixcmd, old, new, ename))

    for cmd in cmds:
        os.system(cmd)

def fix_darwin_exes():
    "fix anaconda python apps on MacOs to launch with pythonw"

    pyapp = pjoin(sys.prefix, 'python.app', 'Contents', 'MacOS', 'python')
    if not pexists(pyapp):
        return
    for script in scripts:
        appname = os.path.join(sys.exec_prefix, bindir, script)
        if os.path.exists(appname):
            with open(appname, 'r') as fh:
                try:
                    lines = fh.readlines()
                except IOError:
                    lines = ['-']
            time.sleep(.025)
            if len(lines) > 1:
                text = ["#!%s\n" % pyapp]
                text.extend(lines[1:])
                with open(appname, 'w') as fh:
                    fh.write("".join(text))

def fix_linux_dylibs():
    """
    fix dynamic libs on Linux with patchelf
    """
    larchdlls = os.path.join(sys.prefix, 'share/larch/dlls/linux64')

    fixcmd = "%s/bin/patchelf --set-rpath "  % (sys.prefix)

    dylibs = ('libgcc_s.so.1','libquadmath.so.0', 'libgfortran.so.3',
              'libfeff6.so', 'libcldata.so', 'libfeff8lpath.so',
              'libfeff8lpotph.so')
    for lname in dylibs:
        os.system("%s '$ORIGIN' %s" % (fixcmd, os.path.join(larchdlls, lname)))

    for ename in compiled_exes:
        os.system("%s %s %s/bin/%s" % (fixcmd, larchdlls, sys.prefix, ename))

# on install:
#   remove historical cruft
#   fix dynamic libraries
#   copy compiled exes to top bin directory (out of egg)
#   fix MacOS + Anaconda python vs. pythonw
#   create desktop icons
if INSTALL:
    remove_cruft()
    remove_distutils_sitepackage()
    copy_compiled_exes()

    larchbin = 'larch'
    if uname.startswith('darwin'):
        fix_darwin_dylibs()
        fix_darwin_exes()
    elif uname.startswith('linux'):
        fix_linux_dylibs()
    elif uname.startswith('win'):
        larchbin = 'larch-script.py'
    subprocess.check_call((pjoin(sys.exec_prefix, pyexe),
                           pjoin(sys.exec_prefix, bindir, larchbin), '-m'))

if len(missing) > 0:
    dl = "#%s#" % ("="*75)
    msg = """%s
 Note: Some optional Python Packages were not found. Some functionality
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
