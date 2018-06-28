import numpy as np

from larch import (Group, Make_CallArgs, ValidateLarchPlugin,
                   parse_group_args)

from larch.utils import index_of
from larch_plugins.xafs.xafsutils import ktoe, etok

@ValidateLarchPlugin
@Make_CallArgs(["energy","mu"])
def rebin_xafs(energy, mu, group=None, e0=None, pre1=None, pre2=-30,
               pre_step=2, xanes_step=None, exafs1=15, exafs2=None,
               exafs_kstep=0.05, _larch=None):
   """rebin XAFS energy and ydata to a 'standard 3 region XAFS scan'

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
       input energy correspond to each bin in the new energy array. the
       centroid of the input mu in each segment will be used for mu.

    """

   energy, mu, group = parse_group_args(energy, members=('energy', 'mu'),
                                        defaults=(mu,), group=group,
                                        fcn_name='rebin_xafs')

   if pre1 is None:
       pre1 = pre_step*int((min(energy) - e0)/pre_step)

   if exafs2 is None:
       exafs2 = max(energy) - e0

   # this is all for xanes step size:
   #  find mean of energy difference, ignoring first/last 1% of energies
   npts = len(energy)
   n1 = max(2, int(npts/100.0))
   de_mean = np.diff(energy[n1:-n1]).mean()
   xanes_step_def = max(0.1, 0.05 * (1 + int(de_mean/0.05)))
   if xanes_step is None:
       xanes_step = xanes_step_def
   else:
       xanes_step = max(xanes_step, xanes_step_def)

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

   bounds = [index_of(energy, e) for e in en]
   mout = []
   j0 = 0
   for i in range(len(en)):
       if i == len(en) - 1:
           j1 = len(energy) - 1
       else:
           j1 = int((bounds[i] + bounds[i+1] + 1)/2.0)
       cen = (ydata[j0:j1]*energy[j0:j1]).mean()/energy[j0:j1].mean()
       mout.append(cen)
       j0 = j1
   group.rebinned = Group(energy=array(enout), mu=array(mount), e0=e0)
   return


def registerLarchPlugin():
    return ('_xafs', {'rebin_xafs': rebin_xafs})
