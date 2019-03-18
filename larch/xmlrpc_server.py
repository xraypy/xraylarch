#!/usr/bin/env python
from __future__ import print_function

import os
import sys
from time import time, sleep, ctime
import signal
import socket
from subprocess import Popen
from threading import Thread
from optparse import OptionParser
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy

from .interpreter import Interpreter
from .site_config import uname
from .utils.jsonutils import encode4js
from .utils import uname

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

NOT_IN_USE, CONNECTED, NOT_LARCHSERVER = range(3)
POLL_TIME = 0.50

"""Notes:
   0.  test server with HOST/PORT, report status (CREATED, ALREADY_RUNNING, FAILED).
   1.  prompt to kill a running server on HOST/PORT, preferably giving a
       'last used by {APPNAME} with {PROCESS_ID} at {DATETIME}'
   2.  launch server on next unused PORT on HOST, increment by 1 to 100, report status.
   3.  connect to running server on HOST/PORT.
   4.  have each client set a keepalive time (that is,
       'die after having no activity for X seconds') for each server (default=3*24*3600.0).
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
    # special case for localhost:
    # use psutil to find next unused port
    if host.lower() == 'localhost':
        if HAS_PSUTIL and uname == 'win':
            available = [True]*nmax
            try:
                conns = psutil.net_connections()
            except:
                conns = []
            if len(conns) > 0:
                for conn in conns:
                    ptest = conn.laddr[1] - port
                    if ptest >= 0 and ptest < nmax:
                        available[ptest] = False
            for index, status in enumerate(available):
                if status:
                    return port+index
        # now test with brute attempt to open the socket:
        for index in range(nmax):
            ptest = port + index
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            success = False
            try:
                sock.bind(('', ptest))
                success = True
            except socket.error:
                pass
            finally:
                sock.close()
            if success:
                return ptest

    # for remote servers or if the above did not work, need to test ports
    for index in range(nmax):
        ptest = port + index
        if NOT_IN_USE == test_server(host=host, port=ptest):
            return ptest
    return None

class LarchServer(SimpleXMLRPCServer):
    def __init__(self, host='localhost', port=4966,
                 logRequests=False, allow_none=True,
                 keepalive_time=3*24*3600):
        self.out_buffer = []

        self.larch = Interpreter(writer=self)
        self.larch.input.prompt = ''
        self.larch.input.prompt2 = ''
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
        _sys.client.machine = socket.getfqdn()

        self.client = self.larch.symtable._sys.client
        self.port = port
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
        out = {'port': self.port}
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
        if uname == 'win':
            ret = ret.replace('\\','/')
        return ret

    def signal_handler(self, sig=0, frame=None):
        self.kill()

    def kill(self):
        """handle alarm signal, generated by signal.alarm(t)"""
        sleep(POLL_TIME)
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
            ret = self.larch.eval(text, lineno=0)
            if ret is not None:
                self.write(repr(ret))
            self.client.last_event = time()
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

def spawn_server(port=4966, wait=True, timeout=30):
    """
    start a new process for a LarchServer on selected port,
    optionally waiting to confirm connection
    """
    topdir = sys.exec_prefix
    pyexe = os.path.join(topdir, 'bin', 'python')
    bindir = 'bin'
    if uname.startswith('win'):
            bindir = 'Scripts'
            pyexe = pyexe + '.exe'

    args = [pyexe, os.path.join(topdir, bindir, 'larch'),
            '-r', '-p', '%d' % port]
    pipe = Popen(args)
    if wait:
        t0 = time()
        while time() - t0 < timeout:
            sleep(POLL_TIME)
            if CONNECTED == test_server(port=port):
                break
    return pipe


###
def larch_server_cli():
    """command-line program to control larch XMLRPC server"""
    __version__ = 'version 2.2'
    usage = """usage: %prog [options] [start|stop|restart|next|status|report]

Commands:
   start       start server on specified port
   stop        stop server on specified port
   restart     restart server on specified port
   next        start server on next avaialable port (see also '-n' option)
   status      print a short status message: whether server is running on port
   report      print a multi-line status report
"""

    parser = OptionParser(usage=usage, prog="larch_server",
                          version="larch_server: %s" % __version__)
    parser.add_option("-p", "--port", dest="port", default='4966',
                      metavar='PORT', help="port number for server [4966]")
    parser.add_option("-q", "--quiet", dest="quiet", action="store_true",
                      default=False, help="suppress messaages [False]")
    parser.add_option("-n", "--next", dest="next", action="store_true",
                      default=False, help="show next available port, but do not start [False]")

    (options, args) = parser.parse_args()

    port = int(options.port)
    command = 'status'

    def smsg(port, txt):
        if not options.quiet:
            print('larch_server port=%i: %s' % (port, txt))

    if len(args) >  0:
        command = args[0].lower()

    if options.next:
        port = get_next_port(port=port)
        print("%i" % port)
        sys.exit(0)

    server_state = test_server(port=port)

    if command == 'start':
        if server_state == CONNECTED:
            smsg(port, 'already running')
        elif server_state == NOT_IN_USE:
            spawn_server(port=port)
            smsg(port, 'started')
        else:
            smsg(port, 'port is in use, cannot start')

    elif command == 'stop':
        if server_state == CONNECTED:
            ServerProxy('http://localhost:%d' % (port)).shutdown()
            smsg(port, 'stopped')

    elif command == 'next':
        port = get_next_port(port=port)
        spawn_server(port=port)
        smsg(port, 'started')

    elif command == 'restart':
        if server_state == CONNECTED:
            ServerProxy('http://localhost:%d' % (port)).shutdown()
            sleep(POLL_TIME)
        spawn_server(port=port)

    elif command == 'status':
        if server_state == CONNECTED:
            smsg(port, 'running')
            sys.exit(0)
        elif server_state == NOT_IN_USE:
            smsg(port, 'not running')
            sys.exit(1)
        else:
            smsg(port, 'port is in use by non-larch server')
    elif command == 'report':
        if server_state == CONNECTED:
            s = ServerProxy('http://localhost:%d' % (port))
            info = s.get_client_info()
            last_event = info.get('last_event', 0)
            last_used = ctime(last_event)
            serverid  = int(info.get('pid_server', 0))
            serverport= int(info.get('port', 0))
            procid    = int(info.get('pid', 0))
            appname   = info.get('app',     'unknown')
            machname  = info.get('machine', 'unknown')
            username  = info.get('user',    'unknown')
            keepalive_time = info.get('keepalive_time', -1)
            keepalive_time += (last_event - time())
            keepalive_units = 'seconds'
            if keepalive_time > 150:
                keepalive_time = round(keepalive_time/60.0)
                keepalive_units = 'minutes'
            if keepalive_time > 150:
                keepalive_time = round(keepalive_time/60.0)
                keepalive_units = 'hours'

            print('larch_server report:')
            print('   Server Port Number  = %s' % serverport)
            print('   Server Process ID   = %s' % serverid)
            print('   Server Last Used    = %s' % last_used)
            print('   Server will expire in %d %s if not used.' % (keepalive_time,
                                                                 keepalive_units))
            print('   Client Machine Name = %s' % machname)
            print('   Client Process ID   = %s' % str(procid))
            print('   Client Application  = %s' % appname)
            print('   Client User Name    = %s' % username)

        elif server_state == NOT_IN_USE:
            smsg(port, 'not running')
            sys.exit(1)
        else:
            smsg(port, 'port is in use by non-larch server')

    else:
        print("larch_server: unknown command '%s'. Try -h" % command)


if __name__ == '__main__':
    spawn_server(port=4966)
