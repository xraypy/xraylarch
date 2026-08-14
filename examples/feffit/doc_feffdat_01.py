## examples/feffit/doc_feffdat_01.py

from larch.xafs import feffpath, path2chi

from wxmplot.interactive import plot

fname = 'feff0001.dat'
path1 = feffpath(fname)

path2chi(path1)

print(dir(path1))

plot(path1.k, path1.chi*path1.k**2, xlabel='$ k \\rm (\\AA^{-1})$',
        ylabel='$ k^2\\chi(k)$', label = '$\\sigma^2 = 0$',
        title=f'$\\chi(k)$ from {fname}',  show_legend=True, new=True)

path1.sigma2 = 0.002

path2chi(path1)

plot(path1.k, path1.chi*path1.k**2, label = '$\\sigma^2 = 0.002$')

## end examples/feffit/doc_feffdat_01.py
