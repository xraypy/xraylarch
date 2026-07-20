#!/usr/bin/env python
## examples/xafs/doc_xafsft4.py

from pathlib import Path
from larch import Group
from larch.io import read_ascii
from larch.xafs import autobk, xftf, xftr
from larch.plot.wxmplot_xafsplots import plot, plot_chik, plot_chir

dat = read_ascii(Path('..', 'xafsdata', 'feo_rt1.xdi'), labels='energy mu i0')
autobk(dat, rbkg=1, kweight=2, clamp_hi=10)

xftf(dat, kmin=3, kmax=13, dk=4, window='hanning', kweight=2)

d2 = Group(r=dat.r, chir=dat.chir, filename=dat.filename)

xftr(dat, rmin=1, rmax=3.3, dr=0.2, window='hanning')
xftr(d2,  rmin=1, rmax=2.0, dr=0.2, window='hanning')

plot_chir(dat)
plot(d2.r,  d2.rwin,  label='R-window, rmax=2.0', linewidth=3)
plot(dat.r, dat.rwin, label='R-window, rmax=3.3', linewidth=3)

plot_chik(dat, kweight=2, label='data', show_window=False, win=2)
plot(d2.q,  d2.chiq_re,  win=2, label='chiq_re, rmax=2.0', linewidth=3, xmax=15)
plot(dat.q, dat.chiq_re, win=2, label='chiq_re, rmax=3.3', linewidth=3, xmax=15)
