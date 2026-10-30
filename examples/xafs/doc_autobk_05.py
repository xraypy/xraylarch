from pathlib import Path
from copy import deepcopy

import numpy as np

try:
    from feffdb import FeffDatabase
except ImportError:
    raise ImportError("This example needs feffdb installed")

from larch.io import read_ascii
from larch.xafs import autobk, xftf
from larch.plot.wxmplot_xafsplots import plot_chik, plot_chir, plot_bkg, plot

filename =  Path('..', 'xafsdata', 'Nickel_II_oxide_id3zpndq_CLSDB.dat')

dat1 = read_ascii(filename)

dat1.energy = np.delete(dat1.energy, 158)
dat1.itrans = np.delete(dat1.itrans, 158)

dat1.i0 = np.delete(dat1.i0, 158)
dat1.mu = -np.log(dat1.itrans/dat1.i0)

# make a copy
dat2 = deepcopy(dat1)


# background subtraction, no std
autobk(dat1, e0=8345., rbkg=1.1, kw=2)

# background subtraction, Ni-O std from Feff database
autobk(dat2, e0=8345., rbkg=1.1, kw=2, std_feffpath='feffdb[NiO206]')


xftf(dat1, kmin=3, kmax=14, dk=4, kwindow='Hanning', kweight=2)
xftf(dat2, kmin=3, kmax=14, dk=4, kwindow='Hanning', kweight=2)

plot_chik(dat1, kweight=2, label='no std', show_window=False)
plot_chik(dat2, kweight=2, label='with std', new=False)

plot_chir(dat1, label='no std',  win=2)
plot_chir(dat2, label='with std', new=False, win=2)

plot_bkg(dat2, emin=-50, emax=300, win=3)

dat1.bkg_norm = (dat1.bkg - dat1.pre_edge) / dat1.edge_step
plot(dat1.energy, dat1.bkg_norm, ymin=0.3, ymax=1.5, label='bkg without std', win=3)
