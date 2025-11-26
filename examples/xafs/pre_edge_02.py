#!/usr/bin/python
import numpy as np
from pathlib import Path
from larch.io import read_ascii
from larch.xafs import pre_edge
from larch.plot.wxmplot_xafsplots import plot_mu

filename =  Path('..', 'xafsdata', 'fe2o3_rt1.xmu').as_posix()

dat = read_ascii(filename, labels='energy mu i0')
.
pre_edge(dat)
plot_mu(dat, show_pre=True, show_post=True, show_e0=True)
