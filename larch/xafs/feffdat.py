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
from scipy.interpolate import UnivariateSpline
from lmfit import Parameters, Parameter
from lmfit.printfuncs import gformat
from larch import Group, isNamedClass

from larch.utils.strutils import fix_varname, b32hash
from larch.xray import atomic_mass, atomic_symbol
from larch.fitting import group2params, isParameter, param_value

from .xafsutils import ETOK, set_xafsGroup

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
            rmass = 0
            for atsym, iz, ipot, amass, x, y, z in self.geom:
                rmass += 1.0/max(1., amass)
            self.__rmass = 1./rmass
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
                        lab = atomic_symbol(iz)
                    amass = atomic_mass(iz)
                    geom = [lab, iz, ipot, amass] + xyz
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


PATH_PARS = ('degen', 's02', 'e0', 'ei', 'deltar', 'sigma2', 'third', 'fourth')
PATHPAR_FMT = "%s__%s"

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
        self.params = None
        self.label = label
        self.spline_coefs = None
        def_degen = 1

        self._feffdat = None
        if filename is not None:
            self._feffdat = FeffDatFile(filename=filename, _larch=_larch)
            self.geom  = self._feffdat.geom
            def_degen  = self._feffdat.degen
            if self.label is None:
                self.label = self.__geom2label()

        self.degen = def_degen if degen  is None else degen
        self.s02    = 1.0      if s02    is None else s02
        self.e0     = 0.0      if e0     is None else e0
        self.ei     = 0.0      if ei     is None else ei
        self.deltar = 0.0      if deltar is None else deltar
        self.sigma2 = 0.0      if sigma2 is None else sigma2
        self.third  = 0.0      if third  is None else third
        self.fourth = 0.0      if fourth is None else fourth

        self.k = None
        self.chi = None
        if self._feffdat is not None:
            self.create_spline_coefs()

    def __geom2label(self):
        """generate label by hashing path geometry"""
        rep = []
        if self.geom is not None:
            for atom in self.geom:
                rep.extend(atom)
        if self._feffdat is not None:
            rep.append(self._feffdat.degen)
            rep.append(self._feffdat.reff)

        for attr in ('s02', 'e0', 'ei', 'deltar', 'sigma2', 'third', 'fourth'):
            rep.append(getattr(self, attr, '_'))
        s = "|".join([str(i) for i in rep])
        return "p%s" % (b32hash(s)[:8].lower())

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

    def create_path_params(self):
        """
        create Path Parameters within the current fiteval
        """
        self.params = Parameters(asteval=self._larch.symtable._sys.fiteval)
        if self.label is None:
            self.label = self.__geom2label()

        self.store_feffdat()

        for pname in PATH_PARS:
            val =  getattr(self, pname)
            attr = 'value'
            if isinstance(val, str):
                attr = 'expr'
            kws =  {'vary': False, attr: val}
            parname = fix_varname(PATHPAR_FMT % (pname, self.label))
            self.params.add(parname, **kws)

    def create_spline_coefs(self):
        """pre-calculate spline coefficients for feff data"""
        self.spline_coefs = {}
        fdat = self._feffdat
        self.spline_coefs['pha'] = UnivariateSpline(fdat.k, fdat.pha, s=0)
        self.spline_coefs['amp'] = UnivariateSpline(fdat.k, fdat.amp, s=0)
        self.spline_coefs['rep'] = UnivariateSpline(fdat.k, fdat.rep, s=0)
        self.spline_coefs['lam'] = UnivariateSpline(fdat.k, fdat.lam, s=0)

    def store_feffdat(self):
        """stores data about this Feff path in the fiteval
        symbol table for use as `reff` and in sigma2 calcs
        """
        fiteval = self._larch.symtable._sys.fiteval
        fdat = self._feffdat
        fiteval.symtable['feffpath'] = fdat
        fiteval.symtable['reff']  = fdat.reff
        return fiteval

    def __path_params(self, **kws):
        """evaluate path parameter value.  Returns
        (degen, s02, e0, ei, deltar, sigma2, third, fourth)
        """
        # put 'reff' and '_feffdat' into the symboltable so that
        # they can be used in constraint expressions, and get
        # fiteval evaluator
        self.store_feffdat()

        if self.params is None:
            self.create_path_params()
        out = []
        for pname in PATH_PARS:
            val = kws.get(pname, None)
            parname = fix_varname(PATHPAR_FMT % (pname, self.label))
            if val is None:
                val = self.params[parname]._getval()
            out.append(val)
        return out

    def path_paramvals(self, **kws):
        (deg, s02, e0, ei, delr, ss2, c3, c4) = self.__path_params()
        return dict(degen=deg, s02=s02, e0=e0, ei=ei, deltar=delr,
                    sigma2=ss2, third=c3, fourth=c4)

    def report(self):
        "return  text report of parameters"
        (deg, s02, e0, ei, delr, ss2, c3, c4) = self.__path_params()
        geomlabel  = '     atom      x        y        z       ipot'
        geomformat = '    %4s      % .4f, % .4f, % .4f  %i'
        out = ['   Path %s, Feff.dat file = %s' % (self.label, self.filename)]
        out.append(geomlabel)

        for atsym, iz, ipot, amass, x, y, z in self.geom:
            s = geomformat % (atsym, x, y, z, ipot)
            if ipot == 0: s = "%s (absorber)" % s
            out.append(s)

        stderrs = {}
        out.append('     {:7s}= {:s}'.format('reff',
                                              gformat(self._feffdat.reff)))

        for pname in ('degen', 's02', 'e0', 'r',
                      'deltar', 'sigma2', 'third', 'fourth', 'ei'):
            val = strval = getattr(self, pname, 0)
            parname = fix_varname(PATHPAR_FMT % (pname, self.label))
            std = None
            if pname == 'r':
                parname = fix_varname(PATHPAR_FMT % ('deltar', self.label))
                par = self.params.get(parname, None)
                val = par.value + self._feffdat.reff
                strval = 'reff + ' + getattr(self, 'deltar', 0)
                std = par.stderr
            else:
                par = self.params.get(parname, None)
                if par is not None:
                    val = par.value
                    std = par.stderr
            if std is None  or std <= 0:
                svalue = gformat(val)
            else:
                svalue = "{:s} +/-{:s}".format(gformat(val), gformat(std))
            if pname == 's02': pname = 'n*s02'

            svalue = "     {:7s}= {:s}".format(pname, svalue)
            if isinstance(strval, str):
                svalue = "{:s}  '{:s}'".format(svalue, strval)

            if val == 0 and pname in ('third', 'fourth', 'ei'):
                continue
            out.append(svalue)
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
        # get values for all the path parameters
        (degen, s02, e0, ei, deltar, sigma2, third, fourth)  = \
                self.__path_params(degen=degen, s02=s02, e0=e0, ei=ei,
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
            pha = self.spline_coefs['pha'](q)
            amp = self.spline_coefs['amp'](q)
            rep = self.spline_coefs['rep'](q)
            lam = self.spline_coefs['lam'](q)

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

def path2chi(path, paramgroup=None, _larch=None, **kws):
    """calculate chi(k) for a Feff Path,
    optionally setting path parameter values
    output chi array will be written to path group

    Parameters:
    ------------
      path:        a FeffPath Group
      kmax:        maximum k value for chi calculation [20].
      kstep:       step in k value for chi calculation [0.05].
      k:           explicit array of k values to calculate chi.

    Returns:
    ---------
      None - outputs are written to path group

    """
    params = group2params(paramgroup, _larch=_larch)

    if not isNamedClass(path, FeffPathGroup):
        msg('%s is not a valid Feff Path' % path)
        return
    path.create_path_params()
    path._calc_chi(**kws)

def ff2chi(pathlist, group=None, paramgroup=None, _larch=None,
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
    params = group2params(paramgroup, _larch=_larch)

    msg = _larch.writer.write
    for path in pathlist:
        if not isNamedClass(path, FeffPathGroup):
            msg('%s is not a valid Feff Path' % path)
            return
        path.create_path_params()
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
