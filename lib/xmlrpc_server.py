#!/usr/bin/env python
from SimpleXMLRPCServer import SimpleXMLRPCServer
import os
import sys
import time
import larch
from larch.interpreter import Interpreter
from larch.inputText import InputText
from larch.utils.jsonutils import json_encode

try:
    import wx
    from larch.wxlib import inputhook
    HAS_WX = True
except ImportError:
    HAS_WX = False

class LarchServer(SimpleXMLRPCServer):
    def __init__(self, host='127.0.0.1', port=5465, with_wx=True, **kws):
        self.keep_alive = True
        self.port = port
        self.with_wx = HAS_WX and with_wx
        SimpleXMLRPCServer.__init__(self, (host, port),
                                    logRequests=False, allow_none=True, **kws)
        self.initialized = False
        self.register_introspection_functions()
        self.register_function(self.list_dir,      'ls')
        self.register_function(self.change_dir,    'chdir')
        self.register_function(self.current_dir,   'cwd')
        self.register_function(self.exit,          'exit')
        self.register_function(self.larch_exec,    'larch')
        self.register_function(self.wx_update,     'wx_update')
        self.register_function(self.get_data,      'get_data')

    def run(self):
        """run server until keep_alive is set to False"""
        print( 'Serving Larch at port %s' % repr(self.port))
        self.help()
        try:
            while self.keep_alive:
                self.handle_request()
        except KeyboardInterrupt:
            sys.exit()

    def list_dir(self, dir_name):
        """list contents of a directory: """
        return os.listdir(dir_name)

    def change_dir(self, dir_name):
        """change directory"""
        return os.chdir(dir_name)

    def current_dir(self):
        """change directory"""
        ret = os.getcwd()
        if sys.platform == 'win32':
            ret = ret.replace('\\','/')
        return ret

    def help(self):
        print 'LarchServer: '
        print dir(self)
        print 'Registered Functions:'
        print ('ls', 'chdir', 'cwd', 'exit', 'larch', 'wx_update',  'get_data')
        print self.funcs.keys()

    def exit(self, app=None, **kws):
        "shutdown LarchServer"
        self.keep_alive = False
        return 1

    def initialize_larch(self):
        self.larch  = Interpreter()
        self.input  = InputText(prompt='', _larch=self.larch)
        self.larch.run_init_scripts()
        self.wxapp = None
        self.wx_evtloop = None
        if self.with_wx:
            self.larch.symtable.set_symbol('_sys.wx.inputhook', inputhook)
            self.larch.symtable.set_symbol('_sys.wx.force_wxupdate', False)

            self.wxapp = wx.App(redirect=False, clearSigInt=False)
            self.wx_evtloop = inputhook.EventLoopRunner(parent=self.wxapp)

            self.larch.symtable.set_symbol('_sys.wx.wxapp', self.wxapp)
            # app.GetTopWindow())
            self.larch.symtable.set_symbol('_sys.wx.parent',None)
            inputhook.ON_INTERRUPT = self.exit
            inputhook.WXLARCH_SYM = self.larch.symtable
        print('Larch Initialized!')
        self.initialized = True

    def wx_update(self, timeout):
        "allow wx widgets to update until timeout expires"
        if self.wx_evtloop is not None:
            t0 = time.time()
            while time.time() - t0 < timeout:
                self.larch.symtable.set_symbol('_sys.wx.force_wxupdate', True)
                self.wx_evtloop.run(poll_time=5)
        return True

    def get_data(self, symname):
        "return json encoded data"
        if not self.initialized:
            self.initialize_larch()
        return json_encode(symname, symtable=self.larch.symtable)

    def larch_exec(self, text):
        "execute larch command"
        if not self.initialized:
            self.initialize_larch()
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
        return ret is None

if __name__ == '__main__':
    s = LarchServer(host='localhost', port=4966)
    s.run()

