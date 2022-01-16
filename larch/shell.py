#!/usr/bin/env python

import cmd
import os
import sys
import numpy
import matplotlib

from .symboltable import SymbolTable
from .interpreter import Interpreter
from .site_config import history_file, show_site_config
from .version import make_banner
from .inputText import InputText
from .larchlib import StdWriter
from .utils import uname
from .wxlib import LarchWxApp
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


class shell(cmd.Cmd):
    def __init__(self,  completekey='tab', debug=False, quiet=False,
                 stdin=None, stdout=None, banner_msg=None,
                 maxhist=25000, with_wx=False, with_plugins=False):

        self.debug  = debug
        cmd.Cmd.__init__(self,completekey='tab')
        homedir = os.environ.get('HOME', os.getcwd())

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
                print('could not read history from %s' % history_file)

        self.larch = Interpreter(with_plugins=with_plugins,
                                 historyfile=history_file,
                                 maxhistory=maxhist)
        self.larch.writer = StdWriter(_larch=self.larch)

        if with_wx and HAS_WXPYTHON:
            symtable = self.larch.symtable

            app = LarchWxApp(redirect=False, clearSigInt=False)

            symtable.set_symbol('_sys.wx.wxapp', app)
            symtable.set_symbol('_sys.wx.force_wxupdate', False)
            symtable.set_symbol('_sys.wx.parent', None)

            def onCtrlC(*args, **kws): return 0

            from .wxlib import inputhook
            symtable.set_symbol('_sys.wx.inputhook', inputhook)
            symtable.set_symbol('_sys.wx.ping',   inputhook.ping)
            inputhook.ON_INTERRUPT = onCtrlC
            inputhook.WXLARCH_SYM = symtable

        self.prompt = self.larch.input.prompt
        writer = self.larch.writer
        self.color_writer = uname != 'win' and hasattr(writer, 'set_textstyle')
        if not quiet:
            if banner_msg is None:
                banner_msg = make_banner(mods=[wx])
            if self.color_writer:
                writer.set_textstyle('error')
            writer.write(banner_msg)
            writer.write("\n")
            if self.color_writer:
                writer.set_textstyle('text')

        self.larch.run_init_scripts()

    def on_exit(self, text=None):
        trim_last = False
        if text is not None:
            trim_last = text.strip() in ('quit', 'exit')
        try:
            self.larch.input.history.save(trim_last=trim_last)
        except PermissionError:
            print("Warning: could not save session history -- permission denied")
        sys.exit()

    def do_quit(self, text):
        self.on_exit(text=text)

    def do_exit(self, text):
        self.on_exit(text=text)

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

    def larch_execute(self, text):
        self.default(text)

    def default(self, text):
        if text.strip() in ('quit', 'exit', 'quit()', 'exit()', 'EOF'):
            self.on_exit(text)
        ret = self.larch.eval(text, fname='<stdin>', lineno=0)
        if self.larch.error:
            self.larch.input.clear()
            if self.color_writer:
                self.larch.writer.set_textstyle('error')
            self.larch.show_errors()
            if self.color_writer:
                self.larch.writer.set_textstyle('text')
        if ret is not None:
            self.larch.writer.write("%s\n" % repr(ret))

        self.larch.writer.flush()
        self.prompt = self.larch.input.next_prompt

if __name__ == '__main__':
    t = shell(debug=True).cmdloop()
