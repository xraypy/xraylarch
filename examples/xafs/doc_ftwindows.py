#!/usr/bin/python

import numpy as np
from larch.xafs import ftwindow
from larch.plot.wxmplot_xafsplots import plot, plot_text, plot_arrow

k = np.linspace(0, 20, 401)

hann_win1 =  ftwindow(k, xmin=5, xmax=15, dx=3, window='hanning')
hann_win2 =  ftwindow(k, xmin=5, xmax=15, dx=5, window='hanning')
hann_win3 =  ftwindow(k, xmin=5, xmax=15, dx=3, dx2=7, window='hanning')
parzen_win1 =  ftwindow(k, xmin=5, xmax=15, dx=3, window='parzen')
welch_win1 =  ftwindow(k, xmin=5, xmax=15, dx=3, window='welch')

plot(k, hann_win1, label='Hanning(5, 15, dx=3)', xlabel='x',
     ymin=-0.05, ymax=1.20, show_legend=True)

plot([3.5, 3.5], [0, 1],   style='dashed', color='black', label='')
plot([6.5, 6.5], [0, 1],   style='dashed', color='black', label='')
plot([5.0, 5.0], [0, 0.5], style='dashed', color='black', label='')

plot_text('dx=3',   3.75, 1.05)
plot_arrow(5.0, 1, 3.5, 1)
plot_arrow(5.0, 1, 6.5, 1)

plot(k, hann_win1, label='Hanning(5, 15, dx=3)', xlabel='x',
         ymin=-0.05, ymax=1.05, show_legend=True, legend_loc='lc', win=2)
plot(k, hann_win2, label='Hanning(5, 15, dx=5)', win=2)

plot(k, welch_win1+0.5, label='Welch(5, 15, dx=3)',
     xlabel='x', ymin=-0.05, ymax=1.55, show_legend=True, legend_loc='lc', win=3)

plot(k, parzen_win1+0.25, label='Parzen(5, 15, dx=3)', win=3)
plot(k, hann_win1, label='Hanning(5, 15, dx=3)', win=3)


plot(k, hann_win1, label='Hanning(5, 15, dx=3)', xlabel='x',
         ymin=-0.05, ymax=1.05, show_legend=True, legend_loc='lc', win=4)
plot(k, hann_win3, label='Hanning(5, 15, dx=3, dx2=7)', win=4)


kai_win1 =  ftwindow(k, xmin=5, xmax=15, dx=4, window='kaiser')
sin_win1 =  ftwindow(k, xmin=5, xmax=15, dx=4, window='sine')
gau_win1 =  ftwindow(k, xmin=5, xmax=15, dx=4, window='gaussian')


plot(k, kai_win1, label='Kaiser(5, 15, dx=4)', xlabel='x',
        ymin=-0.05, ymax=1.05, show_legend=True, legend_loc='lc', win=5)
plot(k, sin_win1, label='Sine(5, 15, dx=4)', win=5)
plot(k, gau_win1, label='Gassian(5, 15, dx=4)', win=5)

plot(k, kai_win1, label='Kaiser(5, 15, dx=4)', xlabel='x',
        ymin=-0.05, ymax=1.05, show_legend=True, legend_loc='lc', win=6)
plot(k, ftwindow(k, xmin=5, xmax=15, dx=10, window='kaiser'),
     label='Kaiser(5, 15, dx=10)', win=6)
plot(k, ftwindow(k, xmin=5, xmax=15, dx=3, window='gaussian'),
     label='Gaussian(5, 15, dx=3)', win=6)
