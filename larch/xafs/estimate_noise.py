#!/usr/bin/env python
"""
  Estimate Noise in an EXAFS spectrum
"""
from numpy import pi, sqrt, where

from larch import parse_group_args, Group, isgroup

from larch.math import index_of, realimag
from .xafsutils import set_xafsGroup
from .xafsft import xftf, xftr

def estimate_noise(k, chi=None, group=None, rmin=15.0, rmax=30.0,
                   kweight=1, kmin=0, kmax=20, dk=4, dk2=None, kstep=0.05,
                   kwindow='kaiser', nfft=2048, _larch=None, **kws):
    """
    estimate noise levels in EXAFS spectrum and estimate highest k
    where data is above the noise level
    Parameters:
    -----------
      k:        1-d array of photo-electron wavenumber in Ang^-1 (or group)
      chi:      1-d array of chi
      group:    output Group  [see Note below]
      rmin:     minimum R value for high-R region of chi(R)
      rmax:     maximum R value for high-R region of chi(R)
      kweight:  exponent for weighting spectra by k**kweight [1]
      kmin:     starting k for FT Window [0]
      kmax:     ending k for FT Window  [20]
      dk:       tapering parameter for FT Window [4]
      dk2:      second tapering parameter for FT Window [None]
      kstep:    value to use for delta_k ( Ang^-1) [0.05]
      window:   name of window type ['kaiser']
      nfft:     value to use for N_fft [2048].

    Returns:
    ---------
      None   -- outputs are written to supplied group.  Values (scalars) written
      to output group:
        epsilon_k     estimated noise in chi(k)
        epsilon_r     estimated noise in chi(R)
        kmax_suggest  highest estimated k value where |chi(k)| > epsilon_k

    Notes:
    -------

     1. This method uses the high-R portion of chi(R) as a measure of the noise
        level in the chi(R) data and uses Parseval's theorem to convert this noise
        level to that in chi(k).  This method implicitly assumes that there is no
        signal in the high-R portion of the spectrum, and that the noise in the
        spectrum s "white" (independent of R) .  Each of these assumptions can be
        questioned.
     2. The estimate for 'kmax_suggest' has a tendency to be fair but pessimistic
        in how far out the chi(k) data goes before being dominated by noise.
     3. Follows the 'First Argument Group' convention, so that you can either
        specifiy all of (an array for 'k', an array for 'chi', option output Group)
        OR pass a group with 'k' and 'chi' as the first argument
    """
    k, chi, group = parse_group_args(k, members=('k', 'chi'),
                                     defaults=(chi,), group=group,
                                     fcn_name='esitmate_noise')



    # save _sys.xafsGroup -- we want to NOT write to it here!
    savgroup = set_xafsGroup(None, _larch=_larch)
    tmpgroup = Group()
    rmax_out = min(10*pi, rmax+2)

    xftf(k, chi, kmin=kmin, kmax=kmax, rmax_out=rmax_out,
         kweight=kweight, dk=dk, dk2=dk2, kwindow=kwindow,
         nfft=nfft, kstep=kstep, group=tmpgroup, _larch=_larch)

    chir  = tmpgroup.chir
    rstep = tmpgroup.r[1] - tmpgroup.r[0]

    irmin = int(0.01 + rmin/rstep)
    irmax = min(nfft/2,  int(1.01 + rmax/rstep))
    highr = realimag(chir[irmin:irmax])

    # get average of window function value, scale eps_r scale by this
    # this is imperfect, but improves the result.
    kwin_ave = tmpgroup.kwin.sum()*kstep/(kmax-kmin)
    eps_r = sqrt((highr*highr).sum() / len(highr)) / kwin_ave

    # use Parseval's theorem to convert epsilon_r to epsilon_k,
    # compensating for kweight
    w = 2 * kweight + 1
    scale = sqrt((2*pi*w)/(kstep*(kmax**w - kmin**w)))
    eps_k = scale*eps_r

    # do reverse FT to get chiq array
    xftr(tmpgroup.r, tmpgroup.chir, group=tmpgroup, rmin=0.5, rmax=9.5,
         dr=1.0, window='parzen', nfft=nfft, kstep=kstep, _larch=_larch)

    # sets kmax_suggest to the largest k value for which
    # | chi(q) / k**kweight| > epsilon_k
    iq0 = index_of(tmpgroup.q, (kmax+kmin)/2.0)
    tst = tmpgroup.chiq_mag[iq0:] / ( tmpgroup.q[iq0:])**kweight
    kmax_suggest = tmpgroup.q[iq0 + where(tst < eps_k)[0][0]]

    # restore original _sys.xafsGroup, set output variables
    _larch.symtable._sys.xafsGroup = savgroup
    group = set_xafsGroup(group, _larch=_larch)
    group.epsilon_k = eps_k
    group.epsilon_r = eps_r
    group.kmax_suggest = kmax_suggest
