import numpy as np
import pylab
from larch import Interpreter, Group

# now import larch-specific Python code
from larch_plugins.xafs import autobk, xftf

# create a larch interpreter, passed to most functions
my_larch = Interpreter(with_plugins=False)

# create an empty Group
xafsdat = Group()

# read data (here using np.loadtxt), stick into Group
# using "expected names" for XAFS data
rawdata = np.loadtxt('../xafsdata/fe2o3_rt1.xmu')

xafsdat.energy = rawdata[:, 0]
xafsdat.mu     = rawdata[:, 1]
xafsdat.i0     = rawdata[:, 1]

# run autobk on the xafsdat Group, including a larch Interpreter....
# note that this expects 'energy' and 'mu' to be in xafsdat, and will
# write data for 'k', 'chi', 'kwin', 'e0', ... into xafsdat
autobk(xafsdat, rbkg=1.0, kweight=2, _larch=my_larch)

# Fourier transform to R space, again passing in a Group (here,
# 'k' and 'chi' are expected, and writitng out 'r', 'chir_mag',
# and so on
xftf(xafsdat, kmin=2, kmax=15, dk=3, kweight=2, _larch=my_larch)

#
# plot grid of results:
# mu + bkg
pylab.subplot(2, 2, 1)
pylab.plot(xafsdat.energy, xafsdat.bkg, 'r--')
pylab.plot(xafsdat.energy, xafsdat.mu)
pylab.xlabel('Energy (eV)')

# normalized XANES
# find array bounds for normalized mu(E) for [e0 - 25: e0 + 75]
j0 = np.abs(xafsdat.energy-(xafsdat.e0 - 25.0)).argmin()
j1 = np.abs(xafsdat.energy-(xafsdat.e0 + 75.0)).argmin()

pylab.subplot(2, 2, 2)
pylab.plot(xafsdat.energy[j0:j1], xafsdat.norm[j0:j1])
pylab.xlabel('Energy (eV)')

# chi(k)
pylab.subplot(2, 2, 3)
pylab.plot(xafsdat.k, xafsdat.chi*xafsdat.k**2)
pylab.plot(xafsdat.k, xafsdat.kwin, 'r--')
pylab.xlabel(r'$ k (\AA^{-1}) $')
pylab.ylabel(r'$ k^2 \chi(\AA^{-2}) $')

# chi(R)
pylab.subplot(2, 2, 4)
pylab.plot(xafsdat.r, xafsdat.chir_mag)
pylab.plot(xafsdat.r, xafsdat.chir_re, 'r--')
pylab.xlabel(r'$ R (\AA) $')
pylab.ylabel(r'$ \chi(R) (\AA^{-3}) $')

pylab.show()
