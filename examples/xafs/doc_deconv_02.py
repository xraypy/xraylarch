#!/usr/bin/env python
## examples/xafs/doc_deconv_02.py

import numpy as np
from pathlib import Path
from larch import Group
from larch.io import read_ascii
from xraydb import core_width
from larch.xafs import (autobk, pre_edge,
                        xas_deconvolve, xas_convolve )
from larch.plot.wxmplot_xafsplots import plot_mu, plot

filename = Path('..', 'xafsdata', 'cu_metal_rt.xdi')
dat = read_ascii(filename, labels='energy i0 i1 mu_o')
dat.mu = -np.log(dat.i1 / dat.i0)

pre_edge(dat)

esigma = core_width('Cu', edge='K')

xas_deconvolve(dat, esigma=esigma)

plot_mu(dat, show_norm=True, emin=-50, emax=250)
plot(dat.energy, dat.deconv, label='deconvolved')

# Test convolution:
test = Group(energy=dat.energy, norm=dat.deconv)
xas_convolve(test, esigma=esigma)
plot_mu(dat, show_norm=True, emin=-50, emax=250, win=2)
plot(test.energy, dat.norm, label='original', win=2)
plot(test.energy, 100*(test.conv-dat.norm),
     label='(reconvolved - original)x100', win=2)
