#!/usr/bin/env python

import numpy as np
from pathlib import Path
from larch.io import read_ascii
from larch.xafs import autobk, pre_edge, xas_deconvolve
from larch.plot.wxmplot_xafsplots import plot_mu, plot

filename = Path('..', 'xafsdata', 'fe2o3_rt1.xmu')

dat = read_ascii(filename, labels='energy mu i0')

pre_edge(dat)
xas_deconvolve(dat, esigma=1.0)

plot_mu(dat, show_norm=True, emin=-30, emax=70)
plot(dat.energy, dat.deconv, label='deconvolved')

## end of examples/xafs/doc_deconv_01.py
