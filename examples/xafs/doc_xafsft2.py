#!/usr/bin/env python
## examples/xafs/doc_xafsft2.py

from pathlib import Path
from larch import Group
from larch.io import read_ascii
from larch.xafs import autobk, xftf
from larch.plot.wxmplot_xafsplots import plot_chir

dat = read_ascii(Path('..', 'xafsdata', 'feo_rt1.xdi'), labels='energy mu i0')
autobk(dat, rbkg=1, kweight=2, clamp_hi=10)

d1 = Group(k=dat.k, chi=dat.chi, filename=dat.filename)
d2 = Group(k=dat.k, chi=dat.chi, filename=dat.filename)
d3 = Group(k=dat.k, chi=dat.chi, filename=dat.filename)
d4 = Group(k=dat.k, chi=dat.chi, filename=dat.filename)
d5 = Group(k=dat.k, chi=dat.chi, filename=dat.filename)

ftopts = dict(kmin=3, kmax=13, dk=4, kweight=2)

xftf(d1, window='hanning',  **ftopts)
xftf(d2, window='parzen',   **ftopts)
xftf(d3, window='welch',    **ftopts)
xftf(d4, window='kaiser',   **ftopts)
xftf(d5, window='gaussian', **ftopts)

plot_chir(d1, label='Hanning')
plot_chir(d2, label='Parzen',   new=False)
plot_chir(d3, label='Welch',    new=False)
plot_chir(d4, label='Kaiser',   new=False)
plot_chir(d5, label='Gaussian', new=False)
