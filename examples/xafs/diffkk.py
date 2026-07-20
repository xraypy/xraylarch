#!/usr/bin/env python
## examples/xafs/diffkk.py

from pathlib import Path
from larch.io import read_ascii
from larch.xafs import diffkk
from larch.plot.wxmplot_xafsplots import plot_diffkk

print('Reading copper foil data')
data = read_ascii(Path('..', 'xafsdata', 'cu_10k.xmu'))
dkk = diffkk(data.energy, data.mu, z=29, edge='K', mback_kws={'e0': 8979, 'order': 4})

print('Doing diff KK transform')
dkk.kk()

plot_diffkk(dkk)
