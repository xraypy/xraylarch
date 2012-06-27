#!/usr/bin/env python

import xmlrpclib
import time
import json
from larch.utils.jsonutils import json_decode
s = xmlrpclib.ServerProxy('http://127.0.0.1:4966')
print ' Methods: ', s.system.listMethods()
print s.system.methodHelp('dir')


s.larch('m = 222.3')

s.larch('g = group(x=linspace(0, 10, 11))')
s.larch('g.z = cos(g.x)')
s.larch('show(g)')
s.larch('print g.z[3:10]')
# s.larch('newplot(g.x, g.z)')
# s.wx_interact(10.2)
# 
# print ' All done! '
# 
s.larch('show(g)')
# 
gx  = json_decode(s.get_data('g.z'))
print 'm = ', s.get_data('m')
print 'x = ', s.get_data('x')
 
print 'gx = ',  gx, type(gx), gx.dtype
# 

s.exit()


