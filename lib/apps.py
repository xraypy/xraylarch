import os
import sys
import numpy
import pkg_resources

from optparse import OptionParser

from pyshortcuts import make_shortcut

from .site_config import larchdir, home_dir


class LarchApp:
    def __init__(self, name, script, icon='larch', terminal=False):
        self.name = name
        self.scipt = script
        self.icon = icon
        self.terminal = terminal
        self.icoext = '.ico'
        if platform.startswith('darwin'):
            self.icoext = '.icns'

        bindir = 'bin'
        if platform.startswith('win'):
            bindir = 'Scripts'

        self.bindir = os.path.join(sys.prefix, bindir)
        self.icondir = os.path.join(larchdir, 'icons')

    def create_shortcut(self):
        make_shortcut(os.path.join(self.bindir, self.script),
                      name=self.name,
                      icon=os.path.join(self.icondir, self.icon+self.icoext),
                      terminal=self.terminal,
                      folder='Larch')


APPS = (LarchApp('Larch CLI', 'larch', terminal=True),
        LarchApp('Larch GUI', 'larch --wxgui'),
        LarchApp('XAS Viewer',  'xas_viewer',  icon='onecone'),
        LarchApp('GSE Mapviewer', 'gse_mapviewer',  icon='gse_xrfmap'),
        LarchApp('XRF Display',  'xrfdisplay',  icon='ptable'),
        LarchApp('2D XRD Viewer', 'diFFit2D'),
        LarchApp('1D XRD Viewer', 'diFFit1D') )

def make_desktop_shortcuts():
    """make desktop shortcuts for Larch apps"""
    for app in APPS:
        app.create_shortcut()


# entry points:

def run_gse_mapviewer():
    """ GSE Mapviewer """
    from larch_plugins.wx import MapViewer
    os.chdir(home_dir)
    MapViewer().MainLoop()
