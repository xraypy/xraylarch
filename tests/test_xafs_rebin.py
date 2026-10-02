#!/usr/bin/env python
"""tests for rebin_xafs: equivalence with the original (loop-based)
implementation, and a timing report on the example data

the timing report is skipped by default, run it with:
    LARCH_REBIN_TIMING=1 pytest -s tests/test_xafs_rebin.py -k timing
"""
import os
import timeit
from pathlib import Path

import numpy as np
import pytest
from scipy.interpolate import CubicSpline

from larch import Group
from larch.io import read_ascii
from larch.math import index_of, interp1d
from larch.xafs import find_e0, rebin_xafs
from larch.xafs.xafsutils import ktoe, etok, ETOK

DATADIR = Path(__file__).parent.parent / 'examples' / 'xafsdata'

# file name, numerator, denominator (None: column is mu),
# mu = log(num/den) for transmission
EXAMPLE_FILES = [('cu_rt01.xmu', 'mu', None),
                 ('fe2o3_rt1.xmu', 'mu', None),
                 ('cu_10k.xmu', 'mu', None),
                 ('cu_metal_rt.xdi', 'mutrans', None),
                 ('fe3c_rt.xdi', 'mutrans', None),
                 ('ni_metal_rt.xdi', 'mutrans', None),
                 ('pt_metal_rt.xdi', 'i0', 'itrans'),
                 ('se_na2so4_rt.xdi', 'i0', 'itrans'),
                 ('v_foil.xdi', 'i0', 'i1'),
                 ('znse_zn_xafs.001', 'i0', 'i1'),
                 ('mn_cpmnco3.dat', 'xmu_trans', None)]

METHODS = ('boxcar', 'centroid', 'spline')

# famewoks default parameters
TEST_KWS = dict(pre1=None, pre2=-30, pre_step=2, xanes_step=None,
                    exafs1=15, exafs2=None, exafs_kstep=0.05)


def _rebin_xafs_reference(energy, mu, group, e0=None, pre1=None, pre2=-30,
                          pre_step=2, xanes_step=None, exafs1=15, exafs2=None,
                          exafs_kstep=0.05, method='boxcar'):
    """verbatim copy of the original rebin_xafs (xraylarch 8d6cd41c),
    without the group argument parsing"""
    if e0 is None:
        e0 = getattr(group, 'e0', None)

    if e0 is None:
        raise ValueError("need e0")

    emin = min(energy) - e0
    emax = max(energy) - e0

    if pre1 is None:
        pre1 = pre_step*int(emin/pre_step)

    if exafs2 is None:
        exafs2 = emax

    # determine xanes step size:
    #  find mean of energy difference within 10 eV of E0
    if xanes_step is None:
        xanes_step = 0.05 * max(1, int(e0 / 1250.0))  # E0/25000, round down to 0.05

    # clip into data range
    pre1 = max(pre1, emin)
    pre2 = min(max(pre2, pre1 + abs(pre_step)), emax)
    exafs1 = min(max(exafs1, pre2 + abs(xanes_step)), emax)
    exafs2 = min(max(exafs2, exafs1 + abs(exafs_kstep) * 20), emax)

    # enforce monotonically increasing
    if pre2 <= pre1:
        pre2 = min(pre1 + abs(pre_step), emax)
    if exafs1 <= pre2:
        exafs1 = min(pre2 + abs(xanes_step), emax)
    if exafs2 <= exafs1:
        exafs2 = min(exafs1 + abs(exafs_kstep) * 20, emax)

    # create new energy array from the 3 segments (pre, xanes, exafs)
    # pre:   (pre1 -> pre2) with pre_step (in E-space)
    # xanes: (pre2 -> exafs1) with xanes_step (in E-space)
    # exafs: (exafs1 -> exafs2) with exafs_kstep (in k-space)
    en = []
    for start, stop, step, isk in ((pre1, pre2, pre_step, False),
                                   (pre2, exafs1, xanes_step, False),
                                   (exafs1, exafs2, exafs_kstep, True)):
        if start == stop:
            continue

        if isk:
            start = etok(start)
            stop = etok(stop)

        npts = 1 + int(0.1  + abs(stop - start) / step)
        reg = np.linspace(start, stop, npts)
        if isk:
            reg = ktoe(reg)
        en.extend(e0 + reg[:-1])

    # find the segment boundaries of the old energy array
    bounds = [index_of(energy, e) for e in en]
    mu_out = []
    err_out = []

    j0 = 0
    for i in range(len(en)):
        if i == len(en) - 1:
            j1 = len(energy) - 1
        else:
            j1 = int((bounds[i] + bounds[i+1] + 1)/2.0)
        if i == 0 and j0 == 0:
            j0 = index_of(energy, en[0]-5)
        # if not enough points in segment, do interpolation
        # print(i, en[i], j0, j1,  len(energy[j0:j1]))
        if (j1 - j0) < 3:
            jx = j1 + 1
            if (jx - j0) < 3:
                jx += 1

            val = interp1d(energy[j0:jx], mu[j0:jx], en[i])
            err = mu[j0:jx].std()
            if np.isnan(val):
                j0 = max(0, j0-1)
                jx = min(len(energy), jx+1)
                val = interp1d(energy[j0:jx], mu[j0:jx], en[i])
                err = mu[j0:jx].std()  # noqa: F841
        else:
            if method.startswith('box'):
                val =  mu[j0:j1].mean()
            elif method.startswith('spl'):
                val = CubicSpline(energy[j0:j1], mu[j0:j1])(en[i])
            else:
                val = (mu[j0:j1]*energy[j0:j1]).mean()/energy[j0:j1].mean()
        mu_out.append(val)
        if j0 == j1:
            err_out.append(np.nan)
        else:
            err_out.append(mu[j0:j1].std())
        j0 = j1

    newname = group.__name__ + '_rebinned'
    group.rebinned = Group(energy=np.array(en), mu=np.array(mu_out),
                           delta_mu=np.array(err_out), e0=e0,
                           __name__=newname)
    return


def read_example(fname, num, den):
    """read an example data file, return a group with energy, mu, e0"""
    dat = read_ascii(DATADIR / fname)
    energy = dat.energy if hasattr(dat, 'energy') else dat.e
    if den is None:
        mu = getattr(dat, num)
    else:
        mu = np.log(getattr(dat, num) / getattr(dat, den))
    group = Group(energy=1.0*energy, mu=1.0*mu, __name__=fname)
    group.e0 = find_e0(group.energy, group.mu)
    return group


def synthetic_group(e0, npts, nonuniform=False, seed=0):
    """XAS-like spectrum: arctan edge + EXAFS-like oscillation + noise"""
    rng = np.random.default_rng(seed)
    if nonuniform:
        # typical step scan: coarse pre-edge, fine XANES, k-spaced EXAFS
        pre = np.arange(e0-200, e0-30, 5.0)
        xan = np.arange(e0-30, e0+30, 0.3)
        kex = np.arange(etok(30), 16, 0.04)
        energy = np.concatenate((pre, xan, e0 + ktoe(kex)))
        energy = energy + rng.normal(scale=0.01, size=len(energy))
        energy.sort()
    else:
        energy = np.linspace(e0-200, e0+1000, npts)
    xe = energy - e0
    k = np.sqrt(ETOK*np.where(xe > 0, xe, 0))
    mu = (0.2 + 1.0e-4*xe + np.arctan(xe/2.0)/np.pi + 0.5
          + 0.05*np.sin(2*2.5*k)*np.exp(-0.01*k*k)*(xe > 0)
          + rng.normal(scale=2e-3, size=len(energy)))
    group = Group(energy=energy, mu=mu, __name__=f'syn_{e0}_{len(energy)}')
    group.e0 = find_e0(group.energy, group.mu)
    return group


def check_same(group, **kws):
    """run the reference and the new rebin_xafs and compare the results.
    if the reference raises an exception, the new version must raise the
    same exception type"""
    ref = Group(__name__=group.__name__, e0=group.e0)
    try:
        _rebin_xafs_reference(group.energy, group.mu, ref, **kws)
    except Exception as exc:
        with pytest.raises(type(exc)):
            rebin_xafs(group.energy, group.mu, group=group, **kws)
        return
    rebin_xafs(group.energy, group.mu, group=group, **kws)
    assert_same(ref.rebinned, group.rebinned)


def assert_same(ref, new):
    assert new.__name__ == ref.__name__
    assert new.e0 == ref.e0
    for attr in ('energy', 'mu', 'delta_mu'):
        a, b = getattr(ref, attr), getattr(new, attr)
        assert a.shape == b.shape, attr
        assert np.array_equal(np.isnan(a), np.isnan(b)), attr
        np.testing.assert_allclose(b, a, rtol=1e-12, atol=0,
                                   equal_nan=True, err_msg=attr)


# each example file with one method, in turn
EXAMPLE_CASES = [(*args, METHODS[i % len(METHODS)])
                 for i, args in enumerate(EXAMPLE_FILES)]


@pytest.mark.parametrize('fname,num,den,method', EXAMPLE_CASES)
def test_rebin_examples(fname, num, den, method):
    group = read_example(fname, num, den)
    check_same(group, method=method, **TEST_KWS)


SYNTH_KWS = [TEST_KWS,
             dict(pre1=-150, pre2=-30, pre_step=5, xanes_step=0.3,
                  exafs1=15, exafs2=None, exafs_kstep=0.05),
             dict(pre1=None, pre2=-15, pre_step=2, xanes_step=None,
                  exafs1=25, exafs2=None, exafs_kstep=0.05),
             dict(pre1=-100, pre2=-20, pre_step=1, xanes_step=0.3,
                  exafs1=30, exafs2=800, exafs_kstep=0.1)]


# (e0, npts, nonuniform, kws, method): instead of the full product, each
# e0, data spacing, keywords set and method appears at least once
SYNTH_CASES = [(7112.0, 0, True, 3, 'boxcar'),
               (7112.0, 500, False, 1, 'spline'),
               (8979.0, 500, False, 0, 'centroid'),
               (8979.0, 0, True, 2, 'spline'),
               (8979.0, 3000, False, 3, 'boxcar'),
               (26711.0, 3000, False, 2, 'spline'),
               (26711.0, 0, True, 1, 'centroid')]


@pytest.mark.parametrize('e0,npts,nonuniform,ikws,method', SYNTH_CASES)
def test_rebin_synthetic(e0, npts, nonuniform, ikws, method):
    group = synthetic_group(e0, npts, nonuniform=nonuniform)
    check_same(group, method=method, **SYNTH_KWS[ikws])


@pytest.mark.parametrize('method', METHODS)
def test_rebin_edge_cases(method):
    # data starting after e0 + pre1
    grp = synthetic_group(8979.0, 800)
    check_same(grp, method=method, pre1=-300)

    # data ending before the EXAFS region
    grp = synthetic_group(8979.0, 800)
    sel = grp.energy < grp.e0 + 10
    grp = Group(energy=grp.energy[sel], mu=grp.mu[sel], e0=grp.e0,
                __name__='short')
    check_same(grp, method=method)

    # duplicated energy values
    grp = synthetic_group(8979.0, 500)
    energy = grp.energy.copy()
    energy[100:300:7] = energy[99:299:7]
    energy[250] = energy[251] = energy[252]
    grp.energy = energy
    check_same(grp, method=method)

    # non-monotonic energy (fallback path)
    grp = synthetic_group(8979.0, 500)
    energy = grp.energy.copy()
    energy[200], energy[201] = energy[201], energy[200]
    energy[400] = energy[350]
    grp.energy = energy
    check_same(grp, method=method)

    # NaN in mu
    for npts in (500, 3000):
        grp = synthetic_group(8979.0, npts)
        grp.mu[[10, 150, 151, 220, 260, 400]] = np.nan
        # (CubicSpline refuses NaN: the spline method may raise)
        check_same(grp, method=method, **TEST_KWS)


def time_call(func, ncalls, repeat=5):
    """median time per call in ms"""
    timer = timeit.Timer(func)
    return 1000*np.median(timer.repeat(repeat=repeat, number=ncalls))/ncalls


@pytest.mark.skipif(not os.environ.get('LARCH_REBIN_TIMING'),
                    reason='benchmark: set LARCH_REBIN_TIMING=1 to run')
def test_rebin_timing_report():
    """report time per call of the reference and the new rebin_xafs"""
    groups = [read_example(*args) for args in EXAMPLE_FILES]
    groups.append(synthetic_group(26711.0, 3000))
    lines = [f"{'data':22s} {'npts':>5s} {'method':9s} "
             f"{'ref (ms)':>9s} {'new (ms)':>9s} {'speedup':>8s}"]
    for group in groups:
        for method in METHODS:
            ref = Group(__name__=group.__name__, e0=group.e0)
            def run_ref():
                _rebin_xafs_reference(group.energy, group.mu, ref,
                                      method=method, **TEST_KWS)
            def run_new():
                rebin_xafs(group.energy, group.mu, group=group,
                           method=method, **TEST_KWS)
            t_ref = time_call(run_ref, 2, repeat=3)
            t_new = time_call(run_new, 20)
            lines.append(f"{group.__name__:22s} {len(group.energy):5d} "
                         f"{method:9s} {t_ref:9.3f} {t_new:9.3f} "
                         f"{t_ref/t_new:8.1f}")
    print('\nrebin_xafs timing (median per call)\n' + '\n'.join(lines))
