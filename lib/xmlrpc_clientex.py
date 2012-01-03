
import xmlrpclib
proxy = xmlrpclib.ServerProxy('http://localhost:7112')
print dir(proxy)
# print getattr(proxy, 'dir')
print 'dir():', proxy.dir('/tmp')

proxy.exit()
## print 'list_contents():', proxy.list_contents('/tmp')
