#!/usr/bin/python
import numpy as np
from pathlib import Path
from larch.io import read_ascii
from larch.xafs import autobk
from larch.plot.wxmplot_xafsplots import plot

filename =  Path('..', 'xafsdata', 'scorodite_as_xafs.001')
dat = read_ascii(filename)
dat.mu = -np.log(dat.i1/dat.i0)

autobk(dat.energy, dat.mu, rbkg=1.0, group=dat, clamp_hi=0)
dat.chi0 = dat.chi * dat.k**2
dat.bkg0 = dat.bkg

autobk(dat.energy, dat.mu, rbkg=1.0, group=dat, clamp_hi=50)
dat.chi50 = dat.chi * dat.k**2
dat.bkg50 = dat.bkg

autobk(dat.energy, dat.mu, rbkg=1.0, group=dat, clamp_hi=200)
dat.chi200 = dat.chi * dat.k**2
dat.bkg200 = dat.bkg

plot(dat.k, dat.chi0, label='clamp_hi=0', show_legend=True, new=True,
        xlabel=r'$k \rm\, (\AA^{-1})$',  ylabel=r'$k^2\chi(k)$',
        title='Effect of clamp_hi')

plot(dat.k, dat.chi50, label='clamp_hi=50', show_legend=True)
plot(dat.k, dat.chi200, label='clamp_hi=200', show_legend=True)
