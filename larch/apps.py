import os
import sys
import numpy
import time
from pyshortcuts import make_shortcut
from pyshortcuts.shortcut import Shortcut

from .site_config import icondir, home_dir, uname
from .shell import shell
from .xmlrpc_server import larch_server_cli

HAS_WXPYTHON = False
try:
    import wx
    HAS_WXPYTHON = True
except ImportError:
    pass

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

def fix_darwin_shebang(script):
    """
    fix anaconda python apps on MacOs to launch with pythonw
    """
    pyapp = os.path.join(sys.prefix, 'python.app', 'Contents', 'MacOS', 'python')
    # strip off any arguments:
    script = script.split(' ', 1)[0]
    if not os.path.exists(script):
        script = os.path.join(sys.exec_prefix, 'bin', script)

    if uname == 'darwin' and os.path.exists(pyapp) and os.path.exists(script):
        with open(script, 'r') as fh:
            try:
                lines = fh.readlines()
            except IOError:
                lines = ['-']

        if len(lines) > 1:
            text = ["#!%s\n" % pyapp]
            text.extend(lines[1:])
            time.sleep(.05)
            with open(script, 'w') as fh:
                fh.write("".join(text))

class LarchApp:
    """
    wrapper for Larch Application
    """
    def __init__(self, name, script, icon='larch', terminal=False):
        self.name = name
        self.script = script
        icon_ext = 'ico'
        if uname == 'darwin':
            icon_ext = 'icns'
        self.icon = "%s.%s" % (icon, icon_ext)
        self.terminal = terminal
        bindir = 'bin'
        if uname == 'win':
            bindir = 'Scripts'

        self.bindir = os.path.join(sys.prefix, bindir)

    def create_shortcut(self):
        script =os.path.join(self.bindir, self.script)
        try:
            scut = Shortcut(script, name=self.name, folder='Larch')
            make_shortcut(script, name=self.name,
                          icon=os.path.join(icondir, self.icon),
                          terminal=self.terminal,
                          folder='Larch')
            if uname == 'linux':
                os.chmod(scut.target, 493)
        except:
            print("Warning: could not create shortcut to ", script)
        if uname == 'darwin':
            try:
                fix_darwin_shebang(script)
            except:
                print("Warning: could not fix Mac exe for ", script)


APPS = (LarchApp('Larch CLI', 'larch', terminal=True),
        LarchApp('Larch GUI', 'larch --wxgui'),
        LarchApp('XAS Viewer',  'xas_viewer',  icon='onecone'),
        LarchApp('GSE Mapviewer', 'gse_mapviewer',  icon='gse_xrfmap'),
        LarchApp('GSE DTCorrect', 'gse_dtcorrect'),
        LarchApp('XRF Display',  'xrfdisplay',  icon='ptable'),
        LarchApp('Dioptas', 'dioptas_larch', icon='dioptas'),
        LarchApp('2D XRD Viewer', 'xrd2d_viewer'),
        LarchApp('1D XRD Viewer', 'xrd1d_viewer') )


def make_desktop_shortcuts():
    """make desktop shortcuts for Larch apps"""
    for app in APPS:
        app.create_shortcut()

# entry points:
def run_gse_mapviewer():
    """GSE Mapviewer """
    use_mpl_wxagg()
    from larch.wxmap import MapViewer
    MapViewer().MainLoop()

def run_gse_dtcorrect():
    """GSE DT Correct """
    use_mpl_wxagg()
    from larch.wxmap import DTViewer
    DTViewer().MainLoop()

def run_xas_viewer():
    """XAS Viewer """
    use_mpl_wxagg()
    from larch.wxxas import XASViewer
    XASViewer().MainLoop()


def run_xrfdisplay():
    """ XRF Display"""
    use_mpl_wxagg()
    from larch.wxlib import XRFApp
    XRFApp().MainLoop()


def run_xrfdisplay_epics():
    """XRF Display for Epics Detectors"""
    use_mpl_wxagg()
    from larch.epics import EpicsXRFApp
    EpicsXRFApp().MainLoop()


def run_xrd1d_viewer():
    """XRD Display for 1D patternss"""
    use_mpl_wxagg()
    from larch.wxxrd import XRD1DViewer
    XRD1DViewer().MainLoop()

def run_xrd2d_viewer():
    """XRD Display for 2D patternss"""
    use_mpl_wxagg()
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
    larch_server_cli()

## main larch cli or wxgui
def run_larch():
    """
    main larch application launcher, running either
    commandline repl program or wxgui
    """
    usage = "usage: %prog [options] file(s)"
    from optparse import OptionParser
    parser = OptionParser(usage=usage, prog="larch",
                          version="larch command-line version 0.2")

    parser.add_option("-e", "--exec", dest="noshell", action="store_true",
                      default=False, help="execute script only, default = False")

    parser.add_option("-q", "--quiet", dest="quiet", action="store_true",
                      default=False, help="set quiet mode, default = False")

    parser.add_option("-x", "--nowx", dest="nowx", action="store_true",
                      default=False, help="set no wx graphics mode, default = False")

    parser.add_option("-w", "--wxgui", dest="wxgui", default=False,
                      action='store_true', help="run Larch GUI")

    parser.add_option("-m", "--makeicons", dest="makeicons", action="store_true",
                      default=False, help="create desktop icons")

    parser.add_option("-r", "--remote", dest="server_mode", action="store_true",
                      default=False, help="run in remote server mode")

    parser.add_option("-p", "--port", dest="port", default='4966',
                      metavar='PORT', help="port number for remote server")

    (options, args) = parser.parse_args()
    with_wx = HAS_WXPYTHON and (not options.nowx)

    # create desktop icons
    if options.makeicons:
        make_desktop_shortcuts()

    # run in server mode
    elif options.server_mode:
        if with_wx:
            use_mpl_wxagg()

        from larch.xmlrpc_server import LarchServer
        server = LarchServer(host='localhost', port=int(options.port))
        server.run()

    # run wx Larch GUI
    elif options.wxgui:
        use_mpl_wxagg()
        from larch.wxlib.larchframe import LarchApp
        LarchApp().MainLoop()

    # run wx Larch CLI
    else:
        if with_wx:
            use_mpl_wxagg()
        cli = shell(quiet=options.quiet, with_wx=with_wx)
        # execute scripts listed on command-line
        if len(args)>0:
            for arg in args:
                cmd = "run('%s')" % arg
                if arg.endswith('.py'):
                    cmd = "import %s" %  arg[:-3]
                cli.default(cmd)

        # if interactive, start command loop
        if not options.noshell:
            try:
                cli.cmdloop()
            except ValueError:
                pass
