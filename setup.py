#!/usr/bin/env python
"""
Setup.py for xraylarch
"""
import os
import sys
import time
import shutil
import subprocess
import importlib
from setuptools import setup, find_packages

HAS_CONDA = os.path.exists(os.path.join(sys.prefix, 'conda-meta'))

cmdline_args = sys.argv[1:]
INSTALL = len(cmdline_args)> 0 and (cmdline_args[0] == 'install')
DEVELOP = len(cmdline_args)> 0 and (cmdline_args[0] == 'develop')

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

## Dependencies: required and recommended modules
## do not use `install_requires` for conda environments
install_reqs = []
with open('requirements.txt', 'r') as f:
    install_reqs = f.read().splitlines()

recommended = (('dioptas', 'dioptas', 'XRD Display and Integraton'),
               ('tomopy', 'tomopy', 'Tomographic reconstructions'),
               ('silx', 'silx', 'Spec File reading, XRD'),
               ('fabio', 'fabio', 'XRD File reading'),
               ('pyfai', 'pyFAI', 'XRD intgration'),
               ('pycifrw', 'CifFile', 'Crystallographic Information files'),
               ('psycopg2', 'psycopg2', 'Postgres databases'),
               ('pyepics', 'epics', 'Epics Channel Access'))

missing = []

try:
    import matplotlib
    matplotlib.use('WXAgg')
except:
    pass

for modname, impname, desc in recommended:
    try:
        x = importlib.import_module(impname)
        import_ok = True
    except ImportError:
        import_ok = False
    if not import_ok:
        missing.append('     {:25.25s} {:s}'.format(modname, desc))

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
        fname = pjoin(larchdir, dirname)
        if os.path.exists(fname):
            try:
                shutil.rmtree(fname)
            except PermissionError:
                pass

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
      install_requires=install_reqs,
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
    subprocess.check_call((pjoin(sys.exec_prefix, sys.executable),
                           pjoin(sys.exec_prefix, bindir, larchbin), '-m'))

if len(missing) > 0:
    dl = "#%s#" % ("="*75)
    msg = """%s
 Note: Some optional Python Packages were not found.
 Some functionality will not be available without these packages:

     Package Name              Needed for
     ----------------          ----------------------------------
%s
     ----------------          ----------------------------------

 If you need these capabilities, you may be able to install them with
    pip install <Package Name>
 or
    conda install -c gsecars <Package Name>
%s"""
    print(msg % (dl, '\n'.join(missing), dl))
