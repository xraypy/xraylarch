## examples/feffit/doc_feffdat_02.py

from larch.xafs import feffpath, path2chi

from wxmplot.interactive import plot

fname = 'feff0001.dat'
path1 = feffpath(fname)

plot(path1._feffdat.k, path1._feffdat.amp, xlabel='$ k \\rm\\, (\\AA^{-1})$',
        ylabel='$ |F_{\\rm eff}(k)|$', label = r'amp', show_legend=True,
        title=f'components of _feffdat for {fname}',
        marker='o', markersize=4, new=True)

plot(path1._feffdat.k, path1._feffdat.lam, side='right',
     marker='o', markersize=4,
     label='lam', y2label='$ \\lambda(k) \\rm\\, (\\AA)$')

## end examples/feffit/doc_feffdat_02.py
