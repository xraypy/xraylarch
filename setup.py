#!/usr/bin/env python
"""
Setup.py for xraylarch
"""
import os
import sys
import time
import shutil
import subprocess
from setuptools import setup, find_packages

cmdline_args = sys.argv[1:]
INSTALL =  len(cmdline_args)> 0 and (cmdline_args[0] == 'install')
DEVELOP =  len(cmdline_args)> 0 and (cmdline_args[0] == 'develop')

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

missing = []

try:
    import matplotlib
    matplotlib.use('WXAgg')
except:
    pass

print( 'Checking dependencies....')
for desc, mods in all_modules:
    for impname, modname in mods.items():
        try:
            x = __import__(impname)
        except ImportError:
            s = (modname + ' '*25)[:25]
            missing.append('     %s %s' % (s, desc))

## For Travis-CI, need to write a local site config file
##
if os.environ.get('TRAVIS_CI_TEST', '0') == '1':
    time.sleep(0.2)


pjoin = os.path.join
pexists = os.path.exists

bindir = 'bin'
pyexe = pjoin(bindir, 'python')
larchbin = 'larch'

if uname == 'win':
    bindir = 'Scripts'
    pyexe = 'python.exe'
    larchbin = 'larch-script.py'

# list of top level scripts to add to Python's bin/
scripts = ['larch', 'larch_server', 'feff6l', 'feff8l', 'xas_viewer',
           'gse_mapviewer', 'gse_dtcorrect', 'xrd1d_viewer','xrd2d_viewer',
           'dioptas_larch', 'xrfdisplay', 'xrfdisplay_epics']

larch_apps = ['{0:s} = larch.apps:run_{0:s}'.format(n) for n in scripts]

packages = ['larch', 'larch.bin']
for pname in find_packages('larch'):
    packages.append('larch.%s' % pname)


package_data = ['icons/*', 'xray/*.dat', 'xray/*.db', 'xrd/*.db',
                'bin/darwin64/*', 'bin/linux64/*', 'bin/win64/*',
                'bin/win32/*']


if INSTALL:
    # before install:  remove historical cruft, including old plugins
    cruft = {'bin': ['larch_makeicons', 'larch_gui', 'larch_client',
                     'gse_scanviewer', 'feff8l_ff2x', 'feff8l_genfmt',
                     'feff8l_pathfinder', 'feff8l_pot', 'feff8l_rdinp',
                     'feff8l_xsph']}

    def remove_file(base, fname):
        fullname = pjoin(base, fname)
        if pexists(fullname):
            try:
                os.unlink(fullname)
            except:
                pass

    for category, flist in cruft.items():
        if category == 'bin':
            basedir = pjoin(sys.exec_prefix, bindir)
            for fname in flist:
                remove_file(basedir, fname)

    # remove all files in share/larch from earlier code layouts
    # system-wide larch directory
    larchdir = pjoin(sys.exec_prefix, 'share', 'larch')
    for dirname in ('plugins', 'dlls', 'icons'):
        fname = pjoin(larchdir, 'plugins')
        if os.path.exists(fname):
            shutil.rmtree(fname)

with open('requirements.txt', 'r') as f:
    install_reqs = f.read().splitlines()

# now we have all the data files, so we can run setup
setup(name = 'xraylarch',
      version = __version__,
      author = 'Matthew Newville and the X-rayLarch Development Team',
      author_email = 'newville@cars.uchicago.edu',
      url          = 'http://xraypy.github.io/xraylarch/',
      download_url = 'http://xraypy.github.io/xraylarch/',
      license = 'BSD',
      description = 'Synchrotron X-ray data analysis in python',
      python_requires='>=3.5.1',
      # install_requires=install_reqs,
      packages = packages,
      package_data={'larch': package_data},
      entry_points = {'console_scripts' : larch_apps},
      platforms = ['Windows', 'Linux', 'Mac OS X'],
      classifiers=['Intended Audience :: Science/Research',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'License :: OSI Approved :: BSD License',
                   'Topic :: Scientific/Engineering'],
      )

# create desktop icons
if INSTALL or DEVELOP:
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
