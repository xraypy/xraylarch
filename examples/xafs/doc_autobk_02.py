#!/usr/bin/python
import numpy as np
from pathlib import Path
from larch.io import read_ascii
from larch.xafs import autobk
from larch.plot.wxmplot_xafsplots import plot_bkg, plot_chik

filename =  Path('..', 'xafsdata', 'scorodite_as_xafs.001')
dat = read_ascii(filename)
dat.mu = -np.log(dat.i1/dat.i0)

autobk(dat.energy, dat.mu, rbkg=1.0, group=dat)

plot_bkg(dat, emin=-150)
plot_chik(dat, kweight=2, win=2)
