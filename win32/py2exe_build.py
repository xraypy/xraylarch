##
"""
Important note:
seeing errors in build with python setup.py py2exe?

move whole directory to a non-networked drive!

"""
##
from distutils.core import setup
# from setuptools import setup
import py2exe
import sys
import os
import shutil
import numpy
import scipy
import matplotlib
import h5py
import Image
import sqlalchemy
import wx
import ctypes
import ctypes.util

import scipy.io.netcdf
from scipy.io.netcdf import netcdf_file
import scipy.constants

loadlib =  ctypes.windll.LoadLibrary

# larch library bits...
from larch.larchlib import get_dll
cllib = get_dll('cldata')

# matplotlib, wxmplot
matplotlib.use('WXAgg')
mpl_data_files = matplotlib.get_py2exe_datafiles()
import wxmplot

# epics
try:
    import epics
    ca = epics.ca.initialize_libca()
except ImportError:
    pass


extra_files = ['inno_setup.iss', '../COPYING', '../README.txt', 'GSEMap.ico']
scipy_dlls = ['lib/site-packages/scipy/optimize/minpack2.pyd',
              'lib/site-packages/scipy/interpolate/dftipack.pyd',
              'lib/site-packages/scipy/integrate/_quadpack.pyd',
              'lib/site-packages/numpy/fft/fftpack_lite.pyd']

dlldir = os.path.join(sys.prefix, 'DLLs')
for n in os.listdir(dlldir):
    extra_files.append(os.path.join(dlldir, n))

for n in scipy_dlls:
    extra_files.append(os.path.join(sys.prefix, n))

windows_apps = [{'script': '../bin/larch_gui',     'icon_resources': [(0, 'larch.ico')]},
                {'script': '../bin/GSE_MapViewer', 'icon_resources': [(0, 'GSEMap.ico')]},
                ]
console_apps = [{'script': '../bin/larch',         'icon_resources': [(0, 'larch.ico')]}]

py2exe_opts = {'optimize':1,
               'bundle_files':2,
               'includes': ['Image', 'ctypes', 'numpy', 
                            'scipy', 'scipy.optimize', 'scipy.constants', 
                            'wx', 'wx._core', 'wx.py', 'wxversion',
                            'wx.lib', 'wx.lib.*', 'wx.lib.masked', 'wx.lib.mixins',
                            'wx.lib.colourselect', 'wx.lib.newevent',
                            'wx.lib.agw', 'wx.lib.agw.flatnotebook',
                            'h5py', 'h5py._objects', 'h5py.defs', 'h5py.utils', 'h5py._proxy',
                            'matplotlib', 'wxmplot',
                            'ConfigParser', 'fpformat',
                            'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.pool',
                            'sqlite3', 'sqlalchemy.dialects.sqlite',
                            'xdrlib',  'epics', 'epics.devices'],
              
               'packages': ['h5py', 'scipy.optimize', 'scipy.signal', 'scipy.io',
                            'numpy.random', 'xml.etree', 'xml.etree.cElementTree'], 
               'excludes': ['Tkinter', '_tkinter', 'Tkconstants', 'tcl',
                            '_imagingtk', 'PIL._imagingtk', 'ImageTk',
                            'PIL.ImageTk', 'FixTk''_gtkagg', '_tkagg',
                            'matplotlib.tests', 'qt', 'PyQt4Gui', 'IPython'],

               'dll_excludes': ['libgdk-win32-2.0-0.dll',
                                'libgobject-2.0-0.dll', 'libzmq.dll']
               }

setup(name = "Larch",
      windows = windows_apps,
      console = console_apps,
      options = {'py2exe': py2exe_opts},
      data_files = mpl_data_files)
 
for fname in extra_files:
    path, name = os.path.split(fname)
    print fname, name
    try:
        shutil.copy(fname, os.path.join('dist', name))
    except:
        pass


if __name__ == '__main__':
    print 'usage:  python py2exe_build.py py2exe'

