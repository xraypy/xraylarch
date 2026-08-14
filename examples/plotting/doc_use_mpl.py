## examples/plotting/doc_use_mpl.py
#
import numpy as np
from scipy.special import gamma
from wxmplot.interactive import plot
title = 'GNXAS-like distribution function'

sigma, beta, r0 = 0.12, 0.65, 3.0
q    = 4/beta**2
amp  = 2 / (sigma*np.abs(beta)*gamma(q))

# calculate g(r) on a fine r-grid:
r   = np.linspace(2.5, 3.5, 201)
arg = q + (2*(r-r0)) / (beta*sigma)
gr  = amp * np.exp(-arg)*arg**(q-1)
# note removal of nan's and impossible values
gr[np.isnan(gr)] = 0
if min(gr)< 0:
    gr[np.where(gr<0)] = 0

# standard plot of g(r)
display = plot(r, gr, grid=False,
             xlabel='$R\\,\\rm(\\AA)$', ylabel=r'$g(R)$',
             title=title, fullbox=False)

# calculate g(r) on a coarse r-grid:
hr   = np.linspace(2.5, 3.5, 21)
harg = q + (2*(hr-r0)) / (beta*sigma)
hgr  = amp * np.exp(-harg)*harg**(q-1)
hgr[np.isnan(hgr)] = 0
if min(hgr)< 0:
    hgr[np.where(hgr<0)] = 0

# get panel, matplotlib axes
panel = display.panel
axes  = panel.axes

# plot histogram of coarse-grid data
histo = axes.hist(hr, weights=hgr, bins=len(hr), rwidth=0.25, color='k')
panel.draw()

## end of examples/plotting/doc_use_mpl.py
