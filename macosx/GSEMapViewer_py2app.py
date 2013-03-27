from setuptools import setup
import epics
import os
import wx
import wx.lib.agw.flatnotebook
import numpy
import scipy
import matplotlib
matplotlib.use('WXAgg')

import wxmplot
import larch

libca = epics.ca.initialize_libca()
mpl_data_files = matplotlib.get_py2exe_datafiles()

resource_files = ['COPYING']
## also: use
##  if getattr(sys, 'frozen', None) == 'macosx_app':
## in lib/site_config.py to specify plugin path

plugin_files = []
psrc = "/usr/share/larch/"
for dname in os.listdir('%s/plugins' % psrc):
    pname = 'plugins/%s' % dname
    if os.path.isdir(pname):
        flist = ['%s/%s/%s' % (psrc, pname, f) for f in os.listdir(pname) if not f.endswith('.pyc')]
        plugin_files.append(("larch/%s" % pname, flist))

APP = ['GSE_MapViewer.py']
DATA_FILES = []
# OPTIONS = {'argv_emulation': True, 'includes': 'epics, wx, Image'}
OPTIONS = {'includes': ['Image', 'ctypes', 'numpy', 'scipy', 'scipy.optimize',
                        'wx', 'wx._core', 'wx.py', 'wxversion',
                        'wx.lib', 'wx.lib.*', 'wx.lib.masked', 'wx.lib.mixins',
                        'wx.lib.colourselect', 'wx.lib.newevent',
                        'wx.lib.agw', 'wx.lib.agw.flatnotebook',
                        'h5py', 'h5py._objects', 'h5py.defs', 'h5py.utils', 'h5py._proxy',
                        'matplotlib', 'wxmplot', 'ConfigParser', 'fpformat',
                        'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.pool',
                        'sqlite', 'sqlalchemy.dialects.sqlite',
                        'xml.etree', 'xml.etree.cElementTree', 'xdrlib',
                        'epics', 'epics.devices'],
           'excludes': ['Tkinter', '_tkinter', 'Tkconstants', 'tcl',
                        '_imagingtk', 'PIL._imagingtk', 'ImageTk',
                        'PIL.ImageTk', 'FixTk''_gtkagg', '_tkagg',
                        'qt', 'PyQt4Gui', 'email'],
           'site_packages': True,
           'resources': resource_files,
           'iconfile': 'GSEMap.icns',
                        }
setup(app=APP,
      options={'py2app': OPTIONS},
      data_files = mpl_data_files + plugin_files,
    )
