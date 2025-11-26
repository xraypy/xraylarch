import numpy as np
from pathlib import Path
from larch.io import read_ascii
from larch.xafs import pre_edge, mback
from larch.plot.wxmplot_xafsplots import plot

filename =  Path('..', 'xafsdata', 'cu_10k.xmu').as_posix()
dat = read_ascii(filename)

mback(dat, z=29, edge='K', order=5, fit_erfc=False)

plot(dat.energy, dat.fpp, label=r'$\mu$', new=True)

plot(dat.energy, dat.f2, xlabel='Energy (eV)',
     ylabel=r'$\mu(E), f_2(E) $', label=r'$f_2$',  show_legend=True)
