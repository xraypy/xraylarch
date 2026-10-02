import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.interpolate import CubicSpline

from larch import Group
from larch.larchlib import Make_CallArgs, parse_group_args
from larch.math import (index_of, interp1d,
                        remove_dups, remove_nans, remove_nans2)
from .xafsutils import ktoe, etok, TINY_ENERGY

@Make_CallArgs(["energy", "mu"])
def sort_xafs(energy: ArrayLike | Group, mu: ArrayLike | None = None,
              group: Group | None = None, fix_repeats: bool = True,
              remove_nans: bool = True, overwrite: bool = True) -> None:
    """sort energy, mu pair of XAFS data so that energy is monotonically increasing

    Arguments
    ---------
    energy       input energy array
    mu           input mu array
    group        output group
    fix_repeats  bool, whether to fix repeated energies [True]
    remove_nans  bool, whether to fix nans [True]
    overwrite    bool, whether to overwrite arrays [True]

    Returns
    -------
      None

    if overwrite is False, a group named 'sorted' will be created
    in the output group, with sorted energy and mu arrays

    (if the output group is None, _sys.xafsGroup will be written to)

    """
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                         fcn_name='sort_xafs')
    energy = np.asarray(energy)
    mu = np.asarray(mu)

    indices = np.argsort(energy)
    new_energy  = energy[indices]
    new_mu  = mu[indices]

    if fix_repeats:
        new_energy = remove_dups(new_energy, tiny=TINY_ENERGY)
    if remove_nans:
        if (len(np.where(~np.isfinite(new_energy))[0]) > 0 or
            len(np.where(~np.isfinite(new_mu))[0] > 0)):
            new_energy, new_mu = remove_nans2(new_energy, new_mu)

    if not overwrite:
        group.sorted = Group(energy=new_energy, mu=new_mu)
    else:
        group.energy = new_energy
        group.mu = new_mu
    return


@Make_CallArgs(["energy", "mu"])
def rebin_xafs(energy: ArrayLike | Group, mu: ArrayLike | None = None,
               group: Group | None = None, e0: float | None = None,
               pre1: float | None = None, pre2: float = -30,
               pre_step: float = 2, xanes_step: float | None = None,
               exafs1: float = 15, exafs2: float | None = None,
               exafs_kstep: float = 0.05, method: str = 'boxcar') -> None:
    """rebin XAFS energy and mu to a 'standard 3 region XAFS scan'

    Arguments
    ---------
    energy       input energy array
    mu           input mu array
    group        output group
    e0           energy reference -- all energy values are relative to this
    pre1         start of pre-edge region [1st energy point]
    pre2         end of pre-edge region, start of XANES region [-30]
    pre_step     energy step for pre-edge region [2]
    xanes_step   energy step for XANES region [see note]
    exafs1       end of XANES region, start of EXAFS region [15]
    exafs2       end of EXAFS region [last energy point]
    exafs_kstep  k-step for EXAFS region [0.05]
    method       one of 'spline, 'boxcar', 'centroid' ['boxcar']


    Returns
    -------
      None

    A group named 'rebinned' will be created in the output group, with the
    following  attributes:
        energy  new energy array
        mu      mu for energy array
        e0      e0 copied from current group

    (if the output group is None, _sys.xafsGroup will be written to)

    Notes
    ------
     1 If the first argument is a Group, it must contain 'energy' and 'mu'.
       See First Argrument Group in Documentation

     2 If xanes_step is None, it will be found from the data as E0/25000,
       truncated down to the nearest 0.05: xanes_step = 0.05*max(1, int(e0/1250.0))


     3 The EXAFS region will be spaced in k-space

     4 The rebinned data is found by determining which segments of the
       input energy correspond to each bin in the new energy array. That
       is, each input energy is assigned to exactly one bin in the new
       array.  For each new energy bin, the new value is selected from the
       data in the segment as either
         a) linear interpolation if there are fewer than 3 points in the segment.
         b) spline interpolation ('spline')
         c) mean value ('boxcar')
         c) centroid ('centroid')

    """
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                        fcn_name='rebin_xafs')

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
    elist: list[float] = []
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
        elist.extend(e0 + reg[:-1])

    energy = np.asarray(energy)
    mu = np.asarray(mu)
    en = np.asarray(elist, dtype=float)
    mu_out: NDArray[np.float64] | list[float] | None = None
    err_out: NDArray[np.float64] | list[float] | None = None
    if len(en) > 0 and len(energy) > 1 and np.all(np.diff(energy) >= 0):
        mu_out, err_out = _rebin_sorted(energy, mu, en, method)
    if mu_out is None:
        mu_out, err_out = _rebin_loop(energy, mu, en, method)

    newname = group.__name__ + '_rebinned'
    group.rebinned = Group(energy=np.array(en), mu=np.array(mu_out),
                           delta_mu=np.array(err_out), e0=e0,
                           __name__=newname)
    return


def _rebin_loop(energy: NDArray[np.float64], mu: NDArray[np.float64],
                en: NDArray[np.float64],
                method: str) -> tuple[list[float], list[float]]:
    """rebin energy, mu onto en, one bin at a time (works for unsorted energy)

    returns lists of mu and delta_mu values
    """
    # find the segment boundaries of the old energy array
    bounds = [index_of(energy, e) for e in en]
    mu_out: list[float] = []
    err_out: list[float] = []

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
            if np.isnan(val):
                j0 = max(0, j0-1)
                jx = min(len(energy), jx+1)
                val = interp1d(energy[j0:jx], mu[j0:jx], en[i])
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

    return mu_out, err_out


def _interp_bin(energy: NDArray[np.float64], mu: NDArray[np.float64],
                en: NDArray[np.float64], i: int, j0: int,
                j1: int) -> tuple[float, int]:
    """linear interpolation for bin i, segment energy[j0:j1] with
    fewer than 3 points, as in _rebin_loop

    returns value and (possibly widened) j0
    """
    jx = j1 + 1
    if (jx - j0) < 3:
        jx += 1
    val = interp1d(energy[j0:jx], mu[j0:jx], en[i])
    if np.isnan(val):
        j0 = max(0, j0-1)
        jx = min(len(energy), jx+1)
        val = interp1d(energy[j0:jx], mu[j0:jx], en[i])
    return val, j0


def _rebin_sorted(energy: NDArray[np.float64], mu: NDArray[np.float64],
                  en: NDArray[np.float64], method: str
                  ) -> tuple[NDArray[np.float64], NDArray[np.float64]] | tuple[None, None]:
    """vectorized version of _rebin_loop, for monotonically increasing energy

    gives the same results as _rebin_loop, or (None, None) if
    the bins cannot be found this way
    """
    npts, nbins = len(energy), len(en)
    # bin boundaries, as index_of(energy, en) for sorted energy
    bounds = np.clip(np.searchsorted(energy, en, side='right') - 1, 0, None)
    j1 = np.empty(nbins, dtype=int)
    j1[:-1] = (bounds[:-1] + bounds[1:] + 1) // 2
    j1[-1] = npts - 1
    j0 = np.empty(nbins, dtype=int)
    j0[1:] = j1[:-1]
    j0[0] = max(0, np.searchsorted(energy, en[0]-5, side='right') - 1)
    if not (np.all(np.isfinite(en)) and np.all(j1 >= j0)):
        return None, None

    mu_out = np.full(nbins, np.nan)
    err_out = np.full(nbins, np.nan)

    # mean and std of mu in all non-empty segments
    full = j1 > j0
    if full.any():
        jstart = j0[full]
        jend = j1[full][-1]
        nseg = (j1 - j0)[full]
        offsets = jstart - jstart[0]
        mu_seg = mu[jstart[0]:jend]
        mean = np.add.reduceat(mu_seg, offsets) / nseg
        dev = mu_seg - np.repeat(mean, nseg)
        err_out[full] = np.sqrt(np.add.reduceat(dev*dev, offsets) / nseg)
        if method.startswith('box'):
            mu_out[full] = mean
        elif not method.startswith('spl'):
            en_seg = energy[jstart[0]:jend]
            mu_out[full] = ((np.add.reduceat(mu_seg*en_seg, offsets) / nseg) /
                            (np.add.reduceat(en_seg, offsets) / nseg))

    # segments with fewer than 3 points: linear interpolation.
    # the interpolation window is energy[j0:jx], use np.interp on the
    # full arrays where the bracketing points are inside the window.
    small = (j1 - j0) < 3
    jx = j1 + 1
    jx = np.minimum(jx + ((jx - j0) < 3), npts)
    jlo = np.searchsorted(energy, en, side='right') - 1
    val = np.interp(en, energy, mu)
    easy = small & (jlo >= j0) & (jlo <= jx - 2) & ~np.isnan(val)
    mu_out[easy] = val[easy]

    # remaining bins, in order: spline and other interpolations
    if method.startswith('spl'):
        todo = ~easy
    else:
        todo = small & ~easy
    for i in np.where(todo)[0]:
        if small[i]:
            mu_out[i], j0w = _interp_bin(energy, mu, en, i, j0[i], j1[i])
            if j0w != j0[i]:
                err_out[i] = np.nan if j0w == j1[i] else mu[j0w:j1[i]].std()
        else:
            mu_out[i] = CubicSpline(energy[j0[i]:j1[i]], mu[j0[i]:j1[i]])(en[i])
    return mu_out, err_out
