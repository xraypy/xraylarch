import time

def _test(larch=None, **kws):
    print 'This was a test plugin: ', time.ctime()

def registerLarchPlugin():
    return ('_shell', {'test': _test})

