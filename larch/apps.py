"""
main Larch Applications
"""
import os
import sys
import locale

import shutil
from argparse import ArgumentParser


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
            return True
        except ImportError:
            pass
    return False

def set_locale():
    """set locale to 'C' for these applications,
    may need some improvement!!"""
    locale.setlocale(locale.LC_ALL, 'C')

#             App Name,       icon,        terminal,  Script / pyshortcuts command
MainApps = (('Larch CLI',     'larch',       True,  'larch'),
            ('Larch Updater', 'larch',       True,  '_ -m pip install --upgrade xraylarch'),
            ('Larch GUI',     'larch',       False, 'larch --wxgui'),
            ('XAS Viewer',    'onecone',     False, 'xas_viewer'),
            ('Larix',         'onecone',     False, 'larix'),
            ('GSE MapViewer', 'gse_xrfmap',  False, 'gse_mapviewer'),
            ('XRF Viewer',    'ptable',      False, 'larch_xrf'),
            ('XRD1D Viewer',  'larch',       False, 'larch_xrd1d') )

def make_desktop_shortcuts():
    """make (or remake) desktop shortcuts for Larch apps"""
    larchdir = os.path.join(get_desktop(), 'Larch')
    if os.path.exists(larchdir):
        shutil.rmtree(larchdir)

    bindir = 'Scripts' if uname == 'win' else 'bin'
    bindir = os.path.join(sys.prefix, bindir)
    for appname, icon, term, script in MainApps:
        kwargs = {'folder': 'Larch', 'terminal': term, 'name': appname}
        if not script.startswith('_'):
            script = os.path.normpath(os.path.join(bindir, script))
        icon = os.path.join(icondir, icon)
        if isinstance(ico_ext, (list, tuple)):
            for ext in ico_ext:
                ticon = f"{icon:s}.{ext:s}"
                if os.path.exists(ticon):
                    icon = ticon
        make_shortcut(script, icon=icon, **kwargs)

def make_cli(description='run larch program', filedesc='data file'):
    "make commandline apps"
    parser = ArgumentParser(description=description)
    parser.add_argument('filename', nargs='?',  help=filedesc)
    args = parser.parse_args()
    filename = None
    if 'filename' in args and args.filename is not None:
        filename = os.path.abspath(args.filename)
    return {'filename': filename}

# entry points:
def run_gse_mapviewer():
    """Mapviewer"""
    set_locale()
    use_mpl_wxagg()
    kwargs = make_cli(description="Larch's XRM Map Viewer and Analysis Program",
                      filedesc='XRM Map File (.h5)')
    from .wxmap import MapViewer
    MapViewer(check_version=True, **kwargs).MainLoop()

def run_gse_dtcorrect():
    """GSE DT Correct """
    set_locale()
    use_mpl_wxagg()
    from .wxmap import DTViewer
    DTViewer().MainLoop()

def run_larix():
    """Larix (was XAS Viewer)"""
    set_locale()
    use_mpl_wxagg()
    from .wxxas import XASViewer, LARIX_TITLE
    kwargs = make_cli(description=LARIX_TITLE)
    XASViewer(check_version=True, **kwargs).MainLoop()

run_xas_viewer = run_larix

def run_larch_xrf():
    """ XRF Display"""
    set_locale()
    use_mpl_wxagg()
    kwargs = make_cli(description="Larch's XRF Viewer and Analysis Program",
                    filedesc='MCA File (.mca)')
    from .wxlib.xrfdisplay import XRFApp
    XRFApp(**kwargs).MainLoop()

def run_epics_xrf():
    """XRF Display for Epics Detectors"""
    set_locale()
    use_mpl_wxagg()
    IMPORT_OK = False
    try:
        from .epics import EpicsXRFApp
        IMPORT_OK = True
    except ImportError:
        print("cannot import EpicsXRFApp: try `pip install xraylarch[epics]`")
    if IMPORT_OK:
        EpicsXRFApp().MainLoop()

def run_larch_xrd1d():
    """XRD Display for 1D patternss"""
    set_locale()
    use_mpl_wxagg()
    from .wxxrd import XRD1DApp
    XRD1DApp().MainLoop()

def run_xrd2d_viewer():
    """XRD Display for 2D patternss"""
    set_locale()
    use_mpl_wxagg()
    from .wxxrd import XRD2DViewer
    XRD2DViewer().MainLoop()


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
