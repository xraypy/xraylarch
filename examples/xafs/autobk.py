#!/usr/bin/env python
## examples/xafs/autobk.py

from pathlib import Path
from larch.io import read_ascii
from larch.xafs import pre_edge, autobk, xftf
from larch.plot.wxmplot_xafsplots import plot_chik, plot_chir

dat = read_ascii(Path('..', 'xafsdata', 'cu_rt01.xmu'), labels='energy mu i0')

pre_edge(dat)
autobk(dat, rbkg=1.0, kweight=2)

xftf(dat, kmin=2, kmax=16, dk=3, window='hanning', kweight=2)

plot_chik(dat, kweight=2)
plot_chir(dat, win=2)
