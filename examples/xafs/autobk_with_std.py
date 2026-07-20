#!/usr/bin/env python
## examples/xafs/autobk_with_std.py

from pathlib import Path
from copy import deepcopy
from larch.io import read_ascii
from larch.xafs import pre_edge, autobk, xftf
from larch.plot.wxmplot_xafsplots import plot

cu1 = read_ascii(Path('..', 'xafsdata', 'cu.xmu'))
chidat = read_ascii(Path('..', 'xafsdata', 'cu10k.chi'), labels='k chi')

pre_edge(cu1.energy, cu1.mu, group=cu1)
cu2 = deepcopy(cu1)

autobk(cu1.energy, cu1.mu, rbkg=1, group=cu1)
autobk(cu2.energy, cu2.mu, rbkg=1, group=cu2, k_std=chidat.k, chi_std=chidat.chi)

xftf(cu1.k, cu1.chi, kmin=2, kmax=16, dk=2, kweight=2, window='hanning', group=cu1)
xftf(cu2.k, cu2.chi, kmin=2, kmax=16, dk=2, kweight=2, window='hanning', group=cu2)

plot(cu1.k, cu1.chi * cu1.k**2, label='no std', new=True,
     ylabel=r'$k^2\chi(k)$', xlabel=r'$k\,(\AA^{-1})$', title=r'$\chi(k)$')
plot(cu2.k, cu2.chi * cu2.k**2, label='with std')
