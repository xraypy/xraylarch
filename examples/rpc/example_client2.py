
import os

from six.moves.xmlrpc_client import ServerProxy
lserve = ServerProxy('http://localhost:4966')

# print lserve.system.listMethods()

parent, thisdir = os.path.split(os.path.abspath(os.curdir))

lserve.chdir(os.path.join(parent, 'feffit'))

lserve.larch("run('doc_feffit1.lar')")

print('## Messages: ')
print(lserve.get_messages())
