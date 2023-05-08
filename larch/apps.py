import os
import sys
import locale
import numpy
import time

from argparse import ArgumentParser
import pkg_resources
from subprocess import check_call, Popen

import shutil
from argparse import ArgumentParser

from pyshortcuts import make_shortcut, ico_ext, get_desktop
from .site_config import (icondir, home_dir, uname, install_extras,
                          update_larch, extras_wxgraph, extras_qtgraph,
                          extras_epics, extras_doc, extras_plotly)

from .shell import Shell

from .version import __date__, make_banner, check_larchversion

HAS_WXPYTHON = False
try:
    import wx
    HAS_WXPYTHON = True
except ImportError:
    pass

if HAS_WXPYTHON:
    # note: this will be needed for some macOS builds until wxPython 4.2.1 is released.
    if uname == 'darwin':
        wx.PyApp.IsDisplayAvailable = lambda _: True

def use_mpl_wxagg():
    """import matplotlib, set backend to wxAgg"""
    if HAS_WXPYTHON:
        try:
            import matplotlib
            matplotlib.use('WXAgg', force=True)
            return True
        except ImportError:
            pass
    return False

def set_locale():
    """set locale to 'C' for these applications,
    may need some improvement!!"""
    locale.setlocale(locale.LC_ALL, 'C')

class LarchApp:
    """
    wrapper for Larch Application
    """
    def __init__(self, name, script, icon='larch', terminal=False):
        self.name = name
        self.script = script
        self.terminal = terminal
        self.icon = icon
        bindir = 'Scripts' if uname == 'win' else 'bin'
        self.bindir = os.path.join(sys.prefix, bindir)

    def create_shortcut(self):
        if self.script.startswith('_'):
            script = self.script
        else:
            script = os.path.normpath(os.path.join(self.bindir, self.script))

        icon = os.path.join(icondir, self.icon)
        if isinstance(ico_ext, (list, tuple)):
            for ext in ico_ext:
                ticon = "{:s}.{:s}".format(icon, ext)
                if os.path.exists(ticon):
                    icon = ticon
        make_shortcut(script, name=self.name, icon=icon,
                      terminal=self.terminal, folder='Larch')

APPS = (LarchApp('Larch CLI', 'larch', terminal=True),
        LarchApp('Larch GUI', 'larch --wxgui'),
        LarchApp('XAS Viewer',  'xas_viewer',  icon='onecone'),
        LarchApp('GSE MapViewer', 'gse_mapviewer',  icon='gse_xrfmap'),
        LarchApp('XRF Display',  'xrfdisplay',  icon='ptable'),
        # LarchApp('GSE DTCorrect', 'gse_dtcorrect'),
        # LarchApp('Dioptas', 'dioptas_larch', icon='dioptas'),
        # LarchApp('2D XRD Viewer', 'xrd2d_viewer'),
        # LarchApp('1D XRD Viewer', 'xrd1d_viewer')
        )


def make_desktop_shortcuts():
    """make desktop shortcuts for Larch apps,
    first clearing any existing shortcuts"""
    larchdir = os.path.join(get_desktop(), 'Larch')
    if os.path.exists(larchdir):
        shutil.rmtree(larchdir)
    for app in APPS:
        app.create_shortcut()
    updater = LarchApp('Larch Updater',  '_ -m pip install --upgrade xraylarch', terminal=True)
    updater.create_shortcut()



def make_cli(description='run larch program', filedesc='data file'):
    usage = "usage: %prog [options] file"
    parser = ArgumentParser(description=description)
    parser.add_argument('filename', nargs='?',  help=filedesc)
    args = parser.parse_args()
    filename = None
    if 'filename' in args and args.filename is not None:
        filename = os.path.abspath(args.filename)
    return dict(filename=filename)

# entry points:
def run_gse_mapviewer():
    """Mapviewer"""
    set_locale()
    use_mpl_wxagg()
    install_extras(extras_wxgraph)
    install_extras(extras_epics)
    from larch.wxmap import MapViewer
    kwargs = make_cli(description="Larch's XRM Map Viewer and Analysis Program",
                      filedesc='XRM Map File (.h5)')
    MapViewer(check_version=True, **kwargs).MainLoop()

def run_gse_dtcorrect():
    """GSE DT Correct """
    set_locale()
    use_mpl_wxagg()
    install_extras(extras_wxgraph)
    install_extras(extras_epics)
    from larch.wxmap import DTViewer
    DTViewer().MainLoop()

def run_xas_viewer():
    """XAS Viewer """
    set_locale()
    use_mpl_wxagg()
    install_extras(extras_wxgraph)
    from larch.wxxas import XASViewer
    kwargs = make_cli(description="Larch's XAS Viewer and Analysis Program")
    XASViewer(check_version=True, **kwargs).MainLoop()

def run_xrfdisplay():
    """ XRF Display"""
    set_locale()
    use_mpl_wxagg()
    install_extras(extras_wxgraph)
    install_extras(extras_epics)
    from larch.wxlib.xrfdisplay import XRFApp
    kwargs = make_cli(description="Larch's XRF Viewer and Analysis Program",
                    filedesc='MCA File (.mca)')
    XRFApp(**kwargs).MainLoop()

def run_xrfdisplay_epics():
    """XRF Display for Epics Detectors"""
    set_locale()
    use_mpl_wxagg()
    install_extras(extras_wxgraph)
    install_extras(extras_epics)
    from larch.epics import EpicsXRFApp
    EpicsXRFApp().MainLoop()

def run_xrd1d_viewer():
    """XRD Display for 1D patternss"""
    set_locale()
    use_mpl_wxagg()
    from larch.wxxrd import XRD1DViewer
    XRD1DViewer().MainLoop()

def run_xrd2d_viewer():
    """XRD Display for 2D patternss"""
    set_locale()
    use_mpl_wxagg()
    install_extras(extras_wxgraph)
    install_extras(extras_epics)
    from larch.wxxrd import XRD2DViewer
    XRD2DViewer().MainLoop()

def run_dioptas_larch():
    """XRD Display for 2D patternss"""
    from dioptas import main
    main()

def run_feff6l():
    "run feff6l"
    from larch.xafs.feffrunner import feff6l_cli
    feff6l_cli()

def run_feff8l():
    "run feff8l"
    from larch.xafs.feffrunner import feff8l_cli
    feff8l_cli()

def run_larch_server():
    "run larch XMLRPC server"
    from .xmlrpc_server import larch_server_cli
    larch_server_cli()

## main larch cli or wxgui
def run_larch():
    """
    main larch application launcher, running either
    commandline repl program or wxgui
    """
    usage = "usage: %prog [options] file(s)"
    parser = ArgumentParser(description='run main larch program')

    parser.add_argument('-v', '--version', dest='version', action='store_true',
                        default=False, help='show version')

    parser.add_argument("-e", "--exec", dest="noshell", action="store_true",
                        default=False, help="execute script only, default = False")

    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true",
                        default=False, help="set quiet mode, default = False")

    parser.add_argument("-x", "--nowx", dest="nowx", action="store_true",
                        default=False, help="set no wx graphics mode, default = False")

    parser.add_argument("-w", "--wxgui", dest="wxgui", default=False,
                        action='store_true', help="run Larch GUI")

    parser.add_argument("-m", "--makeicons", dest="makeicons", action="store_true",
                        default=False, help="create desktop icons")

    parser.add_argument('-u', '--update', dest='update', action='store_true',
                        default=False, help='update larch to the latest version')

    parser.add_argument("-r", "--remote", dest="server_mode", action="store_true",
                        default=False, help="run in remote server mode")

    parser.add_argument("-p", "--port", dest="port", default='4966',
                        help="port number for remote server")

    parser.add_argument('scripts', nargs='*',
                        help='larch or python scripts to run on startup')

    args = parser.parse_args()
    if args.version:
        print(make_banner(with_libraries=True))
        vinfo = check_larchversion()
        if vinfo.update_available:
            print(vinfo.message)
        return

    with_wx = HAS_WXPYTHON and (not args.nowx)

    # create desktop icons
    if args.makeicons:
        install_extras(extras_wxgraph)
        make_desktop_shortcuts()
        return

    # run updates
    if args.update:
        update_larch()
        return

    # run in server mode
    if args.server_mode:
        if with_wx:
            use_mpl_wxagg()
        vinfo = check_larchversion()
        if vinfo.update_available:
            print(vinfo.message)

        from larch.xmlrpc_server import LarchServer
        server = LarchServer(host='localhost', port=int(args.port))
        server.run()

    # run wx Larch GUI
    elif args.wxgui:
        set_locale()
        use_mpl_wxagg()
        install_extras(extras_wxgraph)
        install_extras(extras_epics)
        from larch.wxlib.larchframe import LarchApp
        LarchApp(with_inspection=True).MainLoop()

    # run wx Larch CLI
    else:
        if with_wx:
            set_locale()
            use_mpl_wxagg()
        try:
            install_extras(extras_wxgraph)
            install_extras(extras_epics)
        except:
            pass
        vinfo = check_larchversion()
        if vinfo.update_available:
            print(vinfo.message)

        cli = Shell(quiet=args.quiet, with_wx=with_wx)
        # execute scripts listed on command-line
        if args.scripts is not None:
            for script in args.scripts:
                if script.endswith('.py'):
                    cmd = "import %s" %  script[:-3]
                else:
                    cmd = "run('%s')" % script
                cli.default(cmd)
        # if interactive, start command loop
        if not args.noshell:
            try:
                cli.cmdloop()
            except ValueError:
                pass
