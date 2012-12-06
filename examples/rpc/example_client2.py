
import xmlrpclib
lserve = xmlrpclib.ServerProxy('http://localhost:7112')

###print dir(proxy) #.available()
print lserve.system.listMethods()
print lserve.cwd()
lserve.chdir('examples/feffit')
print lserve.cwd()
print lserve.ls('.')
lserve.larch("run('doc_feffit1.lar')")
lserve.larch("run('doc_feffit1.lar')")

# print getattr(proxy, 'dir')
# print 'dir():', proxy.dir('/tmp')

# proxy.exit()
## print 'list_contents():', proxy.list_contents('/tmp')
