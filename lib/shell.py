#!/usr/bin/env python

import cmd
import os
import sys
import numpy
import matplotlib

from .symboltable import SymbolTable
from .interpreter import Interpreter
from .site_config import history_file, show_site_config
from .version import __version__, __date__, make_banner
from .inputText import InputText

HAS_READLINE = False
try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False

HAS_WXPYTHON = False
try:
    import wx
    HAS_WXPYTHON = True
except ImportError:
    HAS_WXPYTHON = False


class shell(cmd.Cmd):
    ps1    = "larch> "
    ps2    = ".....> "
    def __init__(self,  completekey='tab', debug=False, quiet=False,
                 stdin=None, stdout=None, banner_msg=None,
                 maxhist=5000, with_wx=False, with_plugins=True):

        with_wx = HAS_WXPYTHON and with_wx

        self.maxhist = maxhist
        self.debug  = debug
        cmd.Cmd.__init__(self,completekey='tab')
        homedir = os.environ.get('HOME', os.getcwd())

        if HAS_READLINE:
            self.rdline = readline
            try:
                readline.read_history_file(history_file)
            except IOError:
                print('could not read history from %s' % history_file)

        if stdin is not None:
            sys.stdin = stdin
        if stdout is not None:
            sys.stdout = stdout
        self.stdin = sys.stdin
        self.stdout = sys.stdout

        if banner_msg is None:
            banner_msg = make_banner()

        if with_wx:
            matplotlib.use('WXAgg')

        self.larch = Interpreter(with_plugins=with_plugins)

        if with_wx:
            symtable = self.larch.symtable


            app = wx.App(redirect=False, clearSigInt=False)
            symtable.set_symbol('_sys.wx.wxapp', app)
            symtable.set_symbol('_sys.wx.force_wxupdate', False)
            symtable.set_symbol('_sys.wx.parent', None)

            def onCtrlC(*args, **kws): return 0

            from .wxlib import inputhook
            symtable.set_symbol('_sys.wx.inputhook', inputhook)
            symtable.set_symbol('_sys.wx.ping',   inputhook.ping)
            inputhook.ON_INTERRUPT = onCtrlC
            inputhook.WXLARCH_SYM = symtable

        self.input = InputText(_larch=self.larch)
        self.prompt = self.ps1

        if with_wx:
            matplotlib.use('WXAgg')

        writer = self.larch.writer
        if not quiet:
            writer.write(banner_msg, color='red', bold=True)
            writer.write("\n")

        self.larch.run_init_scripts()

    def __del__(self, *args):
        self.write_history()

    def write_history(self, trim_last=False):
        if not HAS_READLINE or history_file is None:
            return
        try:
            readline.set_history_length(self.maxhist)
            if trim_last:
                n = readline.get_current_history_length()
                readline.remove_history_item(n-1)
            readline.write_history_file(history_file)
        except:
            print("Warning: could not write history file")

    def emptyline(self):
        pass

    def onecmd(self, txt):
        return self.default(txt)

    def do_help(self, txt):
        if txt.startswith('(') and txt.endswith(')'):
            txt = txt[1:-1]
        elif txt.startswith("'") and txt.endswith("'"):
            txt = txt[1:-1]
        elif txt.startswith('"') and txt.endswith('"'):
            txt = txt[1:-1]
        self.default("help(%s)" % txt)

    def do_shell(self, txt):
        os.system(txt)

    def do_quit(self, text):
        self.write_history(trim_last=True)
        sys.exit()

    def do_exit(self, text):
        self.write_history(trim_last=True)
        sys.exit()

    def larch_execute(self, text):
        self.default(text)

    def default(self, text):
        if text.strip() in ('quit', 'exit', 'EOF'):
            trim_last = text.strip() in ('quit', 'exit')
            self.write_history(trim_last=trim_last)
            sys.exit()

        self.input.put(text, filename='<stdin>', lineno=0)
        complete = self.input.complete
        if complete:
            complete = self.input.run()
        self.prompt = {True:self.ps1, False:self.ps2}[complete]

if __name__ == '__main__':
    t = shell(debug=True).cmdloop()
