#!/usr/bin/env python

import Ifeffit
import time

iff = Ifeffit.Ifeffit()

script = """
read_data(file = ../xafsdata/cu_metal_rt.xdi, label = 'energy i0 i1 xmu', group = cu)
spline(energy= cu.energy, xmu= cu.xmu, kweight=1,rbkg=0.8)
fftf(cu.chi, kmin=1, kmax=21, dk=2, kwindow='hanning', kweight=2, group=cu, rmax_out=20)
fftr(real=cu.chir_re, imag=cu.chir_im, rmin=0.1, rmax=15, dr=0)
"""

iff.ifeffit('show $&build')

n = 100

t0 = time.time()

for i in range(n):
    iff.ifeffit(script)

print( 'Ran %i processing steps in % .4f seconds' % (n, time.time() - t0))

iff.ifeffit("plot(cu.k, cu.chi*cu.k**2)")

# doplot = False
# ##- timer = debug##- timer()
# t0 = time.time()
# n = 10
# for i in range(n):
#     print ' --- ', i
#
#     cu = read_ascii('tests/data/cu_metal_rt.xdi')
#     # cu = read_ascii('tests/data/cu_%3.3i.dat' % i)
#     ##- timer.add('read data file')
#     autobk(cu.energy, cu.mutrans, group=cu, rbkg=0.80, debug=True)
#     ##- timer.add('autobk done')
#
#     xafsft(cu.k, cu.chi, kmin=1, kmax=21, dk=2, window='hanning',
#            kweight=2, group=cu, rmax_out=20)
#     ##- timer.add('xafsft done')
#
#     xafsift(cu.r, cu.chir, rmin=0.1, rmax=4, qmax_out=20,
#             dr=0, window='hanning', group=cu)
#     ##- timer.add('xafs ift done')
#
#     if doplot:
#         newplot(cu.energy, cu.mutrans)
#         plot(cu.energy, cu.bkg)
#         #  plot(cu.energy, cu.init_bkg)
#         #  plot(cu.spline_e, cu.spline_y, linewidth=0, marker='o', color='red')
#         #  plot(cu.spline_e, cu.spline_yinit, linewidth=0, marker='o', color='black')
#         ##- timer.add('plot e-space done')
#
#         newplot(cu.k, cu.k**2*cu.chi, win=2)
#         # plot(cu.q, cu.chiq_re, win=2)
#         # #   plot(cu.q, cu.chiq_im, color='black', style='dashed')
#         #
#         ##- timer.add('plot k-space done')
#
#         # winscale = int((1.05* max(cu.chir_mag)))
#         newplot(cu.r, cu.chir_mag, win=3, xmax=15)
#         # plot(cu.r, cu.rwin*winscale, win=3, ymax=int(winscale*1.05))
#
#         ##- timer.add('plot r-space done')
#     endif
#
#     #if i % 8  == 0:
#     #    ##- timer.show_report()
#     #endif
# endfor
#
# # ##- timer.show_report()
#
#
# # show(cu)
#
# print 'Ran %i processing steps in % .4f seconds' % (n, time.time() - t0)
# ;
