from pathlib import Path

import numpy as np
import pytest

from larch.io import read_ascii
from larch.xafs import fluo_corr, pre_edge

basedir = Path(__file__).parent.parent.resolve()


@pytest.mark.parametrize('pre_edge_opts', [
    {},
    dict(pre1=-100, pre2=-30, norm1=50, norm2=300, nnorm=2),
])
def test_fluo_corr_uses_group_normalization(pre_edge_opts):
    """fluo_corr() normalizes with the ranges pre_edge() used for the group"""
    dat = read_ascii(Path(basedir, 'examples', 'xafsdata', 'fe2o3_rt1.xmu'))
    pre_edge(dat, **pre_edge_opts)
    details = dat.pre_edge_details
    explicit = {attr: getattr(details, attr)
                for attr in ('pre1', 'pre2', 'norm1', 'norm2', 'nnorm')}

    fluo_corr(dat.energy, dat.mu, 'Fe2O3', 'Fe', group=dat, e0=dat.e0, **explicit)
    explicit_mu, explicit_norm = dat.mu_corr.copy(), dat.norm_corr.copy()

    fluo_corr(dat.energy, dat.mu, 'Fe2O3', 'Fe', group=dat)
    np.testing.assert_allclose(dat.mu_corr, explicit_mu)
    np.testing.assert_allclose(dat.norm_corr, explicit_norm)
