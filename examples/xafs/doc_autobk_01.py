#!/usr/bin/python

import numpy as np
from pathlib import Path
from larch.io import read_ascii
from larch.xafs import autobk
from larch.plot.wxmplot_xafsplots import plot_bkg, plot_chik

filename =  Path('..', 'xafsdata', 'cu_rt01.xmu').as_posix()

cu = read_ascii(filename)
autobk(cu.energy, cu.mu, rbkg=1.0, group=cu)

plot_bkg(cu, emin=-100, emax=400)

plot_chik(cu, kweight=1, win=2)
