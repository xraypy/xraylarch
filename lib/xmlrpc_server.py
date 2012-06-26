#!/usr/bin/env python
from SimpleXMLRPCServer import SimpleXMLRPCServer
import os
import sys

import larch
from larch.interpreter import Interpreter
from larch.inputText import InputText

try:
    from larch.wxlib import inputhook
    HAS_WX = True
except ImportError:
    HAS_WX = False

class LarchServer(SimpleXMLRPCServer):
    def __init__(self, host='localhost', port=5465, with_wx=True,**kws):
        self.keep_alive = True
        self.host = host
        self.port = port
        self.with_wx = HAS_WX and with_wx
        SimpleXMLRPCServer.__init__(self, (host, port), **kws)
        self.register_introspection_functions()

        self.register_function(self.list_contents, 'dir')
        self.register_function(self.exit, 'exit')
        self.register_function(self.larch_exec, 'larch')

    def run(self):
        """run server until keep_alive is set to False"""
        print 'Serving at port ' , self.port
        try:
            while self.keep_alive:
                self.handle_request()
        except KeyboardInterrupt:
            sys.exit()

    def list_contents(self, dir_name):
        """list contents of a directory: """
        return os.listdir(dir_name)

    def exit(self, app=None, **kws):
        "shutdown LarchServer"
        self.keep_alive = False
        return 1

    def initialize_larch():
        self.larch  = Interpreter()
        self.input  = InputText(prompt=self.ps1, _larch=self.larch)
        self.larch.run_init_scripts()
        if self.with_wx:
            self.larch.symtable.set_symbol('_sys.wx.inputhook', inputhook)
            self.larch.symtable.set_symbol('_sys.wx.force_wxupdate', False)
            # app = wx.App(redirect=False, clearSigInt=False)
            # self.larch.symtable.set_symbol('_sys.wx.wxapp', app) # app.GetTopWindow())
            # self.larch.symtable.set_symbol('_sys.wx.parent',None)
            inputhook.ON_INTERRUPT = onCtrlC
            inputhook.WXLARCH_SYM = self.larch.symtable
        print 'Larch Initialized ! ', self.with_wx

    def larch_exec(self, text):
        "execute larch command"
        text = text.strip()
        if text in ('quit', 'exit', 'EOF'):
            self.exit()
        else:
            ret = None
            self.input.put(text, lineno=0)
            while len(self.input) > 0:
                block, fname, lineno = self.input.get()
                if len(block) == 0:
                    continue
                ret = self.larch.eval(block, fname=fname, lineno=lineno)
                if self.larch.error:
                    err = self.larch.error.pop(0)
                    fname, lineno = err.fname, err.lineno
                    sys.stdout.write("%s\n" % err.get_error()[1])
                    for err in self.larch.error:
                        if self.debug or ((err.fname != fname or err.lineno != lineno)
                                     and err.lineno > 0 and lineno > 0):
                            sys.stdout.write("%s\n" % (err.get_error()[1]))
                    self.input.clear()
                    break
                elif ret is not None:
                    sys.stdout.write("%s\n" % repr(ret))

if __name__ == '__main__':
    s = LarchServer(host='localhost', port=4966)
    s.run()

