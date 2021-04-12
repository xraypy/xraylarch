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
try:
    from packaging.version import parse as version_parse
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = True

HAS_CONDA = os.path.exists(os.path.join(sys.prefix, 'conda-meta'))

cmdline_args = sys.argv[1:]
INSTALL = len(cmdline_args)> 0 and (cmdline_args[0] == 'install')
DEVELOP = len(cmdline_args)> 0 and (cmdline_args[0] == 'develop')

uname = sys.platform.lower()
if os.name == 'nt':
    uname = 'win'

_version__ = None
with open(os.path.join('larch', 'version.py'), 'r') as version_file:
    lines = version_file.readlines()
    for line in lines:
        line = line[:-1]
        if line.startswith('__version__'):
            key, vers = [w.strip() for w in line.split('=')]
            __version__ = vers.replace("'",  "").replace('"',  "").strip()

## Dependencies: required and recommended modules
install_reqs = []
with open('requirements.txt', 'r') as f:
    for line in f.read().splitlines():
        if not line.startswith('#'):
            install_reqs.append(line)

try:
    import wx
    install_reqs.extend(['wxutils>=0.2.3', 'wxmplot>=0.9.43'])
except (ImportError, AttributeError):
    pass


#          required,  module name, import name, min version, description
modules = ((True, 'numpy', 'numpy', '1.12', 'basic scientific python'),
           (True, 'scipy', 'scipy', '1.2', 'basic scientific python'),
           (True, 'matplotlib', 'matplotlib', '3.0', 'basic scientific python'),
           (True, 'h5py', 'h5py', '2.8', 'basic scientific python'),
           (True, 'pillow', 'PIL', '7.0', 'basic scientific python'),
           (True, 'sqlalchemy', 'sqlalchemy', '0.9', 'basic python'),
           (True, 'pyyaml', 'yaml', '5.0', 'basic python'),
           (True, 'requests', 'requests', '0.2', 'basic python'),
           (True, 'scikit-image', 'skimage', '0.17', 'scientific python'),
           (True, 'scikit-learn', 'sklearn', '0.23', 'scientific python'),
           (True, 'lmit', 'lmfit', '1.0', 'scientific python'),
           (True, 'asteval', 'asteval', '0.9.17', 'scientific python'),
           (True, 'uncertainties', 'uncertainties', '3.0', 'scientific python'),
           (True, 'xraydb', 'xraydb', '4.4.5', 'scientific python'),
           # (False, 'dioptas', 'dioptas', '0.4', 'XRD Display and Integraton'),
           (False, 'tomopy', 'tomopy', '1.4', 'Tomographic reconstructions'),
           (False, 'silx', 'silx', '0.12', 'Spec File reading, XRD'),
           (False, 'fabio', 'fabio', '0.10.0', 'XRD File reading'),
           (False, 'pyfai', 'pyFAI', '0.17', 'XRD intgration'),
           (False, 'pycifrw', 'CifFile', None, 'Crystallographic Information files'),
           (False, 'psycopg2', 'psycopg2', '2.8.5', 'Postgres databases'),
           (False, 'pyepics', 'epics', '3.4.0', 'Epics Channel Access'),
           (False, 'wxpython', 'wx', '4.0.4', 'Graphical User interface'),
           (False, 'wxmplot', 'wxmplot', '0.9.43', 'Graphical User interface'),
           (False, 'wxutils', 'wxutils', '0.2.3', 'Graphical User interface'),
           )

missing = []
for required, modname, impname, minver, desc in modules:
    try:
        x = importlib.import_module(impname)
        import_ok, version_ok = True, False
        ver = getattr(x, '__version__', None)
        if ver is None:
            ver = getattr(x, 'version', None)
        if ver is not None and ' ' in ver:
            ver = ver.split(' ', 1)[0]
        if callable(ver): ver = ver()
        version_ok = True
        if HAS_PACKAGING and minver is not None and ver is not None:
            version_ok = version_parse(minver) <= version_parse(ver)
    except: #  ImportError:
        import_ok, version_ok = False, True
    if not (import_ok and version_ok):
        if minver is None: minver = ''
        pref = '***' if required else ''
        missing.append(' {:3.3s} {:18.18s} {:8.8s}  {:s}'.format(pref, modname,
                                                                 minver, desc))


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
           'gse_mapviewer', 'xrfdisplay', 'xrfdisplay_epics']

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
      python_requires='>=3.6',
      packages = packages,
      install_requires=install_reqs,
      package_data={'larch': package_data},
      zip_safe=False,
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
    py_exe = pjoin(sys.exec_prefix, sys.executable)
    larch_exe = pjoin(sys.exec_prefix, bindir, larchbin)
    if not pexists(larch_exe):
        user = os.path.expanduser('~')

        for base in (sys.prefix, sys.exec_prefix,
                     pjoin(user, 'anaconda3'),
                     pjoin(user, 'local'),
                     '/opt/local', '/anaconda3/', '/opt/anaconda3'):
            if pexists(pjoin(base, larchbin)):
                larch_exe = pexists(pjoin(base, larchbin))
            elif pexists(pjoin(base, 'bin', larchbin)):
                larch_exe = pexists(pjoin(base, larchbin))

    if pexists(larch_exe):
        subprocess.check_call((py_exe,  larch_exe, '-m'))

if len(missing) > 0:
    dl = "#%s#" % ("="*75)
    msg = """%s
 Some Python Packages were not found.  Those marked with '***' are
 required for larch to work, while other packages listed will mean
 that some functionality will not be available:

     Package Name      Version    Needed for
     ----------------             ----------------------------------
%s
     ----------------             ----------------------------------

 If you need these capabilities, you may be able to install them with
    pip install <Package Name>

or, for anaconda python, you may use
   conda install -c conda-forge <Package Name>
%s"""
    print(msg % (dl, '\n'.join(missing), dl))
