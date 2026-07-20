#!/usr/bin/env python
## examples/xafs/autobk_timing.py

from pathlib import Path
from pyshortcuts import debugtimer
from larch.io import read_ascii
from larch.xafs import autobk, xftf, xftr

datafile = Path('..', 'xafsdata', 'cu_metal_rt.xdi')

timer = debugtimer()
nrepeats = 10
for i in range(nrepeats):
    cu = read_ascii(datafile)
    timer.add('## read data file')

    cu.mu = cu.mutrans * 1.0
    autobk(cu, rbkg=0.90, calc_uncertainties=(i%2))
    timer.add(f'autobk done calc_uncertainties={(i%2)}')

    xftf(cu.k, cu.chi, kmin=1, kmax=21, dk=2, window='hanning', kweight=2, group=cu, rmax_out=20)
    xftr(cu.r, cu.chir, rmin=0.1, rmax=4, qmax_out=20, dr=0, window='hanning', group=cu)
    timer.add('xftf and xftr done')

print(timer.get_report(precision=4))
