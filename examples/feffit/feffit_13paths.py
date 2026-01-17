# read data

from larch.io import read_ascii
from larch.fitting import param, guess, param_group
from larch.xafs import autobk, feffpath, feffit_transform, feffit_dataset, feffit, feffit_report
from larch.wxlib.xafsplots import plot_chifit

cu_data  = read_ascii('cu_150k.xmu', labels='energy mutrans')

autobk(cu_data.energy, cu_data.mutrans, group=cu_data, rbkg=1.1, kw=2, clamp_hi=50)

pars = param_group(s02      = guess(1),
                   e01      = guess(4),
                   e0       = guess(4),
                   alpha    = guess(0),
                   sig2_p1  = guess(0.002),
                   sig2_p2  = guess(0.002),
                   sig2_p3  = guess(0.002),

                   sig2_p6  = guess(0.002),
                   sig2_p4  = param(expr='sig2_p3'),
                   sig2_p5  = param(expr='sig2_p3'),
                )

path1 = feffpath('Feff_Cu/feff0001.dat',   s02='s02', e0='e01',
                 sigma2 = 'sig2_p1',
                 deltar = 'alpha*reff')

path2 = feffpath('Feff_Cu/feff0002.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p2',
                 deltar = 'alpha*reff')

path3 = feffpath('Feff_Cu/feff0003.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p3',
                 deltar = 'alpha*reff')

path4 = feffpath('Feff_Cu/feff0004.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p4',
                 deltar = 'alpha*reff')

path5 = feffpath('Feff_Cu/feff0005.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p5',
                 deltar = 'alpha*reff')

path6 = feffpath('Feff_Cu/feff0006.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p6',
                 deltar = 'alpha*reff')

path7 = feffpath('Feff_Cu/feff0007.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p5',
                 deltar = 'alpha*reff')

path8 = feffpath('Feff_Cu/feff0008.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p5',
                 deltar = 'alpha*reff')

path9 = feffpath('Feff_Cu/feff0009.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p5',
                 deltar = 'alpha*reff')

path10 = feffpath('Feff_Cu/feff0010.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p5',
                 deltar = 'alpha*reff')

path11 = feffpath('Feff_Cu/feff0011.dat',   s02='s02', e0='e0',
                 sigma2= 'sig2_p5',
                 deltar= 'alpha*reff')

path12 = feffpath('Feff_Cu/feff0012.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p5',
                 deltar = 'alpha*reff')

path13 = feffpath('Feff_Cu/feff0013.dat',   s02='s02', e0='e0',
                 sigma2 = 'sig2_p5',
                 deltar = 'alpha*reff')


trans = feffit_transform(kmin=3, kmax=16, kw=[2,1,3],
                         dk=5, window='kaiser', rmin=1.4, rmax=4.7)

# define dataset to include data, pathlist, transform
dset = feffit_dataset(data=cu_data, transform=trans,
                      pathlist=[path1, path2, path3, path4, path5, path6,
                                path7, path8, path9, path10, path11,
                                path12, path13])

# perform fit!
out = feffit(pars, dset)

print(feffit_report(out, with_paths=True, min_correl=0.3))

plot_chifit(dset, kmin=0, kmax=None, kweight=None, rmax=8,
            show_mag=True, show_imag=True,
            title='13 paths fit to Cu',  new=True)
