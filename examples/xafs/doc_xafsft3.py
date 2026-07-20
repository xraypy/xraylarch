#!/usr/bin/env python
## examples/xafs/doc_xafsft3.py

from pathlib import Path
from larch.io import read_ascii
from larch.xafs import autobk, xftf
from larch.plot.wxmplot_xafsplots import plot_chir

dat = read_ascii(Path('..', 'xafsdata', 'feo_rt1.xdi'), labels='energy mu i0')
autobk(dat, rbkg=1, kweight=2, clamp_hi=10)

xftf(dat, kmin=3, kmax=13, dk=4, window='hanning', kweight=2)

plot_chir(dat, show_mag=True, show_real=True, show_imag=True)
