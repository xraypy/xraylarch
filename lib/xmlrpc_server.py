#!/usr/bin/env python
from __future__ import print_function

from six.moves.xmlrpc_server import SimpleXMLRPCServer
import os
import sys
import time
from threading import Timer
import larch
from larch.interpreter import Interpreter
from larch.inputText import InputText
from larch.utils.jsonutils import encode4js

try:
    import wx
    from larch.wxlib import inputhook
    HAS_WX = True
except ImportError:
    HAS_WX = False

class LarchServer(SimpleXMLRPCServer):
    IDLE_TIME = 86400.0
    IDLE_POLL_TIME = 60.0
    def __init__(self, host='127.0.0.1', port=5465, with_wx=True,
                 local_echo=True, quiet=False, **kws):
        self.keep_alive = True
        self.port = port
        self.with_wx = HAS_WX and with_wx
        self.local_echo = local_echo
        self.quiet = quiet
        self.out_buffer = []
        self.keep_alive_time = time.time() + self.IDLE_TIME
        SimpleXMLRPCServer.__init__(self, (host, port),
                                    logRequests=False, allow_none=True, **kws)
        self.initialized = False
        self.register_introspection_functions()
        self.register_function(self.list_dir,      'ls')
        self.register_function(self.change_dir,    'chdir')
        self.register_function(self.current_dir,   'cwd')
        self.register_function(self.exit,          'exit')
        self.register_function(self.larch_exec,    'larch')
        self.register_function(self.get_data,      'get_data')
        self.register_function(self.get_messages,  'get_messages')
        self.register_function(self.len_messages,  'len_messages')
        if self.with_wx:
            self.register_function(self.wx_update,     'wx_update')

    def write(self, text, **kws):
        self.out_buffer.append(text)
        if self.local_echo:
            sys.stdout.write(text)

    def flush(self):
        if self.local_echo:
            sys.stdout.flush()

    def get_messages(self):
        if self.local_echo:
            print( '== clear output buffer (%i)' % len(self.out_buffer))
        out = "".join(self.out_buffer)
        self.out_buffer = []
        return out

    def len_messages(self):
        return len(self.out_buffer)

    def check_activity(self):
        if (time.time() > self.keep_alive_time) or not self.keep_alive:
            sys.exit()
        else:
            self.timer = Timer(self.IDLE_POLL_TIME, self.check_activity)
            self.timer.start()

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
        if not self.quiet:
            print( 'Serving Larch at port %s' % repr(self.port))
            # print dir(self)
            print('Registered Functions:')
            fnames = ['ls', 'chdir', 'cwd', 'exit', 'larch', 'get_data']
            if self.with_wx:
                fnames.append('wx_update')
            for kname in self.funcs.keys():
                if not kname.startswith('system') and kname not in fnames:
                    fnames.append(kname)

            out = ''
            for fname in sorted(fnames):
                if len(out) == 0:
                    out = fname
                else:
                    out = "%s, %s" % (out, fname)
                if len(out) > 70:
                    print("  %s" % out)
                    out = ''
            if len(out) >  0:
                print("  %s" % out)


    def exit(self, **kws):
        "shutdown LarchServer"
        self.keep_alive = False
        return self.server_close()

    def initialize_larch(self):
        self.larch  = Interpreter(writer=self)
        self.input  = InputText(prompt='', _larch=self.larch)
        self.larch.symtable.set_symbol('_sys.color_exceptions', False)
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
        self.initialized = True

    def wx_update(self, timeout):
        "allow wx widgets to update until timeout expires"
        if self.wx_evtloop is not None:
            t0 = time.time()
            while time.time() - t0 < timeout:
                self.larch.symtable.set_symbol('_sys.wx.force_wxupdate', True)
                self.wx_evtloop.run(poll_time=5)
        return True

    def get_data(self, expr):
        "return json encoded data for a larch expression"
        self.keep_alive_time = time.time() + self.IDLE_TIME
        return encode4js(self.larch.eval(expr))

    def larch_exec(self, text, debug=True):
        "execute larch command"
        self.debug = debug
        if not self.initialized:
            self.initialize_larch()
        text = text.strip()
        complete = True
        if text in ('quit', 'exit', 'EOF'):
            self.exit()
        else:
            ret = None
            self.keep_alive_time = time.time() + self.IDLE_TIME
            self.input.put(text, lineno=0)
            complete = self.input.complete
            if complete:
                complete = self.input.run()
            self.flush()
        return 1

if __name__ == '__main__':
    s = LarchServer(host='localhost', port=4966)
    s.run()
