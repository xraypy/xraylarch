from pathlib import Path
from copy import deepcopy

import numpy as np

from larch.io import read_ascii
from larch.xafs import autobk, pre_edge, xftf
from larch.plot.wxmplot_xafsplots import plot_chik, plot_chir

filename =  Path('..', 'xafsdata', 'cu.xmu')
chi_fname = Path('..', 'xafsdata', 'cu10k.chi')

cu1 = read_ascii(filename)

pre_edge(cu1.energy, cu1.mu, group=cu1)

cu2 = deepcopy(cu1)


# background subtraction the "normal way", with FFT
autobk(cu1, cu1, rbkg=0.9, kweight=1)

# background subtraction with a standard
chidat = read_ascii(chi_fname, labels='k chi')

autobk(cu2, rbkg=0.9, kweight=1,  k_std=chidat.k, chi_std=chidat.chi)

plot_chik(cu1, kweight=2, label='no std')
plot_chik(cu2, kweight=2, label='with std', new=False)



xftf(cu1, kmin=3, kmax=18, dk=4, kwindow='Hanning', kweight=2)
xftf(cu2, kmin=3, kmax=18, dk=4, kwindow='Hanning', kweight=2)


plot_chir(cu1, label='no std',  win=2)
plot_chir(cu2, label='with std', new=False, win=2)
## end of examples/xafs/doc_autobk_04.py
