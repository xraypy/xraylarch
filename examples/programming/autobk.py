#!/usr/bin/env python

## Autobk (XAFS background subtraction) in pure Python,
## using Python code from Lxsarch.
from larch import Interpreter

from larch_plugins.xafs import pre_edge, autobk
from larch_plugins.io import read_ascii

# create plain interpreter, don't load all the plugins
_larch = Interpreter(with_plugins=False)

fname = '../xafsdata/cu_rt01.xmu'

cu = read_ascii(fname, labels='energy mu i0', _larch=_larch)
print( 'Read ASCII File:', cu)
print( dir(cu))

pre_edge(cu, _larch=_larch)
print( 'After pre-edge:')
print( dir(cu))

autobk(cu, rbkg=1.0, kweight=1, _larch=_larch)

print( 'After autobk:')
print( dir(cu))
