
import xmlrpclib
lserve = xmlrpclib.ServerProxy('http://localhost:4966')

# print lserve.system.listMethods()
lserve.chdir('/Users/newville/Codes/xraylarch/examples/feffit')
lserve.larch("run('doc_feffit1.lar')")
print '## Messages: '
print lserve.get_messages()

# allow interaction with plots drwan by server, for a while: 
i = 0
while i < 400:
    i = i + 1
    lserve.wx_update(0.1)
print ' Done!'
