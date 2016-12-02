#!/usr/bin/env python
from __future__ import print_function

import os
import sys
from time import time, sleep
import signal
import socket
from threading import Thread, Timer
from six.moves.xmlrpc_server import SimpleXMLRPCServer
from six.moves.xmlrpc_client import ServerProxy

from larch import Interpreter, InputText
from larch.utils.jsonutils import encode4js

NOT_IN_USE, CONNECTED, NOT_LARCHSERVER = range(3)
POLL_TIME = 2.0

"""Notes:
   0.  test server with HOST/PORT, report status (CREATED, ALREADY_RUNNING, FAILED).
   1.  prompt to kill a running server on HOST/PORT, preferably giving a 'last used by {APPNAME} with {PROCESS_ID} at {DATETIME}'
   2.  launch server on next unused PORT on HOST, increment by 1 to 100, report status.
   3.  connect to running server on HOST/PORT.
   4.  have each client set a keepalive time (that is, 'die after having no activity for X seconds') for each server (default=3*24*3600.0).
"""

def test_server(host='localhost', port=4966):
    """Test for a Larch server on host and port

    Arguments
      host (str): host name ['localhost']
      port (int): port number [4966]

    Returns
      integer status number:
          0    Not in use.
          1    Connected, valid Larch server
          2    In use, but not a valid Larch server
    """
    server = ServerProxy('http://%s:%d' % (host, port))
    try:
        methods = server.system.listMethods()
    except socket.error:
        return NOT_IN_USE

    # verify that this is a valid larch server
    if len(methods) < 5 or 'larch' not in methods:
        return NOT_LARCHSERVER
    ret = ''
    try:
        ret = server.get_rawdata('_sys.config.user_larchdir')
    except:
        return NOT_LARCHSERVER
    if len(ret) < 1:
        return NOT_LARCHSERVER

    return CONNECTED


def get_next_port(host='localhost', port=4966, nmax=100):
    """Return next available port for a Larch server on host

    Arguments
      host (str): host name ['localhost']
      port (int): starting port number [4966]
      nmax (int): maximum number to try [100]

    Returns
      integer: next unused port number or None in nmax exceeded.
    """
    for i in range(nmax):
        ptest = port + i
        if NOT_IN_USE == test_server(host=host, port=ptest):
            return ptest
    return None

class LarchServer(SimpleXMLRPCServer):
    def __init__(self, host='localhost', port=4966,
                 logRequests=False, allow_none=True,
                 keepalive_time=3*24*3600):
        self.out_buffer = []

        self.larch = Interpreter(writer=self)
        self.input = InputText(prompt='', _larch=self.larch)
        self.larch.run_init_scripts()

        self.larch('_sys.client = group(keepalive_time=%f)' % keepalive_time)
        self.larch('_sys.wx = group(wxapp=None)')
        _sys = self.larch.symtable._sys
        _sys.color_exceptions = False
        _sys.client.last_event = int(time())
        _sys.client.pid_server = int(os.getpid())
        _sys.client.app = 'unknown'
        _sys.client.pid = 0
        _sys.client.user = 'unknown'
        _sys.client.machine = 'unknown'

        self.client = self.larch.symtable._sys.client

        SimpleXMLRPCServer.__init__(self, (host, port),
                                    logRequests=logRequests,
                                    allow_none=allow_none)

        self.register_introspection_functions()
        self.register_function(self.larch_exec, 'larch')

        for method in ('ls', 'chdir', 'cd', 'cwd', 'shutdown',
                        'set_keepalive_time', 'set_client_info',
                        'get_client_info', 'get_data', 'get_rawdata',
                        'get_messages', 'len_messages'):
            self.register_function(getattr(self, method), method)

        # sys.stdout = self
        self.finished = False
        signal.signal(signal.SIGINT, self.signal_handler)
        self.activity_thread = Thread(target=self.check_activity)

    def write(self, text, **kws):
        if text is None:
            text = ''
        self.out_buffer.append(str(text))

    def flush(self):
        pass

    def set_keepalive_time(self, keepalive_time):
        """set keepalive time
        the server will self destruct after keepalive_time of inactivity

        Arguments:
            keepalive_time (number): time in seconds

        """
        self.larch("_sys.client.keepalive_time = %f" % keepalive_time)

    def set_client_info(self, key, value):
        """set client info

        Arguments:
            key (str): category
            value (str): value to use

        Notes:
            the key can actually be any string but include by convention:
               app      application name
               user     user name
               machine  machine name
               pid      process id
        """
        self.larch("_sys.client.%s = '%s'" % (key, value))

    def get_client_info(self):
        """get client info:
        returns json dictionary of client information
        """
        out = {}
        client = self.larch.symtable._sys.client
        for attr in dir(client):
            out[attr] = getattr(client, attr)
        return encode4js(out)

    def get_messages(self):
        """get (and clear) all output messages (say, from "print()")
        """
        out = "".join(self.out_buffer)
        self.out_buffer = []
        return out

    def len_messages(self):
        "length of message buffer"
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

    def signal_handler(self, sig=0, frame=None):
        self.kill()

    def kill(self):
        """handle alarm signal, generated by signal.alarm(t)"""
        sleep(2.0)
        self.shutdown()
        self.server_close()

    def shutdown(self):
        "shutdown LarchServer"
        self.finished = True
        if self.activity_thread.is_alive():
            self.activity_thread.join(POLL_TIME)
        return 1

    def check_activity(self):
        while not self.finished:
            sleep(POLL_TIME)
            # print("Tick ", time()- (self.client.keepalive_time + self.client.last_event))
            if time() > (self.client.keepalive_time + self.client.last_event):
                t = Thread(target=self.kill)
                t.start()
                break

    def larch_exec(self, text):
        "execute larch command"
        text = text.strip()
        if text in ('quit', 'exit', 'EOF'):
            self.shutdown()
        else:
            self.input.put(text, lineno=0)
            if self.input.complete:
                self.larch('_sys.client.last_event = %i' % time())
                self.input.run()
            self.flush()
        return 1

    def get_rawdata(self, expr):
        "return non-json encoded data for a larch expression"
        return self.larch.eval(expr)

    def get_data(self, expr):
        "return json encoded data for a larch expression"
        self.larch('_sys.client.last_event = %i' % time())
        return encode4js(self.larch.eval(expr))

    def run(self):
        """run server until times out"""
        self.activity_thread.start()
        while not self.finished:
            try:
                self.handle_request()
            except:
                break

if __name__ == '__main__':
    s = LarchServer(host='localhost', port=4966)
    s.run()
