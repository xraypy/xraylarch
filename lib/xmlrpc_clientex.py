#!/usr/bin/env python

import xmlrpclib
larch = xmlrpclib.ServerProxy('http://localhost:4966')
print larch
print ' Methods: ', larch.system.listMethods()
print larch.system.methodHelp('dir')

print 'list_contents():', larch.dir('/tmp')
# proxy.exit()

