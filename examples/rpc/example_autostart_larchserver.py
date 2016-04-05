#!/usr/bin/env python
"""
This example automatically starts a larch server
"""
import os
import subprocess
import xmlrpclib
import time
import json
from larch.utils.jsonutils import json_decode

def server_start(port=4966):
    """spawn a subprocess, 'larch -r -p PORT'"""
    return subprocess.Popen(['larch', '-r', '-p', '%i' % port])

def server_connect(port=4966):
    """connect to larch server on PORT of localhost.
    May start a new server if needed.

    Returns server object
    """
    try:
        server = xmlrpclib.ServerProxy('http://127.0.0.1:%i' % port)
        methods = server.system.listMethods()
    except:
        print( 'server not found, trying to create new server process....')
        server_start()
        time.sleep(1)
        methods = None
    if methods is None:
        server = xmlrpclib.ServerProxy('http://127.0.0.1:%i' % port)
        methods = server.system.listMethods()
    return server

server = server_connect()

## Mapping / Dictionary / Hash
adict = server.get_data('adict')
if adict is None:  # that is, 'adict' is not found in larch session
    server.larch('adict = {"a": 1, "b": 2, "c": 3}')

print( 'adict (raw val return from get_data) = ', server.get_data('adict'))
print( 'adict (decoded dictionary): = ', json_decode(server.get_data('adict')))

## Array Data
arr = server.get_data('arr')
if arr is None:  # that is, 'arr' is not found in larch session
    server.larch('arr = linspace(0, 1, 11)')

print( 'arr (raw val return from get_data) = ', server.get_data('arr'))
print( 'arr (decoded array): = ', json_decode(server.get_data('arr')))
