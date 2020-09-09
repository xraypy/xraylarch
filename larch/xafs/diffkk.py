
import time
import numpy as np
from scipy.special import erfc

from larch import Group
from larch.math import interp
from larch.utils.show import show

from .mback import mback

try:
    from larch.wxlib   import _newplot, _plot
    HASPLOT = True
except:
    HASPLOT = False

pi = np.pi

TINY = 1e-20
FOPI = 4/pi
MAXORDER = 6

##
## to test the advantage of the vectorized MacLaurin series algorithm:
##
#     import time
#     a=read_ascii('/home/bruce/git/demeter/examples/cu/cu10k.dat')
#
#     b=diffkk(a.energy, a.xmu, e0=8979, z=29, order=4, form='mback')
#     start = time.clock()
#     for i in range(10):
#         b.kktrans()
#     endfor
#     finish = time.clock()
#     print(finish - start)
#
#     start = time.clock()
#     for i in range(10):
#         b.kktrans(how='sca')
#     endfor
#     finish = time.clock()
#     print(finish - start)
##
## I got 7.6 seconds and 76.1 seconds for 10 iterations of each.  Awesome!
##


###
###  These are the scalar forms of the MacLaurin series algorithm as originally coded up by Matt
###  see https://github.com/newville/ifeffit/blob/master/src/diffkk/kkmclr.f,
###      https://github.com/newville/ifeffit/blob/master/src/diffkk/kkmclf.f,
###  and https://gist.github.com/maurov/33997083e96ab4036fe7
###  The last one is a direct translation of Fortan to python, written by Matt, and used in
###  CARD (http://www.esrf.eu/computing/scientific/CARD/CARD.html)
###
###  See below for vector forms (much faster!)
###
def kkmclf_sca(e, finp):
    """
    forward (f'->f'') kk transform, using mclaurin series algorithm

    arguments:
    npts   size of arrays to consider
    e      energy array *must be on an even grid with an even number of points* [npts] (in)
    finp   f' array [npts] (in)
    fout   f'' array [npts] (out)
    notes  fopi = 4/pi
    """
    npts = len(e)
    if npts != len(finp):
        Exception("Input arrays not of same length in kkmclf_sca")
    if npts < 2:
        Exception("Array too short in kkmclf_sca")
    if npts % 2:
        Exception("Array has an odd number of elements in kkmclf_sca")
    fout = [0.0]*npts
    if npts >= 2:
        factor = FOPI * (e[npts-1] - e[0]) / (npts - 1)
        nptsk = npts / 2
        for i in range(npts):
            fout[i] = 0.0
            ei2 = e[i]*e[i]
            ioff = i%2 - 1
            for k in range(nptsk):
                j = k + k + ioff
                de2 = e[j]*e[j] - ei2
                if abs(de2) <= TINY:
                    de2 = TINY
                fout[i] = fout[i] + finp[j]/de2
            fout[i] *= factor*e[i]
    return fout

def kkmclr_sca(e, finp):
    """
    reverse (f''->f') kk transform, using maclaurin series algorithm

    arguments:
    npts   size of arrays to consider
    e      energy array *must be on a even grid with an even number of points* [npts] (in)
    finp   f'' array [npts] (in)
    fout   f' array [npts] (out)
    m newville jan 1997
    """
    npts = len(e)
    if npts != len(finp):
        Exception("Input arrays not of same length in kkmclr")
    if npts < 2:
        Exception("Array too short in kkmclr")
    if npts % 2:
        Exception("Array has an odd number of elements in kkmclr")
    fout = [0.0]*npts

    factor = -FOPI * (e[npts-1] - e[0]) / (npts - 1)
    nptsk  = npts / 2
    for i in range(npts):
        fout[i] = 0.0
        ei2 = e[i]*e[i]
        ioff = i%2 - 1
        for k in range(nptsk):
            j = k + k + ioff
            de2 = e[j]*e[j] - ei2
            if abs(de2) <= TINY:
                de2 = TINY
            fout[i] = fout[i] + e[j]*finp[j]/de2
        fout[i] *= factor
    return fout

###
###  These are vector forms of the MacLaurin series algorithm, adapted from Matt's code by Bruce
###  They are about an order of magnitude faster.
###

def kkmclf(e, finp):
    """
    forward (f'->f'') kk transform, using maclaurin series algorithm

    arguments:
      e      energy array *must be on an even grid with an even number of points* [npts] (in)
      finp   f'' array [npts] (in)
      fout   f' array [npts] (out)
    """
    npts = len(e)
    if npts != len(finp):
        Exception("Input arrays not of same length for diff KK transform in kkmclr")
    if npts < 2:
        Exception("Array too short for diff KK transform in kkmclr")
    if npts % 2:
        Exception("Array has an odd number of elements for diff KK transform in kkmclr")

    fout   = np.zeros(npts)
    factor = FOPI * (e[-1] - e[0]) / (npts-1)
    ei2    = e**2
    ioff   = np.mod(np.arange(npts), 2) - 1

    nptsk  = int(npts/2)
    k      = np.arange(nptsk)

    for i in range(npts):
        j    = 2*k + ioff[i]
        de2  = e[j]**2 - ei2[i]
        fout[i] = sum(finp[j]/de2)

    fout = fout * factor
    return fout


def kkmclr(e, finp):
    """
    reverse (f''->f') kk transform, using maclaurin series algorithm

    arguments:
      e      energy array *must be on an even grid with an even number of points* [npts] (in)
      finp   f' array [npts] (in)
      fout   f'' array [npts] (out)
    """
    npts = len(e)
    if npts != len(finp):
        Exception("Input arrays not of same for length diff KK transform in kkmclr")
    if npts < 2:
        Exception("Array too short for diff KK transform in kkmclr")
    if npts % 2:
        Exception("Array has an odd number of elements for diff KK transform in kkmclr")

    fout   = np.zeros(npts)
    factor = -FOPI * (e[-1] - e[0]) / (npts-1)
    ei2    = e**2
    ioff   = np.mod(np.arange(npts), 2) - 1

    nptsk  = int(npts/2)
    k      = np.arange(nptsk)

    for i in range(npts):
        j    = 2*k + ioff[i]
        de2  = e[j]**2 - ei2[i]
        fout[i] = sum(e[j]*finp[j]/de2)

    fout = fout * factor
    return fout


class diffKKGroup(Group):
    """
    A Larch Group for generating f'(E) and f"(E) from a XAS measurement of mu(E).
    """

    def __init__(self, energy=None, mu=None, z=None, edge='K', mback_kws=None, **kws):
        kwargs = dict(name='diffKK')
        kwargs.update(kws)
        Group.__init__(self,  **kwargs)
        self.energy     = energy
        self.mu         = mu
        self.z          = z
        self.edge       = edge
        self.mback_kws  = mback_kws
    def __repr__(self):
        return '<diffKK Group>'


# e0=None, z=None, edge=None, order=3, form='mback', whiteline=False, how=None
    def kk(self, energy=None, mu=None, z=None, edge='K', how='scalar', mback_kws=None):
        """
        Convert mu(E) data into f'(E) and f"(E).  f"(E) is made by
        matching mu(E) to the tabulated values of the imaginary part
        of the scattering factor (Cromer-Liberman), f'(E) is then
        obtained by performing a differential Kramers-Kronig transform
        on the matched f"(E).

          Attributes
            energy:     energy array
            mu:         array with mu(E) data
            z:          Z number of absorber
            edge:       absorption edge, usually 'K' or 'L3'
            mback_kws:  arguments for the mback algorithm

          Returns
            self.f1, self.f2:  CL values over on the input energy grid
            self.fp, self.fpp: matched and KK transformed data on the input energy grid

        References:
          * Cromer-Liberman: http://dx.doi.org/10.1063/1.1674266
          * KK computation: Ohta and Ishida, Applied Spectroscopy 42:6 (1988) 952-957
          * diffKK implementation: http://dx.doi.org/10.1103/PhysRevB.58.11215
          * MBACK (Weng, Waldo, Penner-Hahn): http://dx.doi.org/10.1086/303711
          * Lee and Xiang: http://dx.doi.org/10.1088/0004-637X/702/2/970

        """

        if type(energy).__name__ == 'ndarray': self.energy = energy
        if type(mu).__name__     == 'ndarray': self.mu     = mu
        if z    != None: self.z    = z
        if edge != None: self.edge = edge
        if mback_kws != None: self.mback_kws = mback_kws

        if self.z == None:
            Exception("Z for absorber not provided for diffKK")
        if self.edge == None:
            Exception("absorption edge not provided for diffKK")

        mb_kws = dict(order=3, z=self.z, edge=self.edge, e0=None,
                      leexiang=False, tables='chantler',
                      fit_erfc=False, return_f1=True)
        if self.mback_kws is not None:
            mb_kws.update(self.mback_kws)

        start = time.monotonic()

        mback(self.energy, self.mu, group=self, **mb_kws)

        ## interpolate matched data onto an even grid with an even number of elements (about 1 eV)
        npts = int(self.energy[-1] - self.energy[0]) + (int(self.energy[-1] - self.energy[0])%2)
        self.grid = np.linspace(self.energy[0], self.energy[-1], npts)
        fpp = interp(self.energy, self.f2-self.fpp, self.grid, fill_value=0.0)

        ## do difference KK
        if repr(how).startswith('sca'):
            fp = kkmclr_sca(self.grid, fpp)
        else:
            fp = kkmclr(self.grid, fpp)

        ## interpolate back to original grid and add diffKK result to f1 to make fp array
        self.fp = self.f1 + interp(self.grid, fp, self.energy, fill_value=0.0)

        ## clean up group
        #for att in ('normalization_function', 'weight', 'grid'):
        #    if hasattr(self, att): delattr(self, att)
        finish = time.monotonic()
        self.time_elapsed = float(finish-start)

def diffkk(energy=None, mu=None, z=None, edge='K', mback_kws=None, **kws):
    """
    Make a diffKK group given mu(E) data

      Attributes
        energy:     energy array
        mu:         array with mu(E) data
        z:          Z number of absorber
        edge:       absorption edge, usually 'K' or 'L3'
        mback_kws:  arguments for the mback algorithm
    """
    return diffKKGroup(energy=energy, mu=mu, z=z, mback_kws=mback_kws)
