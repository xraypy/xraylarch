#!/usr/bin/env python
from SimpleXMLRPCServer import SimpleXMLRPCServer
import os
import socket

class LarchServer(SimpleXMLRPCServer):
    def __init__(self, hostport=None, **kws):
        self.keep_alive = True
        if hostport is None:
            hostport = ('localhost', 7112)

        SimpleXMLRPCServer.__init__(self, hostport)

    def serve_forever(self):
        while self.keep_alive:
	    self.handle_request()

# Expose a function with an alternate name
def list_contents(dir_name):
    return os.listdir(dir_name)

def exit(app=None, **kw):
    server.keep_alive = False
    return 1

server = LarchServer()
server.register_function(list_contents, 'dir')
server.register_function(exit, 'exit')

try:
    server.serve_forever()
except KeyboardInterrupt:
    print 'ctrl-c Exiting'
print 'done.'

