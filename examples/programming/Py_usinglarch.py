from numpy import linspace, sin, exp
import sys
import pylab
import larch

# set Python path so that larch plugins can be found
sys.path.append(larch.plugin_path('xafs'))
import xafsft

k = linspace(0, 20, 401)
chi = sin(4.2*k)*exp(-k*k/150)*exp(-(k-10)**2/50)

# need to have an larch interpreter for most functions
mylarch = larch.Interpreter()

# create an empty group
out = larch.Group()

# forward transform
xafsft.xftf(k, chi, kmin=2, kmax=15, dk=3, kweight=4,
            _larch=mylarch, group=out)

pylab.plot(out.r, out.chir_mag)
pylab.show()
