__DOC__ = '''
XAFS Functions for Larch, essentially Ifeffit 2

The functions here include (but are not limited to):

function         description
------------     ------------------------------
pre_edge         pre_edge subtraction, normalization
autobk           XAFS background subtraction (mu(E) to chi(k))
xftf             forward XAFS Fourier transform (k -> R)
xftr             backward XAFS Fourier transform, Filter (R -> q)
ftwindow         create XAFS Fourier transform window

feffpath         create a Feff Path from a feffNNNN.dat file
path2chi         convert a single Feff Path to chi(k)
ff2chi           sum a set of Feff Paths to chi(k)

feffit_dataset   create a Dataset for Feffit
feffit_transform create a Feffit transform group
feffit           fit a set of Feff Paths to Feffit Datasets
feffit_report    create a report from feffit() results
'''


from .xafsutils import KTOE, ETOK, set_xafsGroup, etok, ktoe, guess_energy_units
from .xafsft import xftf, xftr, xftf_fast, xftr_fast, ftwindow, xftf_prep
from .pre_edge import pre_edge, preedge, find_e0, pre_edge_baseline, prepeaks_setup
from .feffdat import FeffDatFile, FeffPathGroup, feffpath, path2chi, ff2chi
from .feffit import (FeffitDataSet, TransformGroup, feffit,
                     feffit_dataset, feffit_transform, feffit_report)

from .autobk import autobk
from .mback import mback, mback_norm
from .diffkk import diffkk, diffKKGroup
from .fluo import fluo_corr

from .feffrunner import FeffRunner, feffrunner, feff6l, feff8l, find_exe
from .feff8lpath import feff8_xafs



from .cauchy_wavelet import cauchy_wavelet
from .deconvolve import xas_convolve, xas_deconvolve
from .estimate_noise import estimate_noise
from .rebin_xafs import rebin_xafs, sort_xafs
from .sigma2_models import sigma2_eins, sigma2_debye, sigma2_correldebye


def _larch_init(_larch):
    """initialize xafs"""
    # initialize _xafs._feff_executable
    feff6_exe = find_exe('feff6l')
    _larch.symtable.set_symbol('_xafs._feff_executable', feff6_exe)
    

_larch_groups = (diffKKGroup, FeffRunner, FeffDatFile, FeffPathGroup,
                 TransformGroup, FeffitDataSet)

_larch_builtins = {'_xafs': dict(autobk=autobk, etok=etok, ktoe=ktoe,
                                 guess_energy_units=guess_energy_units,
                                 diffkk=diffkk, xftf=xftf, xftr=xftr,
                                 xftf_prep=xftf_prep, xftf_fast=xftf_fast,
                                 xftr_fast=xftr_fast, ftwindow=ftwindow,
                                 find_e0=find_e0, pre_edge=pre_edge,
                                 prepeaks_setup=prepeaks_setup,
                                 pre_edge_baseline=pre_edge_baseline,
                                 mback=mback, mback_norm=mback_norm,
                                 cauchy_wavelet=cauchy_wavelet,
                                 xas_deconvolve=xas_deconvolve,
                                 xas_convolve=xas_convolve,
                                 fluo_corr=fluo_corr,
                                 estimate_noise=estimate_noise,
                                 rebin_xafs=rebin_xafs,
                                 sort_xafs=sort_xafs,
                                 sigma2_eins=sigma2_eins,
                                 sigma2_debye=sigma2_debye, feffit=feffit,
                                 feffit_dataset=feffit_dataset,
                                 feffit_transform=feffit_transform,
                                 feffit_report=feffit_report,
                                 feffrunner=feffrunner, feff6l=feff6l,
                                 feff8l=feff8l, feffpath= feffpath,
                                 path2chi=path2chi, ff2chi=ff2chi,
                                 feff8_xafs=feff8_xafs)}
