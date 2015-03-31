from larch import Interpreter
from larch_plugins.xafs.autobk import autobk
from larch_plugins.io.xdi import read_xdi

mylarch = Interpreter()
dat = read_xdi('../xafsdata/fe3c_rt.xdi', _larch=mylarch)
dat.mu = dat.mutrans
autobk(dat, rbkg=1.0, kweight=2, _larch=mylarch)
