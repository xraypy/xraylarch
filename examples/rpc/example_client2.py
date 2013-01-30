
import os
import xmlrpclib
lserve = xmlrpclib.ServerProxy('http://localhost:4966')

# print lserve.system.listMethods()

parent, thisdir = os.path.split(os.path.abspath(os.curdir))

lserve.chdir(os.path.join(parent, 'feffit'))

lserve.larch("run('doc_feffit1.lar')")

print '## Messages: '
print lserve.get_messages()

# allow interaction with plots drwan by server, for a while:
i = 0
while i < 400:
    i = i + 1
    lserve.wx_update(0.1)
print ' Done!'
