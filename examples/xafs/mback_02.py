import numpy as np
from pathlib import Path
from larch.io import read_ascii
from larch.xafs import pre_edge, mback
from larch.plot.wxmplot_xafsplots import plot_mu, plot

filename =  Path('..', 'xafsdata', 'sno2_l3.dat').as_posix()
dat = read_ascii(filename)

pre_edge(dat)
dat.norm_poly = dat.norm

mback(dat, z=50, edge='L3', pre1=-60, pre2=-30, norm1=50, norm2=200)

plot_mu(dat, show_norm=True, title='SnO3 L3 edge', new=True,
        label='MBACK normalized')

plot(dat.energy, dat.norm_poly, label='Polynomial normalized')

print(dat.e0)
