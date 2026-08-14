## examples/feffit/doc_feffit4.py

from larch import Group
from larch.io import read_ascii
from larch.fitting import param, guess, param_group
from larch.xafs import autobk, feffpath, feffit_transform, feffit_dataset, feffit, feffit_report
from larch.wxlib.xafsplots import plot_chifit

feo_dat = read_ascii('../xafsdata/feo_xafs.dat', labels='energy mu')
autobk(feo_dat, kweight=2, rbkg=0.9)

# define fitting parameter group
pars = Group(n1     = param(6, vary=True),
             n2     = param(12, vary=True),
             s02    = param(0.700, vary=False),
             de0    = guess(0.1),
             sig2_1 = param(0.002, vary=True),
             delr_1 = guess(0.),
             sig2_2 = param(0.002, vary=True),
             delr_2 = guess(0.)  )

# define Feff Paths, give expressions for Path Parameters
path_feo = feffpath('feff_feo01.dat',
                    degen = 1,
                    s02    = 's02*n1',
                    e0     = 'de0',
                    sigma2 = 'sig2_1',
                    deltar = 'delr_1')

path_fefe = feffpath('feff_feo02.dat',
                     degen = 1,
                     s02    = 's02*n2',
                     e0     = 'de0',
                     sigma2 = 'sig2_2',
                     deltar = 'delr_2')

# set tranform / fit ranges
trans = feffit_transform(kmin=2.0, kmax=13.5, kweight=3,
                         dk=3,  window='kaiser',
                         rmin=1.0, rmax=3.2, fitspace='r')

# define dataset to include data, pathlist, transform
dset  = feffit_dataset(data=feo_dat, pathlist=[path_feo, path_fefe],
                       transform=trans)
out = feffit(pars, dset)
print( feffit_report(out))
try:
    fout = open('doc_feffit4.out', 'w')
    fout.write("%s\n" % feffit_report(out))
    fout.close()
except:
    print('could not write doc_feffit4.out')



plot_chifit(dset, title='Two-path fit to FeO')
## end examples/feffit/doc_feffit4.py
