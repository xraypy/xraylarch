#
"""
Important note:
seeing errors in build with python setup.py py2exe?

move whole directory to a non-networked drive!

Seeing errors about vcvarsall.bat?

  SET VS90COMNTOOLS=%VS100COMNTOOLS%

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
# import Image
import sqlalchemy
import wx
from wx import MessageDialog
import ctypes
import ctypes.util
from numpy import sort
import cython

# import scipy.lib.six
import scipy.io.netcdf
from scipy.io.netcdf import netcdf_file

from scipy.sparse.csgraph import _validation
from scipy.special import _ufuncs, _ufuncs_cxx
from scipy.linalg import _decomp_update, cython_blas

import scipy.constants

loadlib =  ctypes.windll.LoadLibrary

x = xrange(10)

# larch library bits...
import larch
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


extra_files = ['inno_setup.iss', '../COPYING', '../README.txt',
               '../icons/gse_xrfmap.ico',
               '../icons/epics_scan.ico',
               '../icons/larch.ico',
               '../icons/ptable.ico']

scipy_dlls = ['lib/site-packages/scipy/optimize/minpack2.pyd',
              'lib/site-packages/scipy/interpolate/dftipack.pyd',
              'lib/site-packages/scipy/integrate/_quadpack.pyd',
              'lib/site-packages/numpy/fft/fftpack_lite.pyd']

dlldir = os.path.join(sys.prefix, 'DLLs')
for n in os.listdir(dlldir):
    extra_files.append(os.path.join(dlldir, n))

for n in scipy_dlls:
    extra_files.append(os.path.join(sys.prefix, n))

style_xml = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="x86"
    name="XrayLarch"
    type="win32"
  />
  <description>XrayLarch</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel
            level="asInvoker"
            uiAccess="false">
        </requestedExecutionLevel>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
            type="win32"
            name="Microsoft.VC90.CRT"
            version="9.0.21022.8"
            processorArchitecture="x86"
            publicKeyToken="1fc8b3b9a1e18e3b">
      </assemblyIdentity>
    </dependentAssembly>
  </dependency>
  <dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
  </dependency>
</assembly>
"""

windows_apps = [{'script': '../bin/larch_gui',
                 'icon_resources': [(0, '../icons/larch.ico')],
                 'other_resources': [(24, 1, style_xml)],
                 },
                {'script': '../bin/GSE_MapViewer',
                 'icon_resources': [(0, '../icons/gse_xrfmap.ico')],
                 'other_resources': [(24, 1, style_xml)],
                 },
                {'script': '../bin/EpicsXRFDisplay',
                 'icon_resources': [(0, '../icons/ptable.ico')],
                 'other_resources': [(24, 1, style_xml)],
                 },
                {'script': '../bin/ScanViewer',
                 'icon_resources': [(0, '../icons/epics_scan.ico')],
                 'other_resources': [(24, 1, style_xml)],
                 },
                ]
console_apps = [{'script': '../bin/larch',
                 'icon_resources': [(0, '../icons/larch.ico')]}]


py2exe_opts = {'optimize':1,
               'bundle_files':2,
               'includes': ['ConfigParser',
                            # 'Image',
                            'ctypes',
                            'larch', 'larch.builtins', 
                            'epics', 'epics.devices', 'epics.wx', 
                            'fpformat',
                            'h5py', 'h5py._objects', 'h5py._proxy',
                            'h5py.defs', 'h5py.utils',
                            'matplotlib',
                            'numpy',
                            'scipy',
                            # 'scipy.lib', 
                            # 'scipy.lib.six', 
                            'scipy.constants',
                            'scipy.fftpack',
                            'scipy.sparse',
                            # 'scipy.sparse.compressed',
                            # 'scipy.sparse.sparsetools',
                            'scipy.sparse.csgraph',
                            'scipy.sparse.csgraph.*',
                            'scipy.special.*', 
                            'scipy.linalg',
                            'scipy.linalg.*', 
                            'scipy.io.matlab.mio5_utils',
                            'scipy.io.matlab.streams',
                            'scipy.io.netcdf',
                            'scipy.optimize',
                            'scipy.signal',
                            'skimage',
                            'skimage.exposure', 
                            'sqlalchemy',
                            'sqlalchemy.dialects.sqlite',
                            'sqlalchemy.dialects.postgresql',
                            'sqlalchemy.dialects.mysql', 
                            'sqlalchemy.orm',
                            'sqlalchemy.pool',
                            'sqlite3',
                            'wx',
                            'wx._core',
                            'wx.*',
                            'wx.dataview', 'wx.richtext',
                            'wx.lib', 'wx.lib.agw',
                            'wx.lib.agw.flatnotebook',
                            'wx.lib.colourselect', 'wx.lib.masked',
                            'wx.lib.mixins', 'wx.lib.mixins.inspection',
                            'wx.lib.agw.pycollapsiblepane',
                            'wx.lib.newevent', 'wx.py', 'wxmplot',
                            'wxutils',                            
                            'wxversion', 'xdrlib', 'xml.etree',
                            'xml.etree.cElementTree'],
               'packages': ['h5py', 'wx', 'scipy.optimize', 'scipy.signal', 'scipy.io',
                            'numpy.random', 'xml.etree', 'xml.etree.cElementTree'], 
               'excludes': ['Tkinter', '_tkinter', 'Tkconstants', 'tcl',
                            '_imagingtk', 'PIL._imagingtk', 'ImageTk',
                            'PIL.ImageTk', 'FixTk''_gtkagg', '_tkagg',
                            'matplotlib.tests', 'qt', 'PyQt4Gui', 'IPython',
                            'pywin', 'pywin.dialogs', 'pywin.dialogs.list'],
               'dll_excludes': ['w9xpopen.exe',
                                'libgdk-win32-2.0-0.dll',
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

