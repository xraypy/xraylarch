#!/usr/bin/env python
"""
feffdat  provides the following function related to
reading and dealing with Feff.data files in larch:

  path1 = read_feffdat('feffNNNN.dat')

returns a Feff Group -- a special variation of a Group -- for
the path represented by the feffNNNN.dat

  group  = ff2chi(pathlist)

creates a group that contains the chi(k) for the sum of paths.
"""

import numpy as np
import sys, os
import larch
from larch.larchlib import Parameter, param_value, plugin_path

sys.path.insert(0, plugin_path('std'))
sys.path.insert(0, plugin_path('xafs'))

from xafsutils import ETOK

SMALL = 1.e-6

class FeffDatFile(object):
    def __init__(self, filename=None):
        if filename is not None:
            self.read(filename)

    def read(self, filename):
        try:
            lines = open(filename, 'r').readlines()
        except:
            print 'Error reading file %s ' % filename
            return
        self.filename = filename
        mode = 'header'
        self.potentials, self.geom = [], []
        data = []
        pcounter = 0
        iline = 0
        for line in lines:
            iline += 1
            line = line[:-1]
            if line.startswith('#'): line = line[1:]
            line = line.strip()
            if iline == 1:
                self.title = line[:64].strip()
                self.version = line[64:].strip()
                continue
            if line.startswith('k') and line.endswith('real[p]@#'):
                mode = 'arrays'
                continue
            elif '----' in line[2:10]:
                mode = 'path'
                continue
            #
            if (mode == 'header' and
                line.startswith('Abs') or line.startswith('Pot')):
                words = line.replace('=', ' ').split()
                ipot, z, rmt, rnm = (0, 0, 0, 0)
                words.pop(0)
                if line.startswith('Pot'):
                    ipot = int(words.pop(0))
                iz = int(words[1])
                rmt = float(words[3])
                rnm = float(words[5])
                self.potentials.append((ipot, iz, rmt, rnm))
            elif mode == 'header' and line.startswith('Gam_ch'):
                words  = line.replace('=', ' ').split(' ', 2)
                self.gam_ch = float(words[1])
                self.exch   = words[2]
            elif mode == 'header' and line.startswith('Mu'):
                words  = line.replace('=', ' ').split()
                self.mu = float(words[1])
                self.kf = float(words[3])
                self.vint = float(words[5])
                self.rs_int= float(words[7])
            elif mode == 'path':
                pcounter += 1
                if pcounter == 1:
                    w = [float(x) for x in line.split()[:5]]
                    self.nleg = int(w.pop(0))
                    self.degen, self.reff, self.rnorman, self.edge = w
                elif pcounter > 2:
                    words = line.split()
                    xyz = [float(x) for x in words[:3]]
                    ipot = int(words[3])
                    iz   = int(words[4])
                    lab = words[5]
                    geom = [lab, iz, ipot] + xyz
                    self.geom.append(tuple(geom))
            elif mode == 'arrays':
                d = np.array([float(x) for x in line.split()])
                if len(d) == 7:
                    data.append(d)
        data = np.array(data).transpose()
        self.k        = data[0]
        self.real_phc = data[1]
        self.mag_feff = data[2]
        self.pha_feff = data[3]
        self.red_fact = data[4]
        self.lam = data[5]
        self.rep = data[6]
        self.pha = data[1] + data[3]
        self.amp = data[2] * data[4]

class FeffPathGroup(larch.Group):
    def __init__(self, filename=None, _larch=None,
                 label=None, s02=None, degen=None, e0=None,
                 ei=None, deltar=None, sigma2=None,
                 third=None, fourth=None,  **kws):

        larch.Group.__init__(self,  **kws)
        self._larch = _larch
        self.filename = filename
        self._dat = FeffDatFile(filename=filename)
        try:
            self.reff = self._dat.reff
            self.nleg  = self._dat.nleg
            self.geom  = self._dat.geom
            self.degen = self._dat.degen if degen is None else degen
        except AttributeError:
            pass
        self.label  = filename if label is None else label
        self.label  = filename if label is None else label
        self.s02    = 1 if s02    is None else s02
        self.e0     = 0 if e0     is None else e0
        self.ei     = 0 if ei     is None else ei
        self.deltar = 0 if deltar is None else deltar
        self.sigma2 = 0 if sigma2 is None else sigma2
        self.third  = 0 if third  is None else third
        self.fourth = 0 if fourth is None else fourth

        self.k = []
        self.chi = []
        self.calc_chi = self._calc_chi

    def __repr__(self):
        if self.filename is not None:
            return '<FeffPath Group %s>' % self.filename
        return '<FeffPath Group (empty)>'

    def _pathparams(self, paramgroup=None, **kws):
        """evaluate path parameter value
        """
        # degen, s02, e0, ei, deltar, sigma2, third, fourth
        if (paramgroup is not None and
            self._larch.symtable.isgroup(paramgroup)):
            self._larch.symtable._sys.paramGroup = paramgroup
        self._larch.symtable._fix_searchGroups()

        out = []
        for param in ('degen', 's02', 'e0', 'ei',
                      'deltar', 'sigma2', 'third', 'fourth'):
            val = getattr(self, param)
            if param in kws:
                if kws[param] is not None:
                    val = kws[param]
            if isinstance(val, (str, unicode)):
                setattr(self, param,
                        Parameter(expr=val, _larch=self._larch))
                val = getattr(self, param)
            out.append(param_value(val))
        return out

    def _calc_chi(self, k=None, kmax=None, kstep=None, degen=None, s02=None,
                 e0=None, ei=None, deltar=None, sigma2=None,
                 third=None, fourth=None, debug=False, **kws):
        """calculate chi(k) with the provided parameters"""
        if self.reff < 0.05:
            self._larch.writer.write('reff is too small to calculate chi(k)')
            return
        # make sure we have a k array
        if k is None:
            if kmax is None:
                kmax = 30.0
            kmax = min(max(self._dat.k), kmax)
            if kstep is None: kstep = 0.05
            k = kstep * np.arange(int(1.01 + kmax/kstep), dtype='float64')

        reff = self.reff
        # put 'reff' into the paramGroup so that it can be used in
        # constraint expressions
        if self._larch.symtable._sys.paramGroup is not None:
            self._larch.symtable._sys.paramGroup.reff = reff

        # get values for all the path parameters
        (degen, s02, e0, ei, deltar, sigma2, third, fourth)  = \
                self._pathparams(degen=degen, s02=s02, e0=e0, ei=ei,
                                 deltar=deltar, sigma2=sigma2,
                                 third=third, fourth=fourth)

        # create e0-shifted energy and k, careful to look for |e0| ~= 0.
        en = k*k - e0*ETOK
        if min(abs(en)) < SMALL:
            try:
                en[np.where(abs(en) < 2*SMALL)] = SMALL
            except ValueError:
                pass
        # q is the e0-shifted wavenumber
        q = np.sign(en)*np.sqrt(abs(en))

        # lookup Feff.dat values (pha, amp, rep, lam)
        pha = np.interp(q, self._dat.k, self._dat.pha)
        amp = np.interp(q, self._dat.k, self._dat.amp)
        rep = np.interp(q, self._dat.k, self._dat.rep)
        lam = np.interp(q, self._dat.k, self._dat.lam)

        if debug:
            self.debug_k   = q
            self.debug_pha = pha
            self.debug_amp = amp
            self.debug_rep = rep
            self.debug_lam = lam

        # p = complex wavenumber, and its square:
        pp   = (rep + 1j/lam)**2 + 1j * ei * ETOK
        p    = np.sqrt(pp)

        # the xafs equation:
        cchi = np.exp(-2*reff*p.imag - 2*pp*(sigma2 - pp*fourth/3) +
                      1j*(2*q*reff + pha +
                          2*p*(deltar - 2*sigma2/reff - 2*pp*third/3) ))

        cchi = degen * s02 * amp * cchi / (q*(reff + deltar)**2)
        cchi[0] = 2*cchi[1] - cchi[2]

        # outputs:
        self.k = k
        self.p = p
        self.chi = cchi.imag
        self.chi_real = -cchi.real

def _read_feffdat(fname, _larch=None, **kws):
    """read Feff.dat file into a FeffPathGroup"""
    return FeffPathGroup(filename=fname, _larch=_larch)

def _ff2chi(pathlist, paramgroup=None, _larch=None, group=None,
            k=None, kmax=None, kstep=0.05, **kws):
    """sum the XAFS for a set of paths... assumes that the
    Path Parameters are set"""
    msg = _larch.writer.write
    if (paramgroup is not None and
         _larch.symtable.isgroup(group)):
        _larch.symtable._sys.paramGroup = paramgroup
    for p in pathlist:
        if not hasattr(p, 'calc_chi'):
            msg('%s is not a valid Feff Path' % p)
            return
        p.calc_chi(k=k, kstep=kstep, kmax=kmax)
    k = pathlist[0].k[:]
    out = np.zeros_like(k)
    for p in pathlist:
        out += p.chi

    if _larch.symtable.isgroup(group):
        group.k = k
        group.chi = out
    else:
        return out

def feffpath(filename=None, _larch=None,
             label=None, s02=None, degen=None, e0=None,
             ei=None, deltar=None, sigma2=None,
             third=None, fourth=None,  **kws):
    """create a feff path"""
    print 'I  am feffpath'
    return FeffPathGroup(filename=filename, label=label, s02=s02,
                         degen=degen, e0=e0, ei=ei, deltar=deltar,
                         sigma2=sigma2, third=third, fourth=fourth,
                         _larch=_larch)

def registerLarchPlugin():
    return ('_xafs', {'read_feffdat': _read_feffdat,
                      'ff2chi': _ff2chi,
                      'feffpath': feffpath})
