#!/usr/bin/env python
"""tests for energy_align, on a synthetic edge and a copy shifted by a known amount

a small (seeded) noise is added so that, as with real data, only the edge region
constrains the shift: noiseless curves can be aligned on any window, which would
hide a wrong fit window
"""
import numpy as np
import pytest

from larch import Group
from larch.xafs import energy_align

E0 = 8979.0
SHIFT = 2.0
NOISE = 1.e-3


def synthetic_mu(energy: np.ndarray, e0: float) -> np.ndarray:
    """arctan edge step plus a Gaussian white line just above e0"""
    step = 0.5 + np.arctan((energy - e0)/1.5)/np.pi
    whiteline = 0.6*np.exp(-(energy - e0 - 4.0)**2/(2*2.5**2))
    return step + whiteline


def make_groups() -> tuple[Group, Group]:
    rng = np.random.default_rng(0)
    energy = np.arange(E0 - 100, E0 + 200, 0.25)
    ref_mu = synthetic_mu(energy, E0) + NOISE*rng.normal(size=energy.size)
    dat_mu = synthetic_mu(energy, E0 + SHIFT) + NOISE*rng.normal(size=energy.size)
    ref = Group(energy=energy, mu=ref_mu, e0=E0)
    dat = Group(energy=energy.copy(), mu=dat_mu)
    return dat, ref


def test_energy_align_without_dmude() -> None:
    """dmude is built when missing (was a NameError on `gradient`)"""
    dat, ref = make_groups()
    assert not hasattr(dat, 'dmude')
    assert not hasattr(ref, 'dmude')
    energy_align(dat, ref)
    assert hasattr(dat, 'dmude')
    assert hasattr(ref, 'dmude')


@pytest.mark.parametrize('array', ['dmude', 'mu'])
def test_energy_align_recovers_shift(array: str) -> None:
    """default emin/emax window spans the edge, so a known shift is recovered"""
    dat, ref = make_groups()
    eshift = energy_align(dat, ref, array=array)
    assert eshift == pytest.approx(-SHIFT, abs=0.05)
    assert dat.eshift == eshift
