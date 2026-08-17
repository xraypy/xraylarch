## examples/feffit/doc_feffit3.py

from larch import Group
from larch.io import read_ascii
from larch.fitting import param, guess, param_group
from larch.xafs import autobk, feffpath, feffit_transform, feffit_dataset, feffit, feffit_report, sigma2_eins
from larch.wxlib.xafsplots import plot_chifit

# read 3 datasets
cu_10 = read_ascii('../xafsdata/cu_10k.xmu')
autobk(cu_10.energy, cu_10.mu, group=cu_10, rbkg=1.0, kw=2)

cu_50 = read_ascii('../xafsdata/cu_50k.xmu')
autobk(cu_50.energy, cu_50.mu, group=cu_50, rbkg=1.0, kw=2)

cu_150 = read_ascii('../xafsdata/cu_150k.xmu')
autobk(cu_150.energy, cu_150.mu, group=cu_150, rbkg=1.0, kw=2)

# define fitting parameter group
pars = Group(amp    = param(1, vary=True),
             del_e0 = guess(2.0),
             theta  = param(250, min=10, vary=True),
             dr_off = guess(0),
             alpha  = guess(0) )

# define 3 Feff Path, give expressions for Path Parameters
path1_10  = feffpath('feff0001.dat',  s02 = 'amp', e0 = 'del_e0',
                     deltar = 'dr_off + 10*alpha*reff',
                     sigma2 = 'sigma2_eins(10, theta)')


path1_50  = feffpath('feff0001.dat',  s02 = 'amp', e0 = 'del_e0',
                     deltar = 'dr_off + 50*alpha*reff',
                     sigma2 = 'sigma2_eins(50, theta)')

path1_150 = feffpath('feff0001.dat',  s02 = 'amp', e0 = 'del_e0',
                     deltar = 'dr_off + 150*alpha*reff',
                     sigma2 = 'sigma2_eins(150, theta)')

trans = feffit_transform(kmin=3, kmax=17, kw=2, dk=4, window='kaiser', rmin=1.4, rmax=3.4)

# define 3 datasets, each with data, pathlist, transform for each
dset_10   = feffit_dataset(data=cu_10,  pathlist=[path1_10],  transform=trans)
dset_50   = feffit_dataset(data=cu_50,  pathlist=[path1_50],  transform=trans)
dset_150  = feffit_dataset(data=cu_150, pathlist=[path1_150], transform=trans)

# perform fit!
out = feffit(pars, [dset_10, dset_50, dset_150])
report = feffit_report(out)

print( report)
try:
    fout = open('doc_feffit3.out', 'w')
    fout.write("%s\n" % feffit_report(out))
    fout.close()
except:
    print('could not write doc_feffit3.out')


plot_chifit(dset_10, title='fit to Cu, 10K', rmax=5, win=1)
plot_chifit(dset_50, title='fit to Cu, 50K', rmax=5, win=3)
plot_chifit(dset_150, title='fit to Cu, 150K', rmax=5, win=5)

_ave = sigma2_eins(150, out.paramgroup.theta, path1_150)
_dlo = sigma2_eins(150, out.paramgroup.theta-out.paramgroup.theta.stderr, path1_150) - _ave
_dhi = sigma2_eins(150, out.paramgroup.theta+out.paramgroup.theta.stderr, path1_150) - _ave
print(f"sigma2(T=150) = {_ave:.5f}  ({_dlo:+.5f}, {_dhi:+.5f})")

# ## end examples/feffit/doc_feffit3.py
