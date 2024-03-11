## examples/pca/pca_aucyano.py
# note that this is similar to examples/fitting/doc_example3

from larch.io import read_athena
from larch.xafs import pre_edge
from larch.math import pca_train, pca_fit

from larch.wxlib.xafsplots import plot_pca_components, plot_pca_weights, plot_pca_fit

prj = read_athena('cyanobacteria.prj', do_fft=False, do_bkg=False)


standards = (prj.Au_foil, prj.Au3_Cl_aq, prj.Au_hydroxide, prj.Au_thiocyanide,
             prj.Au_sulphide, prj.Au_thiosulphate_aq)

unknowns = (prj.d_0_12, prj.d_2_42, prj.d_4_73, prj.d_7_03,
           prj.d_9_33, prj.d_20, prj.d_33, prj.d_720)

# make sure pre_edge() is run with the same params for all groups
for grp in standards + unknowns:
    pre_edge(grp, pre1=-150, pre2=-30, nnorm=1, norm1=150, norm2=850)
#endfor

# train model with standards
au_pcamodel = pca_train(standards, arrayname='norm', xmin=11870, xmax=12030)


# plot components and weights
plot_pca_components(au_pcamodel, min_weight=0.005)
plot_pca_weights(au_pcamodel, win=2, min_weight=0.005, ylog_scale=True)

# print out weights
total = 0
print(" Comp #  |  Weight   |  Cumulative Total")
for i, weight in enumerate(au_pcamodel.variances):
    total = total + weight
    print("  %3i    | %8.5f  | %8.5f " % (i+1, weight, total))
#endfor

# fit unknown data to model
pca_fit(prj.d_720, au_pcamodel, ncomps=4)

# plot
plot_pca_fit(prj.d_720, win=3)


## end of examples/pca/pca_aucyano.py
