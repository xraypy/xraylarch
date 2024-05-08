#
# read some ASCII data files, and create an Athena Project file from them
#
from pathlib import Path

from larch.io import read_ascii, AthenaProject
from larch.xafs import pre_edge

# first we will read in a few "raw beamline data files" and create a list of datasets

folder = Path('..', 'xafsdata', 'fexafs')
filenames = ['fexanes_a.001', 'fexanes_b.001', 'fexanes_c.001',
             'fexanes_d.001', 'fexanes_e.001']

datasets = []
for filename in filenames:
    # note that these files will have a lot of columns -- we only need "sum_fe_ka"
    fname = Path(folder, filename)
    print("reading data file ", fname)
    dset = read_ascii(fname,  labels='energy, t, i0, i1, i2, sum_out, sum_caka, sum_feka')
    dset.mu = dset.sum_feka / dset.i0

    # this works ok for pre-edge subtraction and normalization for this dataset, but
    # might need adjusting for other datasets
    pre_edge(dset, pre1=-200.00, pre2=-25.00, nnorm=1, norm1=100.00, norm2=300.00)
    datasets.append(dset)


# with those datasets of XAFS data now as Larch Groups, we can create and
# Athena Project File and add these groups to it, and then save the project

project = AthenaProject(filename=Path(folder, 'FeXANES_example.prj'))
for dset in datasets:
    print("Adding to Project:  ", dset, getattr(dset, 'filename', 'no filename'))
    project.add_group(dset)
project.save(use_gzip=True)
