#!/usr/bin/env python
from __future__ import print_function

import os
import sys
from time import time
from select import error as select_error
from socket import error as socket_error
from threading import Timer
from six.moves.xmlrpc_server import SimpleXMLRPCServer
from larch import Interpreter, InputText
from larch.utils.jsonutils import encode4js

class LarchServer(SimpleXMLRPCServer):
    KEEPALIVE_TIME = 3*24*3600.0
    POLL_TIME = 1.0

    def __init__(self, host='127.0.0.1', port=4966, **kws):
        self.out_buffer = []
        self.keep_alive = True
        self.expiration_time = time() + self.KEEPALIVE_TIME
        self.timer = None
        SimpleXMLRPCServer.__init__(self, (host, port),
                                    logRequests=False,
                                    allow_none=True, **kws)
        for method in  ('ls', 'chdir', 'cd', 'cwd', 'exit', 'larch',
                        'get_data', 'get_messages', 'len_messages'):
            self.register_function(getattr(self, method), method)

        self.larch = Interpreter(writer=self)
        self.input = InputText(prompt='', _larch=self.larch)
        self.larch.symtable.set_symbol('_sys.color_exceptions', False)
        self.larch.run_init_scripts()

    def write(self, text, **kws):
        self.out_buffer.append(text)

    def get_messages(self):
        out = "".join(self.out_buffer)
        self.out_buffer = []
        return out

    def len_messages(self):
        return len(self.out_buffer)

    def ls(self, dir_name):
        """list contents of a directory: """
        return os.listdir(dir_name)

    def chdir(self, dir_name):
        """change directory"""
        return os.chdir(dir_name)

    def cd(self, dir_name):
        """change directory"""
        return os.chdir(dir_name)

    def cwd(self):
        """change directory"""
        ret = os.getcwd()
        if sys.platform == 'win32':
            ret = ret.replace('\\','/')
        return ret

    def exit(self, **kws):
        "shutdown LarchServer"
        try:
            self.timer.stop()
        except AttributeError:
            pass
        self.server_close()
        sys.exit()

    def check_activity(self):
        if not self.keep_alive or time() > self.expiration_time:
            self.exit()
        else:
            self.timer = Timer(self.POLL_TIME, self.check_activity)
            self.timer.start()

    def larch(self, text, **kws):
        "execute larch command"
        text = text.strip()
        self.expiration_time = time() + self.KEEPALIVE_TIME
        if not self.keep_alive or text in ('quit', 'exit', 'EOF'):
            self.exit()
        else:
            self.input.put(text, lineno=0)
            if self.input.complete:
                self.input.run()
            self.flush()
        return 1

    def get_data(self, expr):
        "return json encoded data for a larch expression"
        self.expiration_time = time() + self.KEEPALIVE_TIME
        return encode4js(self.larch.eval(expr))

    def run(self):
        """run server until keep_alive is set to False"""
        self.check_activity()
        try:
            self.serve_forever()
        except (KeyboardInterrupt, select_error, socket_error):
            self.keep_alive = False
            sys.exit()

if __name__ == '__main__':
    s = LarchServer(host='localhost', port=4966)
    s.run()
