# wavelet transform in larch
# follows method of Munuz, Argoul, and Farges

import numpy as np
from pathlib import Path
from larch import Group
from larch.io import read_ascii
from xraydb import core_width
from larch.xafs import autobk, pre_edge, xftf, cauchy_wavelet
from larch.plot.wxmplot_xafsplots import imshow, plot, plot_chik, plot_chir


feo = read_ascii(Path('..', 'xafsdata', 'feo_xafs.dat'))
autobk(feo, rbkg=0.9, kweight=2)

kopts = {'xlabel': r'$k \,(\AA^{-1})$',
         'ylabel': r'$k^2\chi(k) \, (\AA^{-2})$',
         'linewidth': 3, 'title': 'FeO', 'show_legend':True}

xftf(feo, kmin=1, kmax=14, kweight=2, dk=4.5, window='Kaiser')

plot_chik(feo, kweight=2)


# do wavelet transform (no window function yet)
cauchy_wavelet(feo, kweight=2)

# display wavelet magnitude, real part
# horizontal axis is k, vertical is R
imopts = {'x': feo.k, 'y': feo.wcauchy_r}
imshow(feo.wcauchy_mag, win=1, label='Wavelet Transform: Magnitude', **imopts)
imshow(feo.wcauchy_re,  win=2, label='Wavelet Transform: Real Part', **imopts)

# plot wavelet projected to k space
plot(feo.k, feo.wcauchy_re.sum(axis=0), win=2, label='projected wavelet', **kopts)

ropts = kopts
ropts['xlabel'] = r'$R \, (\AA) $'
ropts['ylabel'] = r'$|\chi(R)| \, (\AA^{-3})$'

# plot wavelet projected to R space
plot(feo.r,  feo.chir_mag, win=3,  label='traditional XAFS FT', **ropts)
plot(feo.wcauchy_r, feo.wcauchy_mag.sum(axis=1)/6.0, win=3,  label='projected wavelet/6 (?)', **ropts)
