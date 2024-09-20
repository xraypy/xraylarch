"""
main Larch Applications
"""
import sys
import locale
import inspect
import shutil
from argparse import ArgumentParser
from  pathlib import Path

import matplotlib
from pyshortcuts import make_shortcut, ico_ext, get_desktop

from .site_config import icondir, uname, update_larch
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
            matplotlib.use('WXAgg', force=True)
        except ImportError:
            pass

def set_locale():
    """set locale to 'C' for these applications"""
    locale.setlocale(locale.LC_ALL, 'C')

class LarchApp(object):
    """wrapper for Larh application"""
    def __init__(self, name, script, icon=None, description=None,
                 is_wxapp=True, filetype=None):
        self.name = name
        self.script = script
        self.is_wxapp = is_wxapp
        self.description = description or name
        self.icon = icon or 'larch'
        self.filetype = filetype or 'data file'

    def make_desktop_shortcut(self, folder='Larch'):
        """make (or remake) desktop shortcuts for Larch apps"""
        bindir = 'Scripts' if uname == 'win' else 'bin'
        bindir = Path(sys.prefix, bindir).absolute()
        script = self.script
        if not self.script.startswith('_'):
            script = Path(bindir, self.script).absolute().as_posix()

        icon = Path(icondir, self.icon).absolute()
        if isinstance(ico_ext, (list, tuple)):
            for ext in ico_ext:
                ticon = Path(f"{self.icon:s}.{ext:s}").absolute()
                if ticon.exists():
                    icon = ticon
        make_shortcut(script, name=self.name, folder=folder,
                      icon=icon.as_posix(),
                      description=self.description,
                      terminal=(not self.is_wxapp))


    def prep_cli(self):
        parser = ArgumentParser(description=self.description)
        parser.add_argument('filename', nargs='?',  help=self.filetype)

        parser.add_argument('-m', '-mode', dest='run_mode', action='store_true',
                            default='xas', help='set startup mode')
        parser.add_argument('-w', '-wx_inspect', dest='wx_inspect', action='store_true',
                            default=False, help='enable wxPython inspection and debugging')

        args = parser.parse_args()
        self.filename = None
        if 'filename' in args and args.filename is not None:
            self.filename = Path(args.filename).absolute()
        self.wx_inspect = args.wx_inspect
        self.run_mode = args.run_mode
        if self.is_wxapp:
            set_locale()
            use_mpl_wxagg()


# #             App Name,       icon,        terminal,  Script / pyshortcuts command, Description
# MainApps = (('Larch CLI',     'larch',       True,  'larch', 'Basic Command-line interface for Larch'),
#             ('Larch Updater', 'larch',       True,  '_ -m pip install --upgrade xraylarch', 'Larch Updatar'),
#             ('Larch GUI',     'larch',       False, 'larch --wxgui', 'Enhanced Command-line interface for Larch'),
#             ('XAS Viewer',    'onecone',     False, 'larix', 'XANES and EXAFS Analysis GUI for Larch'),
#             ('Larix',         'onecone',     False, 'larix', 'XANES and EXAFS Analysis GUI for Larch'),
#             ('GSE MapViewer', 'gse_xrfmap',  False, 'gse_mapviewer', 'XRF Map Viewing and Analysis'),
#             ('XRF Viewer',    'ptable',      False, 'larch_xrf', 'X-ray FluorescenceData Viewing and Analysis'),
#             ('XRD1D Viewer',  'larch',       False, 'larch_xrd1d', 'X-ray Diffraction Data Viewing'),
#             )
#


LarchApps = {
    'larch': LarchApp(name='Larch CLI', script='larch', icon='larch',
                      description='Basic Command-line interface for Larch'),
    'Larch GUI': LarchApp(name='Larch GUI', script='larch --wxgui', icon='larch',
                      description='Enhanced Command-line interface for Larch'),
    'Larch Updater': LarchApp(name='Update Larch',
                              script='_ -m pip install --upgrade xraylarch',
                              icon='larch',
                              description='Larch Updater', is_wxapp=False),

    'Larix': LarchApp(name='Larix', script='larix', icon='onecone',
                      description='XANES and EXAFS Analysis GUI for Larch'),
    'XRFMap Viewer': LarchApp(name='XRFMap Viewer', script='gse_mapviewer',
                              icon='gse_xrfmap', filetype='XRM Map File (.h5)',
                              description='XRFMap Viewing and Analysis'),
    'XRF Viewer': LarchApp(name='XRF Viewer', script='larch_xrf', icon='ptable',
                           description='X-ray FluorescenceData Viewing and Analysis'),
    'XRD1D Viewer': LarchApp(name='XRD1D Viewer', script='larch_xrd1d', icon='larch',
                             description='X-ray Diffraction Data Viewing'),
    }


# entry points:
def run_gse_mapviewer():
    "XRFMap Viewer"
    app = LarchApps['XRFMap Viewer']
    app.prep_cli()
    from .wxmap import MapViewer
    MapViewer(check_version=True, title=app.description,
              filename=app.filename).MainLoop()


def run_larix():
    """XANES and EXAFS Analysis GUI for Larch"""
    app = LarchApps['Larix']
    app.prep_cli()
    from .wxxas import LarixApp
    LarixApp(check_version=True, filename=app.filename,
             mode=app.run_mode, with_wx_inspect=app.wx_inspect).MainLoop()

run_xas_viewer = run_larix

def run_larch_xrf():
    """X-ray FluorescenceData Viewing and Analysis"""
    app = LarchApps['XRF Viewer']
    app.prep_cli()
    from .wxlib.xrfdisplay import XRFApp
    XRFApp(filename=app.filename).MainLoop()

def run_epics_xrf():
    """XRF Viewing and Control for Epics XRF Detectors"""
    app = LarchApps['XRF Viewer']
    app.prep_cli()
    try:
        from .epics import EpicsXRFApp
        EpicsXRFApp().MainLoop()
    except ImportError:
        print('cannot import EpicsXRFApp: try `pip install "xraylarch[epics]"`')

def run_larch_xrd1d():
    """X-ray Diffraction Data Display"""
    app = LarchApps['XRD1D Viewer']
    app.prep_cli()
    from .wxxrd import XRD1DApp
    XRD1DApp().MainLoop()

def run_xrd2d_viewer():
    """XRD Display for 2D patternss"""
    set_locale()
    use_mpl_wxagg()
    from .wxxrd import XRD2DViewer
    XRD2DViewer().MainLoop()

def run_gse_dtcorrect():
    """GSE DT Correct """
    set_locale()
    use_mpl_wxagg()
    from .wxmap import DTViewer
    DTViewer().MainLoop()


def run_feff6l():
    "run feff6l"
    from .xafs.feffrunner import feff6l_cli
    feff6l_cli()

def run_feff8l():
    "run feff8l"
    from .xafs.feffrunner import feff8l_cli
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
    parser = ArgumentParser(description='run main larch program')
    sargs = (("-v", "--version", "version", False, "show version"),
             ("-e", "--exec", "noshell", False, "execute script only"),
             ("-q", "--quiet", "quiet", False, "set quiet mode"),
             ("-x", "--nowx", "nowx", False, "set no wx graphics mode"),
             ("-w", "--wxgui", "wxgui", False, "run Larch GUI"),
             ("-m", "--makeicons", "makeicons", False, "create desktop icons"),
             ("-u", "--update", "update", False, "update larch to the latest version"),
             ("-r", "--remote", "server_mode", False, "run in remote server mode"),
             ("-p", "--port", "port", "4966", "port number for remote server"))

    for opt, longopt, dest, default, help in sargs:
        parser.add_argument(opt, longopt, dest=dest, action='store_true',
                            default=default, help=help)

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
        larchdir = Path(get_desktop(), 'Larch').absolute()
        if Path(larchdir).exists():
            shutil.rmtree(larchdir)

        for n, app in LarchApps.items():
            app.make_desktop_shortcut()
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
        from .xmlrpc_server import LarchServer
        server = LarchServer(host='localhost', port=int(args.port))
        server.run()

    # run wx Larch GUI
    elif args.wxgui:
        set_locale()
        use_mpl_wxagg()
        from .wxlib.larchframe import LarchApp
        LarchApp(with_inspection=True).MainLoop()

    # run wx Larch CLI
    else:
        if with_wx:
            set_locale()
            use_mpl_wxagg()
        vinfo = check_larchversion()
        if vinfo.update_available:
            print(vinfo.message)

        from .shell import Shell
        cli = Shell(quiet=args.quiet, with_wx=with_wx)
        # execute scripts listed on command-line
        if args.scripts is not None:
            for script in args.scripts:
                if script.endswith('.py'):
                    cmd = f"import {script[:-3]}"
                else:
                    cmd = f"run('{script}')"
                cli.default(cmd)
        # if interactive, start command loop
        if not args.noshell:
            try:
                cli.cmdloop()
            except ValueError:
                pass
