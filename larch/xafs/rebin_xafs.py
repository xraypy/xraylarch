import numpy as np

from larch import Group, Make_CallArgs, parse_group_args
from larch.math import index_of, interp1d, remove_dups
from .xafsutils import ktoe, etok

@Make_CallArgs(["energy", "mu"])
def sort_xafs(energy, mu=None, group=None, fix_repeats=True, overwrite=True):
    """sort energy, mu pair of XAFS data so that energy is monotonically increasing

    Arguments
    ---------
    energy       input energy array
    mu           input mu array
    group        output group
    fix_repeats  bool, whether to fix repeated energies
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

    indices = np.argsort(energy)
    new_energy  = energy[indices]
    new_mu  = mu[indices]

    if fix_repeats:
        new_energy = remove_dups(new_energy)

    if not overwrite:
        group.sorted = Group(energy=new_energy, mu=new_mu)
    else:
        group.energy = new_energy
        group.mu = new_mu
    return


@Make_CallArgs(["energy", "mu"])
def rebin_xafs(energy, mu=None, group=None, e0=None, pre1=None, pre2=-30,
               pre_step=2, xanes_step=None, exafs1=15, exafs2=None,
               exafs_kstep=0.05, method='centroid'):
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
    method       one of 'boxcar', 'centroid' ['centroid']

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

     2 If xanes_step is None, it will be found from the data.  If it is
       given, it may be increased to better fit the input energy array.

     3 The EXAFS region will be spaced in k-space

     4 The rebinned data is found by determining which segments of the
       input energy correspond to each bin in the new energy array. That
       is, each input energy is assigned to exactly one bin in the new
       array.  For each new energy bin, the new value is selected from the
       data in the segment as either
         a) linear interpolation if there are fewer than 3 points in the segment.
         b) mean value ('boxcar')
         c) centroid ('centroid')

    """
    energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                         defaults=(mu,), group=group,
                                        fcn_name='rebin_xafs')

    if e0 is None:
        e0 = getattr(group, 'e0', None)

    if e0 is None:
        raise ValueError("need e0")

    if pre1 is None:
        pre1 = pre_step*int((min(energy) - e0)/pre_step)

    if exafs2 is None:
        exafs2 = max(energy) - e0

    # determine xanes step size:
    #  find mean of energy difference, ignoring first/last 1% of energies
    npts = len(energy)
    n1 = max(2, int(npts/100.0))
    de_mean = np.diff(energy[n1:-n1]).mean()
    xanes_step_def = max(0.1, 0.05 * (1 + int(de_mean/0.05)))
    if xanes_step is None:
        xanes_step = xanes_step_def
    else:
        xanes_step = max(xanes_step, xanes_step_def)

    # create new energy array from the 3 segments (pre, xanes, exafs)
    en = []
    for start, stop, step, isk in ((pre1, pre2, pre_step, False),
                                   (pre2, exafs1, xanes_step, False),
                                   (exafs1, exafs2, exafs_kstep, True)):
        if isk:
            start = etok(start)
            stop = etok(stop)
        reg = np.linspace(start+step, stop, int(0.1 + abs(stop-start)/step))
        if isk:
            reg = ktoe(reg)
        en.extend(e0 + reg)

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
        # if not enough points in segment, do interpolation
        if (j1 - j0) < 3:
            jx = j1 + 1
            if (jx - j0) < 2:
                jx += 1
            val = interp1d(energy[j0:jx], mu[j0:jx], en[i])
            err = mu[j0:j1].std()
        else:
            if method.startswith('box'):
                val =  mu[j0:j1].mean()
            else:
                val = (mu[j0:j1]*energy[j0:j1]).mean()/energy[j0:j1].mean()
        mu_out.append(val)
        err_out.append(mu[j0:j1].std())
        j0 = j1

    newname = group.__name__ + '_rebinned'
    group.rebinned = Group(energy=np.array(en), mu=np.array(mu_out),
                           delta_mu=np.array(err_out), e0=e0,
                           __name__=newname)
    return
