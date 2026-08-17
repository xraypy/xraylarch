## examples/feffit/doc_feffit5.py
from copy import copy
from larch.xafs import feffit, feffit_report
from larch.wxlib.xafsplots import plot_chifit

# start with earlier model and fit
from doc_feffit4 import out, pars, dset

def save_result(out, fname):
    f = open(fname, 'w')
    f.write(feffit_report(out, with_paths=False, min_correl=0.5))
    f.write('\n')
    f.close()


# fit in R space
save_result(out, 'doc_feffit5_r.out')

# fit in Q space (back-transformed or filtered K-space)
pars2 = copy(pars)   # copy parameters
dset.transform.fitspace = 'q'

out2 = feffit(pars2, dset)
save_result(out2, 'doc_feffit5_q.out')

# fit in K space (unfiltered)
pars3 = copy(pars)   # copy parameters
dset.transform.kweight = 2
dset.transform.fitspace = 'k'

out3 = feffit(pars3, dset)
save_result(out3, 'doc_feffit5_k.out')


# fit in W space (using Wavelet transform)
pars4 = copy(pars)   # copy parameters
dset.transform.fitspace = 'w'

out4 = feffit(pars4, dset)
save_result(out4, 'doc_feffit5_w.out')

print('wrote outputs for fitting in different spaces')
## end examples/feffit/doc_feffit5.py
