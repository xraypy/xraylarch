#!/usr/bin/env python
"""
Larch command-line shell
"""
import cmd
import os
import sys
import signal
from .interpreter import Interpreter

from .site_config import history_file
from .version import make_banner
from .larchlib import StdWriter
from .utils import uname

HAS_READLINE = False
try:
    import readline
    HAS_READLINE = True
except ImportError:
    pass

HAS_WXPYTHON = False
try:
    import wx
    HAS_WXPYTHON = True
except ImportError:
    wx = None


class Shell(cmd.Cmd):
    """command shell for Larch"""
    def __init__(self,  completekey='tab', debug=False, quiet=False,
                 stdin=None, stdout=None, banner_msg=None,
                 maxhist=25000, with_wx=False):

        self.debug  = debug
        cmd.Cmd.__init__(self,completekey='tab')
        if stdin is not None:
            sys.stdin = stdin
        if stdout is not None:
            sys.stdout = stdout
        self.stdin = sys.stdin
        self.stdout = sys.stdout

        if HAS_READLINE:
            try:
                readline.read_history_file(history_file)
            except IOError:
                print(f'could not read history from {history_file}')


        self.larch = Interpreter(historyfile=history_file,
                                 maxhistory=maxhist)
        self.larch.writer = StdWriter(_larch=self.larch)

        if with_wx and HAS_WXPYTHON:
            symtable = self.larch.symtable
            try:
                from .wxlib import LarchWxApp
                app = LarchWxApp(redirect=False, clearSigInt=False)
            except SystemExit:
                with_wx = False

            symtable.set_symbol('_sys.wx.wxapp', app)
            symtable.set_symbol('_sys.wx.force_wxupdate', False)
            symtable.set_symbol('_sys.wx.parent', None)

            from .wxlib import inputhook
            symtable.set_symbol('_sys.wx.inputhook', inputhook)
            if uname == 'darwin':
                symtable.set_symbol('_sys.wx.ping',   inputhook.ping_darwin)
            else:
                symtable.set_symbol('_sys.wx.ping',   inputhook.ping)

            inputhook.ON_INTERRUPT = self.onCtrlC
            inputhook.WXLARCH_SYM = symtable

        signal.signal(signal.SIGINT, self.onCtrlC)
        self.prompt = self.larch.input.prompt
        writer = self.larch.writer
        self.color_writer = (uname != 'win' and hasattr(writer, 'set_textstyle'))
        if not quiet:
            if banner_msg is None:
                banner_msg = make_banner(show_libraries=['numpy', 'scipy', 'matplotlib', 'h5py',
                                                         'lmfit', 'xraydb', 'wx','wxmplot'])
            if self.color_writer:
                writer.set_textstyle('error')
            writer.write(banner_msg)
            writer.write("\n")
            if self.color_writer:
                writer.set_textstyle('text')

        self.larch_execute = self.default
        self.larch.run_init_scripts()

    def onCtrlC(self, *args, **kws):
        self.larch.symtable.set_symbol('_sys.wx.keyboard_interrupt', True)
        return 0

    def on_exit(self, text=None):
        "exit"
        trim_last = False
        if text is not None:
            trim_last = text.strip() in ('quit', 'exit')
        try:
            self.larch.input.history.save(trim_last=trim_last)
        except PermissionError:
            print("Warning: could not save session history -- permission denied")
        self.larch.symtable._plotter.close_all_displays()
        sys.exit()

    def do_exit(self, text):
        "exit"
        self.on_exit(text=text)

    def do_quit(self, text):
        "quit"
        self.on_exit(text=text)

    def emptyline(self):
        pass

    def onecmd(self, line):
        "single command"
        return self.default(line)

    def do_help(self, arg):
        "help"
        if arg.startswith('(') and arg.endswith(')'):
            arg = arg[1:-1]
        elif arg.startswith("'") and arg.endswith("'"):
            arg = arg[1:-1]
        elif arg.startswith('"') and arg.endswith('"'):
            arg = arg[1:-1]
        self.default(f"help({arg})")

    def do_shell(self, txt):
        "shell command"
        os.system(txt)

    def default(self, line):
        "default handler"
        if line.strip() in ('quit', 'exit', 'quit()', 'exit()', 'EOF'):
            self.on_exit(line)
        ret = self.larch.eval(line, fname='<stdin>', lineno=0)
        if self.larch.error:
            self.larch.input.clear()
            if self.color_writer:
                self.larch.writer.set_textstyle('error')
            self.larch.show_errors()
            if self.color_writer:
                self.larch.writer.set_textstyle('line')
        if ret is not None:
            self.larch.writer.write("%s\n" % repr(ret))

        self.larch.writer.flush()
        self.prompt = self.larch.input.next_prompt
