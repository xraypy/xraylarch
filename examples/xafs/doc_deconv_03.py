#!/usr/bin/env python
## examples/xafs/doc_deconv_03.py

import numpy as np
from pathlib import Path
from larch import Group
from larch.io import read_ascii
from xraydb import core_width
from larch.xafs import pre_edge, autobk, xftf, xas_deconvolve
from larch.plot.wxmplot_xafsplots import plot_mu, plot_chik, plot_chir, plot

filename = Path('..', 'xafsdata', 'pt_metal_rt.xdi')
data = read_ascii(filename, labels='energy time i1 i0')
data.mu = -np.log(data.i1 / data.i0)

pre_edge(data)
autobk(data, rbkg=1.1, kweight=2)
xftf(data, kmin=2, kmax=17, dk=5, window='kaiser', kweight=2)

xas_deconvolve(data, esigma=core_width('Pt', edge='L3'))

decon = Group(energy=data.energy, mu=data.deconv, filename=data.filename)
autobk(decon, rbkg=1.1, kweight=2)
xftf(decon, kmin=2, kmax=17, dk=5, window='kaiser', kweight=2)

# plot in E
plot_mu(data, show_norm=True, emin=-50, emax=250)
plot(data.energy, data.deconv, label='deconvolved', win=1)

# plot in k
plot_chik(data, kweight=2, show_window=False, win=2)
plot_chik(decon, kweight=2, show_window=False, label='deconvolved', new=False, win=2)

# plot in R
plot_chir(data, win=3)
plot_chir(decon, label='deconvolved', new=False, win=3)
