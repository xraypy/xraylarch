from setuptools import setup
import epics
import sys
import os
import wx
import wx.lib.agw.flatnotebook
import numpy
import scipy
import matplotlib
matplotlib.use('WXAgg')

import sqlalchemy
import wxutils
import wxmplot
from wxmplot.plotframe import PlotFrame
import larch

from scipy.sparse.csgraph import _validation
from  scipy.io import netcdf
netcdf_open = netcdf.netcdf_file

import PIL as Image
import epics
import Carbon

libca = epics.ca.initialize_libca()
mpl_data_files = matplotlib.get_py2exe_datafiles()

APP = 'GSE_MapViewer.py'
ICONFILE = 'GSEMap.icns'

libca = epics.ca.initialize_libca()
mpl_data_files = matplotlib.get_py2exe_datafiles()

resource_files = ['../COPYING']
## also: use
##  if getattr(sys, 'frozen', None) == 'macosx_app':
## in lib/site_config.py to specify plugin path

plugin_files = []
psrc = "/usr/share/larch"
for dname in os.listdir('%s/plugins' % psrc):
    pname = '%s/plugins/%s' % (psrc, dname)
    if os.path.isdir(pname):
        flist = ['%s/%s' % (pname, f) for f in
                 os.listdir(pname) if not f.endswith('.pyc')]
        plugin_files.append(("larch/plugins/%s" % dname, flist))


dll_files = [("larch/dlls/darwin/",
              ['%s/dlls/darwin/%s' % (psrc, f) for f in
               os.listdir('%s/dlls/darwin' % psrc)]
              )]

DATA_FILES = []

OPTIONS = {'includes': ['ConfigParser', 'Image', 'ctypes', 'epics',
                        'epics.devices', 'fpformat', 'h5py', 'h5py.h5ac',
                        'h5py.h5ac',
                        'h5py._objects', 'h5py._proxy', 'h5py.defs',
                        'h5py.utils', 'matplotlib', 'numpy', 'scipy',
                        'scipy.constants', 'scipy.fftpack',
                        'scipy.io.matlab.mio5_utils',
                        'scipy.io.matlab.streams', 'scipy.io.netcdf',
                        'scipy.optimize', 'scipy.signal',
                        'scipy.sparse.csgraph._validation', 'skimage',
                        'skimage.exposure', 'sqlalchemy',
                        'sqlalchemy.dialects.sqlite', 'sqlalchemy.orm',
                        'sqlalchemy.pool', 'sqlite3', 'wx', 'wx._core',
                        'wx.lib', 'wx.lib.*', 'wx.lib.agw',
                        'wx.lib.agw.flatnotebook',
                        'wx.lib.agw.pycollapsiblepane',
                        'wx.lib.colourselect', 'wx.lib.masked',
                        'wx.lib.mixins', 'wx.lib.mixins.inspection',
                        'wx.lib.newevent', 'wx.py' 'wxmplot' 'wxutils'
                        'wxversion' 'xdrlib' 'xml.etree'
                        'xml.etree.cElementTree'],
           'excludes': ['Tkinter', '_tkinter', 'Tkconstants', 'tcl',
                        '_imagingtk', 'PIL._imagingtk', 'ImageTk',
                        'PIL.ImageTk', 'FixTk''_gtkagg', '_tkagg',
                        'matplotlib.tests',
                        'qt', 'PyQt4Gui', 'email', 'IPython'],
           'site_packages': True,
           'resources': resource_files,
           'iconfile': ICONFILE,
                        }
setup(app=[APP],
      options={'py2app': OPTIONS},
      data_files = mpl_data_files + plugin_files + dll_files,
    )
print "============ "
print "============ HEY, WAKE UP ============ "
print "need to move libfreetype.6.dylib by hand to APPNAME.app/Contents/Framework/. !!"
print " from  mpl folder "

