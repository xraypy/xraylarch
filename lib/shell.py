#!/usr/bin/env python

import cmd
import os
import sys
import numpy
import larch
from .interpreter import Interpreter
from .site_config import history_file, show_site_config
from .version import __version__, __date__, make_banner
from .inputText import InputText

try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False

class shell(cmd.Cmd):
    ps1    = "larch> "
    ps2    = ".....> "
    def __init__(self,  completekey='tab', debug=False, quiet=False,
                 stdin=None, stdout=None, banner_msg=None, maxhist=5000):
        self.maxhist = maxhist
        self.debug  = debug
        cmd.Cmd.__init__(self,completekey='tab')
        homedir = os.environ.get('HOME', os.getcwd())

        self.history_written = False
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
        self.larch  = Interpreter()
        self.input  = InputText(_larch=self.larch)
        self.prompt = self.ps1
        self.buffer = []

        writer = self.larch.writer
        if not quiet:
            writer.write(banner_msg, color='red', bold=True)
            writer.write("\n")

        self.larch.run_init_scripts()
        self.termcolor_opts = self.larch.symtable._builtin.get_termcolor_opts

    def __del__(self, *args):
        self._write_history()

    def _write_history(self):
        if HAS_READLINE:
            try:
                readline.set_history_length(self.maxhist)
                if history_file is not None and not self.history_written:
                    readline.write_history_file(history_file)
            except:
                pass

    def emptyline(self):
        pass

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
        txt = text.strip()
        write = self.larch.writer.write

        if txt in ('quit', 'exit', 'EOF'):
            if HAS_READLINE:
                try:
                    n = readline.get_current_history_length()
                    readline.remove_history_item(n-1)
                except:
                    pass
                self._write_history()
                self.history_written = True
            return True

        self.input.put(text)
        self.prompt, self.buffer = self.input.run(buffer=self.buffer)

        old = """
        while len(self.input) > 0:
            block, fname, lineno = self.input.get()
            self.buffer.append(block)
            if not self.input.complete:
                continue

            ret = self.larch.eval('\n'.join(self.buffer),
                                  fname=fname, lineno=lineno)
            self.prompt = self.ps1
            self.buffer = []
            if self.larch.error:
                self.input.clear()
                eopts = self.termcolor_opts('error', _larch=self.larch)
                err = self.larch.error.pop(0)
                if err.fname is not None:
                    fname = err.fname
                    if err.lineno is not None:
                        lineno = err.lineno
                if err.tback is not None:
                    write(err.tback, **eopts)
                if self.debug:
                    for err in self.larch.error:
                        write("%s\n" % (err.get_error()[1]), **eopts)
                thiserr = err.get_error(fname=fname, lineno=lineno)
                write("%s\n" % thiserr[1], **eopts)
                break
            elif ret is not None:
                wopts = self.termcolor_opts('text', _larch=self.larch)
                write("%s\n" % repr(ret), **wopts)

        self.larch.writer.flush()
        """

if __name__ == '__main__':
    t = shell(debug=True).cmdloop()
