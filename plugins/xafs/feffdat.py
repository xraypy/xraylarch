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
import six
import numpy as np
from scipy.interpolate import UnivariateSpline
from larch import (Group, Parameter, isParameter,
                   ValidateLarchPlugin,
                   param_value, isNamedClass)

from larch_plugins.xafs import ETOK, set_xafsGroup
from larch_plugins.xray import atomic_mass, atomic_symbol

SMALL = 1.e-6

class FeffDatFile(Group):
    def __init__(self, filename=None, _larch=None, **kws):
        self._larch = _larch
        kwargs = dict(name='feff.dat: %s' % filename)
        kwargs.update(kws)
        Group.__init__(self,  **kwargs)
        if filename is not None:
            self.__read(filename)

    def __repr__(self):
        if self.filename is not None:
            return '<Feff.dat File Group: %s>' % self.filename
        return '<Feff.dat File Group (empty)>'

    def __copy__(self):
        return FeffDatFile(filename=self.filename, _larch=self._larch)

    def __deepcopy__(self, memo):
        return FeffDatFile(filename=self.filename, _larch=self._larch)

    @property
    def reff(self): return self.__reff__

    @reff.setter
    def reff(self, val):     pass

    @property
    def nleg(self): return self.__nleg__

    @nleg.setter
    def nleg(self, val):     pass

    @property
    def rmass(self):
        """reduced mass for a path"""
        if self.__rmass is None:
            amass = 0
            for label, iz, ipot, x, y, z in self.geom:
                m = atomic_mass(iz, _larch=self._larch)
                amass += 1.0/max(1., m)
            self.__rmass = 1./amass
        return self.__rmass

    @rmass.setter
    def rmass(self, val):     pass

    def __read(self, filename):
        try:
            lines = open(filename, 'r').readlines()
        except:
            print( 'Error reading file %s ' % filename)
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
                    self.__nleg__ = int(w.pop(0))
                    self.degen, self.__reff__, self.rnorman, self.edge = w
                elif pcounter > 2:
                    words = line.split()
                    xyz = [float(x) for x in words[:3]]
                    ipot = int(words[3])
                    iz   = int(words[4])
                    if len(words) > 5:
                        lab = words[5]
                    else:
                        lab = atomic_symbol(iz, _larch=self._larch)
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
        self.__rmass = None  # reduced mass of path


class FeffPathGroup(Group):
    def __init__(self, filename=None, _larch=None,
                 label=None, s02=None, degen=None, e0=None,
                 ei=None, deltar=None, sigma2=None,
                 third=None, fourth=None,  **kws):

        kwargs = dict(name='FeffPath: %s' % filename)
        kwargs.update(kws)
        Group.__init__(self, **kwargs)
        self._larch = _larch
        self.filename = filename
        def_degen = 1
        if filename is not None:
            self._feffdat = FeffDatFile(filename=filename, _larch=_larch)
            self.geom  = self._feffdat.geom
            def_degen  = self._feffdat.degen
        self.degen = degen if degen is not None else def_degen
        self.label = label if label is not None else filename
        self.s02    = 1 if s02    is None else s02
        self.e0     = 0 if e0     is None else e0
        self.ei     = 0 if ei     is None else ei
        self.deltar = 0 if deltar is None else deltar
        self.sigma2 = 0 if sigma2 is None else sigma2
        self.third  = 0 if third  is None else third
        self.fourth = 0 if fourth is None else fourth
        self.k = None
        self.chi = None

    def __copy__(self):
        return FeffPathGroup(filename=self.filename, _larch=self._larch,
                             s02=self.s02, degen=self.degen, e0=self.e0,
                             ei=self.ei, deltar=self.deltar, sigma2=self.sigma2,
                             third=self.third, fourth=self.fourth)

    def __deepcopy__(self, memo):
        return FeffPathGroup(filename=self.filename, _larch=self._larch,
                             s02=self.s02, degen=self.degen, e0=self.e0,
                             ei=self.ei, deltar=self.deltar, sigma2=self.sigma2,
                             third=self.third, fourth=self.fourth)

    @property
    def reff(self): return self._feffdat.reff

    @reff.setter
    def reff(self, val):  pass

    @property
    def nleg(self): return self._feffdat.nleg

    @nleg.setter
    def nleg(self, val):     pass

    @property
    def rmass(self): return self._feffdat.rmass

    @rmass.setter
    def rmass(self, val):  pass

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

        # put 'reff' and '_feffdat' into the paramGroup so that
        # 'reff' can be used in constraint expressions and
        # '_feffdat' can be used inside Debye and Eins functions
        stable = self._larch.symtable
        if stable.isgroup(stable._sys.paramGroup):
            stable._sys.paramGroup.reff = self._feffdat.reff
            stable._sys.paramGroup._feffdat = self._feffdat

        out = []
        for param in ('degen', 's02', 'e0', 'ei',
                      'deltar', 'sigma2', 'third', 'fourth'):
            val = getattr(self, param)
            if param in kws:
                if kws[param] is not None:
                    val = kws[param]
            if isinstance(val, six.string_types):
                thispar = Parameter(expr=val, _larch=self._larch)

                #if isinstance(thispar, Parameter):
                #    thispar = thispar.value
                setattr(self, param, thispar)
                val = getattr(self, param)
            out.append(param_value(val))
        return out

    def report(self):
        "return  text report of parameters"
        (deg, s02, e0, ei, delr, ss2, c3, c4) = self._pathparams()

        # put 'reff' into the paramGroup so that it can be used in
        # constraint expressions
        reff = self._feffdat.reff
        self._larch.symtable._sys.paramGroup._feffdat = self._feffdat
        self._larch.symtable._sys.paramGroup.reff = reff


        geomlabel  = '          Atom     x        y        z     ipot'
        geomformat = '           %s   % .4f, % .4f, % .4f  %i'
        out = ['   feff.dat file = %s' % self.filename]
        if self.label != self.filename:
            out.append('     label     = %s' % self.label)
        out.append(geomlabel)

        for label, iz, ipot, x, y, z in self.geom:
            s = geomformat % (label, x, y, z, ipot)
            if ipot == 0: s = "%s (absorber)" % s
            out.append(s)

        stderrs = {}
        out.append('     reff   =  %.5f' % self._feffdat.reff)
        for param in ('degen', 's02', 'e0', 'ei',
                      'deltar', 'sigma2', 'third', 'fourth'):
            val = getattr(self, param)
            std = 0
            if isParameter(val):
                std = val.stderr
                val = val.value
                if isParameter(val):
                    if val.stderr is not None:
                        std = val.stderr
            if std is None: std = -1
            stderrs[param] = std

        def showval(title, par, val, stderrs, ifnonzero=False):
            if val == 0 and ifnonzero:
                return
            s = '     %s=' % title
            if title.startswith('R  '):
                val = val + self._feffdat.reff
            if stderrs[par] == 0:
                s = '%s % .5f' % (s, val)
            else:
                s = '%s % .5f +/- % .5f' % (s, val, stderrs[par])
            out.append(s)
        showval('Degen  ', 'degen',  deg,  stderrs)
        showval('S02    ', 's02',    s02,  stderrs)
        showval('E0     ', 'e0',     e0,   stderrs)
        showval('R      ', 'deltar', delr, stderrs)
        showval('deltar ', 'deltar', delr, stderrs)
        showval('sigma2 ', 'sigma2', ss2,  stderrs)
        showval('third  ', 'third',  c3,   stderrs, ifnonzero=True)
        showval('fourth ', 'fourth', c4,   stderrs, ifnonzero=True)
        showval('Ei     ', 'ei',     ei,   stderrs, ifnonzero=True)

        return '\n'.join(out)

    def _calc_chi(self, k=None, kmax=None, kstep=None, degen=None, s02=None,
                 e0=None, ei=None, deltar=None, sigma2=None,
                 third=None, fourth=None, debug=False, interp='cubic', **kws):
        """calculate chi(k) with the provided parameters"""
        fdat = self._feffdat
        if fdat.reff < 0.05:
            self._larch.writer.write('reff is too small to calculate chi(k)')
            return
        # make sure we have a k array
        if k is None:
            if kmax is None:
                kmax = 30.0
            kmax = min(max(fdat.k), kmax)
            if kstep is None: kstep = 0.05
            k = kstep * np.arange(int(1.01 + kmax/kstep), dtype='float64')

        reff = fdat.reff
        # put 'reff' into the paramGroup so that it can be used in
        # constraint expressions
        if self._larch.symtable._sys.paramGroup is not None:
            self._larch.symtable._sys.paramGroup._feffdat = fdat
            self._larch.symtable._sys.paramGroup.reff = fdat.reff

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
        if interp.startswith('lin'):
            pha = np.interp(q, fdat.k, fdat.pha)
            amp = np.interp(q, fdat.k, fdat.amp)
            rep = np.interp(q, fdat.k, fdat.rep)
            lam = np.interp(q, fdat.k, fdat.lam)
        else:
            pha = UnivariateSpline(fdat.k, fdat.pha, s=0)(q)
            amp = UnivariateSpline(fdat.k, fdat.amp, s=0)(q)
            rep = UnivariateSpline(fdat.k, fdat.rep, s=0)(q)
            lam = UnivariateSpline(fdat.k, fdat.lam, s=0)(q)

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
        self.chi_imag = -cchi.real

@ValidateLarchPlugin
def _path2chi(path, paramgroup=None, _larch=None, **kws):
    """calculate chi(k) for a Feff Path,
    optionally setting path parameter values
    output chi array will be written to path group

    Parameters:
    ------------
      path:        a FeffPath Group
      paramgroup:  a Parameter Group for calculating Path Parameters [None]
      kmax:        maximum k value for chi calculation [20].
      kstep:       step in k value for chi calculation [0.05].
      k:           explicit array of k values to calculate chi.

    Returns:
    ---------
      None - outputs are written to path group

    """
    if not isNamedClass(path, FeffPathGroup):
        msg('%s is not a valid Feff Path' % path)
        return
    if _larch is not None:
        if (paramgroup is not None and
            _larch.symtable.isgroup(paramgroup)):
            _larch.symtable._sys.paramGroup = paramgroup
        elif not hasattr(_larch.symtable._sys, 'paramGroup'):
            _larch.symtable._sys.paramGroup = Group()
    path._calc_chi(**kws)

@ValidateLarchPlugin
def _ff2chi(pathlist, group=None, paramgroup=None, _larch=None,
            k=None, kmax=None, kstep=0.05, **kws):
    """sum chi(k) for a list of FeffPath Groups.

    Parameters:
    ------------
      pathlist:    a list of FeffPath Groups
      paramgroup:  a Parameter Group for calculating Path Parameters [None]
      kmax:        maximum k value for chi calculation [20].
      kstep:       step in k value for chi calculation [0.05].
      k:           explicit array of k values to calculate chi.
    Returns:
    ---------
       group contain arrays for k and chi

    This essentially calls path2chi() for each of the paths in the
    pathlist and writes the resulting arrays to group.k and group.chi.

    """
    msg = _larch.writer.write
    if (paramgroup is not None and _larch is not None and
         _larch.symtable.isgroup(paramgroup)):
        _larch.symtable._sys.paramGroup = paramgroup
    for path in pathlist:
        if not isNamedClass(path, FeffPathGroup):
            msg('%s is not a valid Feff Path' % path)
            return
        path._calc_chi(k=k, kstep=kstep, kmax=kmax)
    k = pathlist[0].k[:]
    out = np.zeros_like(k)
    for path in pathlist:
        out += path.chi

    if group is None:
        group = Group()
    else:
        group = set_xafsGroup(group, _larch=_larch)
    group.k = k
    group.chi = out
    return group

def feffpath(filename=None, _larch=None, label=None, s02=None,
             degen=None, e0=None,ei=None, deltar=None, sigma2=None,
             third=None, fourth=None, **kws):
    """create a Feff Path Group from a *feffNNNN.dat* file.

    Parameters:
    -----------
      filename:  name (full path of) *feffNNNN.dat* file
      label:     label for path   [file name]
      degen:     path degeneracy, N [taken from file]
      s02:       S_0^2    value or parameter [1.0]
      e0:        E_0      value or parameter [0.0]
      deltar:    delta_R  value or parameter [0.0]
      sigma2:    sigma^2  value or parameter [0.0]
      third:     c_3      value or parameter [0.0]
      fourth:    c_4      value or parameter [0.0]
      ei:        E_i      value or parameter [0.0]

    For all the options described as **value or parameter** either a
    numerical value or a Parameter (as created by param()) can be given.

    Returns:
    ---------
        a FeffPath Group.

    """
    return FeffPathGroup(filename=filename, label=label, s02=s02,
                         degen=degen, e0=e0, ei=ei, deltar=deltar,
                         sigma2=sigma2, third=third, fourth=fourth,
                         _larch=_larch)

def registerLarchPlugin():
    return ('_xafs', {'feffpath': feffpath,
                      'path2chi': _path2chi,
                      'ff2chi': _ff2chi})
