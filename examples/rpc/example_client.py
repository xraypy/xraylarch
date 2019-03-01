#!/usr/bin/env python
from six.moves.xmlrpc_client import ServerProxy

import time
import json
from larch.utils.jsonutils import decode4js
s = ServerProxy('http://127.0.0.1:4966')

print('Avaialable Methods from XML-RPC server: ', s.system.listMethods())
s.larch('m = 222.3')

s.larch('g = group(x=linspace(0, 10, 11))')
s.larch('g.z = cos(g.x)')

# show and print will be done in server process of course!!!
s.larch('show(g)')

s.larch('print( g.z[3:10])')

print( '== Messages:')
print( s.get_messages())
print( '==')


gx  = decode4js(s.get_data('g.z'))
print( 'm = ', s.get_data('m'))
print( 'x = ', s.get_data('x'))

print('gx = ',  gx, type(gx), gx.dtype)

# could tell server to exit!
# s.exit()
