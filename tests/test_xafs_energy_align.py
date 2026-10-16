#!/usr/bin/env python
"""tests for energy_align, on a synthetic edge and a copy shifted by a known amount

a small (seeded) noise is added so that, as with real data, only the edge region
constrains the shift: noiseless curves can be aligned on any window, which would
hide a wrong fit window
"""
import importlib

import numpy as np
import pytest

from larch import Group
from larch.xafs import energy_align, pre_edge

E0 = 8979.0
SHIFT = 2.0
NOISE = 1.e-3
ENERGY = np.arange(E0 - 100, E0 + 200, 0.25)


def synthetic_mu(energy: np.ndarray, e0: float) -> np.ndarray:
    """arctan edge step plus a Gaussian white line just above e0"""
    step = 0.5 + np.arctan((energy - e0)/1.5)/np.pi
    whiteline = 0.6*np.exp(-(energy - e0 - 4.0)**2/(2*2.5**2))
    return step + whiteline


def make_groups(shift: float = SHIFT, noise: float = NOISE,
                seed: int = 0) -> tuple[Group, Group]:
    """group (edge at E0+shift, with noise) and reference (edge at E0, e0 set)"""
    rng = np.random.default_rng(seed)
    ref_mu = synthetic_mu(ENERGY, E0) + NOISE*rng.normal(size=ENERGY.size)
    dat_mu = synthetic_mu(ENERGY, E0 + shift) + noise*rng.normal(size=ENERGY.size)
    ref = Group(energy=ENERGY.copy(), mu=ref_mu, e0=E0)
    dat = Group(energy=ENERGY.copy(), mu=dat_mu)
    return dat, ref


def normalize(*groups: Group) -> None:
    """run pre_edge on groups, keeping an e0 already set"""
    for grp in groups:
        e0 = getattr(grp, 'e0', None)
        pre_edge(grp)
        if e0 is not None:
            grp.e0 = e0


def test_energy_align_mu_only() -> None:
    """groups with only energy and mu: no arrays are written to them
    (was a NameError on `gradient` when building dmude)"""
    dat, ref = make_groups()
    eshift = energy_align(dat, ref)
    assert eshift == pytest.approx(-SHIFT, abs=0.05)
    assert dat.eshift == eshift
    for grp in (dat, ref):
        assert not hasattr(grp, 'dmude')
        assert not hasattr(grp, 'norm')


@pytest.mark.parametrize('array', ['auto', 'norm', 'mu', 'dmude'])
def test_energy_align_recovers_shift(array: str) -> None:
    """default emin/emax window spans the edge, so a known shift is recovered"""
    dat, ref = make_groups()
    normalize(dat, ref)
    eshift = energy_align(dat, ref, array=array)
    assert eshift == pytest.approx(-SHIFT, abs=0.05)


@pytest.mark.parametrize('shift', [8.0, -8.0, 15.0])
def test_energy_align_large_shift_from_e0(shift: float) -> None:
    """with a group e0 the fit starts from the e0 difference"""
    dat, ref = make_groups(shift)
    # an e0 off by 0.5 eV is still a good enough starting point
    dat.e0 = E0 + shift + 0.5
    eshift = energy_align(dat, ref)
    assert eshift == pytest.approx(-shift, abs=0.05)


@pytest.mark.parametrize('seed', [0, 1, 2])
@pytest.mark.parametrize('shift', [2.0, 15.0])
def test_energy_align_noisy(shift: float, seed: int) -> None:
    """noisy group (as Larix aligns them: normalized, e0 from pre_edge):
    the smoothed residual keeps the fit on the edge"""
    dat, ref = make_groups(shift, noise=3.e-2, seed=seed)
    normalize(dat, ref)
    eshift = energy_align(dat, ref)
    assert eshift == pytest.approx(-shift, abs=0.3)


@pytest.mark.parametrize('shift', [2.0, 8.0])
def test_energy_align_wrong_e0(shift: float) -> None:
    """a group e0 30 eV off (e.g. from a glitch) does not mislead the fit"""
    dat, ref = make_groups(shift, noise=1.e-2)
    normalize(dat, ref)
    dat.e0 = E0 + shift + 30
    eshift = energy_align(dat, ref)
    assert eshift == pytest.approx(-shift, abs=0.3)


@pytest.mark.parametrize('use_e0', [False, True])
def test_energy_align_raw_mu_baseline(use_e0: bool) -> None:
    """raw mu with a different step height, offset and pre-edge slope:
    the linear baseline in the fit replaces normalization"""
    shift = 8.0
    dat, ref = make_groups(shift, noise=1.e-2)
    dat.mu = 0.3*dat.mu + 1.2 - 0.002*(dat.energy - E0)
    if use_e0:
        dat.e0 = E0 + shift + 0.5
    eshift = energy_align(dat, ref, array='mu')
    assert eshift == pytest.approx(-shift, abs=0.3)


def test_energy_align_fit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """a failing fit gives nan, not a silent 0"""
    module = importlib.import_module('larch.xafs.pre_edge')

    def fail(self: object) -> None:
        raise RuntimeError('fit failed')

    monkeypatch.setattr(module.Minimizer, 'leastsq', fail)
    dat, ref = make_groups()
    eshift = energy_align(dat, ref)
    assert np.isnan(eshift)
    assert np.isnan(dat.eshift)


def test_energy_align_bad_arguments() -> None:
    dat, ref = make_groups()
    with pytest.raises(ValueError):
        energy_align(dat, ref, array='chi')
    with pytest.raises(ValueError):
        energy_align(dat, ref, array='norm')   # no norm without pre_edge
    with pytest.raises(ValueError):
        energy_align(dat, Group(energy=ref.energy, mu=ref.mu))   # no e0
