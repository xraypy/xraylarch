
from larch import (Group, Parameter, isParameter, param_value, use_plugin_path, isNamedClass, Interpreter, Minimizer)
use_plugin_path('std')
from show import _show
use_plugin_path('math')
from mathutils import _interp
use_plugin_path('xray')
from cromer_liberman import f1f2
from xraydb_plugin import xray_edge, xray_line
use_plugin_path('xafs')
#from pre_edge import pre_edge
import numpy as np
from scipy.special import erfc
from math import pi

use_plugin_path('wx')
from plotter import (_newplot, _plot)

import time

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
#     print finish - start
#
#     start = time.clock()
#     for i in range(10):
#         b.kktrans(how='sca')
#     endfor
#     finish = time.clock()
#     print finish - start
##
## I got 7.6 seconds and 76.1 seconds for 10 iterations of each.  Awesome!
##


def match_f2(p):
    """Match mu(E) data for tabulated f"(E) using the MBACK algorithm or the Lee & Xiang extension"""
    s      = p.s.value
    a      = p.a.value
    em     = p.em.value
    xi     = p.xi.value
    c0     = p.c0.value
    eoff   = p.e - p.e0.value

    norm = a*erfc((p.e-em)/xi) + c0 # erfc function + constant term of polynomial
    for i in range(MAXORDER):       # successive orders of polynomial
        j = i+1
        attr = 'c%d' % j
        if hasattr(p, attr):
            norm = norm + getattr(getattr(p, attr), 'value') * eoff**j
    func = (p.f2 + norm - s*p.x) * p.theta / p.weight
    if p.form.lower() == 'lee':
        func = func / s*p.x
    return func


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

    nptsk  = npts/2
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

    nptsk  = npts/2
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

    def __init__(self, energy=None, xmu=None, e0=None, z=None, edge='K', order=3, form='mback', whiteline=False, _larch=None, **kws):
        kwargs = dict(name='diffKK')
        kwargs.update(kws)
        Group.__init__(self,  **kwargs)
        self.energy     = energy
        self.xmu        = xmu
        self.e0         = e0
        self.z          = z
        self.edge       = edge
        self.order      = order
        self.form       = form
        self.whiteline  = whiteline

        if _larch == None:
            self._larch   = Interpreter()
        else:
            self._larch = _larch

    def __repr__(self):
        return '<diffKK Group>'


    def __normalize__(self):
        """Match mu(E) data for tabulated f"(E) using the MBACK algorithm or the Lee & Xiang extension"""
        if self.order < 1: self.order = 1 # set order of polynomial
        if self.order > MAXORDER: self.order = MAXORDER


        #toss = Group()
        #pre_edge(self.energy, self.xmu, group=toss,_larch=self._larch, e0=self.e0)
        #self.pre_edge = toss.pre_edge
        #del toss

        n = self.edge
        if self.edge.lower().startswith('l'): n = 'L'
        
        self.params = Group(s      = Parameter(1,      vary=True,  _larch=self._larch), # scale of data
                            a      = Parameter(1,      vary=False,  _larch=self._larch), # amplitude of erfc
                            xi     = Parameter(1,      vary=False,  _larch=self._larch), # width of erfc
                            em     = Parameter(xray_line(self.z, n,         _larch=self._larch)[0], vary=False, _larch=self._larch), # erfc centroid
                            e0     = Parameter(xray_edge(self.z, self.edge, _larch=self._larch)[0], vary=False, _larch=self._larch), # abs. edge energy
                            e      = self.energy,
                            x      = self.xmu,
                            f2     = self.f2,
                            weight = self.weight,
                            theta  = self.theta,
                            form   = self.form,
                            _larch = self._larch)

        for i in range(self.order): # polynomial coefficients
            setattr(self.params, 'c%d' % i, Parameter(0, vary=True, _larch=self._larch))


        fit = Minimizer(match_f2, self.params, _larch=self._larch, toler=1.e-5) 
        fit.leastsq()
        eoff = self.energy - self.params.e0.value
        self.normalization_function = self.params.a.value*erfc((self.energy-self.params.em.value)/self.params.xi.value) + self.params.c0.value
        for i in range(MAXORDER):
            j = i+1
            attr = 'c%d' % j
            if hasattr(self.params, attr):
                self.normalization_function  = self.normalization_function + getattr(getattr(self.params, attr), 'value') * eoff**j
        #if self.form.lower() == 'lee':
        #    self.normalization_function = self.normalization_function / s*p.x

        self.fpp = self.params.s*self.xmu - self.normalization_function
        



    def kk(self, energy=None, xmu=None, e0=None, z=None, edge=None, order=3, form='mback', whiteline=False, how=None):
        """
        Convert mu(E) data into f'(E) and f"(E).  f"(E) is made by
        matching mu(E) to the tabulated values of the imaginary part
        of the scattering factor (Cromer-Liberman), f'(E) is then
        obtained by performing a differential Kramers-Kronig transform 
        on the matched f"(E).

          Attributes
            energy:     energy array
            xmu:        array with mu(E) data
            e0:         edge energy
            z:          Z number of absorber
            order:      order of normalization polynomial (2 to 6)
            form:       functional form of normalization function, "mback" or "lee"
            whiteline   margin around L3/L2 white lines to exclude from determination of
                        normalization, it should be a smallish, positive number, like 20

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
        if type(xmu).__name__    == 'ndarray': self.xmu    = xmu
        if e0   != None: self.e0   = e0
        if z    != None: self.z    = z
        if edge != None: self.edge = edge
        if form != None: self.form = form
        if whiteline:    self.whiteline = whiteline

        if self.z == None:
            Exception("Z for absorber not provided for diffKK")
        if self.e0 == None:
            Exception("e0 value not provided for diffKK")
        if self.edge == None:
            Exception("absorption edge not provided for diffKK")

        start = time.clock()       

        self.theta = np.ones(len(self.energy))
        if self.edge.lower().startswith('l'):
            l2 = xray_edge(self.z, 'L2', _larch=self._larch)[0]
            if self.whiteline:
                theta_pre  = 1*(self.energy<self.e0)
                theta_post = 1*(self.energy>self.e0+float(self.whiteline))
                self.theta = theta_pre + theta_post

                l2_pre  = 1*(self.energy<l2)
                l2_post = 1*(self.energy>l2+float(self.whiteline))
                l2theta = l2_pre + l2_post
                self.theta = self.theta * l2theta


        ## this is used to weight the pre- and post-edge differently in MBACK
        #if self.edge.lower().startswith('k'):
        weight1 = 1*(self.energy<self.e0)
        weight2 = 1*(self.energy>self.e0)
        self.weight = np.sqrt(sum(weight1))*weight1 + np.sqrt(sum(weight2))*weight2

        (self.f1, self.f2) = f1f2(self.z, self.energy, edge=self.edge, _larch=self._larch)

        ## match mu(E) data to f2
        self.__normalize__()

        ## interpolate matched data onto an even grid with an even number of elements (about 1 eV)
        npts = int(self.energy[-1] - self.energy[0]) + (int(self.energy[-1] - self.energy[0])%2)
        self.grid = np.linspace(self.energy[0], self.energy[-1], npts)
        fpp = _interp(self.energy, self.f2-self.fpp, self.grid, fill_value=0.0)

        ## do difference KK
        if repr(how).startswith('sca'):
            fp = kkmclr_sca(self.grid, fpp)
        else:
            fp = kkmclr(self.grid, fpp)

        ## interpolate back to original grid and add diffKK result to f1 to make fp array
        self.fp = self.f1 + _interp(self.grid, fp, self.energy, fill_value=0.0)

        ## clean up group
        #for att in ('normalization_function', 'weight', 'grid'):
        #    if hasattr(self, att): delattr(self, att)
        finish = time.clock()
        self.time_elapsed = float(finish-start)


    def plotkk(self):
        """
        Make a quick-n-dirty plot of the output of the KK transform.
        """
        _newplot(self.energy, self.f2, _larch=self._larch, label='f2', xlabel='Energy (eV)', ylabel='scattering factors',
                 show_legend=True, legend_loc='lr')
        _plot(self.energy, self.fpp, _larch=self._larch, label='f"(E)')
        _plot(self.energy, self.f1,  _larch=self._larch, label='f1')
        _plot(self.energy, self.fp,  _larch=self._larch, label='f\'(E)')


def diffkk(energy=None, xmu=None, e0=None, z=None, edge='K', order=3, form='mback', whiteline=False, _larch=None, **kws):
    """
    Make a diffKK group given mu(E) data

      Attributes
        energy:     energy array
        xmu:        array with mu(E) data
        e0:         edge energy
        z:          Z number of absorber
        order:      order of normalization polynomial (2 to 6)
        form:       functional form of normalization function, "mback" or "lee"
        whiteline:  margin around L3/L2 white lines to exclude from determination of
                    normalization, it should be a smallish, positive number, like 20

    """
    return diffKKGroup(energy=energy, xmu=xmu, e0=e0, z=z, edge=edge, order=order, form=form, whiteline=whiteline, _larch=_larch)
    
    
def registerLarchPlugin(): # must have a function with this name!
    return ('_xafs', { 'diffkk': diffkk })
    
