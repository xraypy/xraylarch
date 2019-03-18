import numpy as np
import ctypes
from ctypes import POINTER, pointer, c_int, c_long, c_char, c_char_p, c_double

import larch
from larch.larchlib import get_dll
from larch.xray import  atomic_mass

F8LIB = None

FEFF_maxpts = 150  # nex
FEFF_maxpot = 11   # nphx
FEFF_maxleg = 9    # legtot
BOHR = 0.52917721067
RYDBERG = 13.605698

def with_phase_file(fcn):
    """decorator to ensure that the wrapped function either
    has a non-None 'phase_file' argument or that that
    self.phase_file is not None
    """
    errmsg = "function '%s' needs a non-None phase_file"
    def wrapper(*args, **keywords):
        "needs phase_file"
        phase_file = keywords.get('phase_file', None)
        if phase_file is None:
            phase_file = getattr(args[0], 'phase_file', None)
            if phase_file is None:
                raise AttributeError(errmsg % fcn.__name__)
        else:
            setattr(args[0], 'phase_file', phase_file)
        # raise Warning(errmsg % fcn.__name__)
        return fcn(*args, **keywords)
    wrapper.__doc__ = fcn.__doc__
    wrapper.__name__ = fcn.__name__
    wrapper.__filename__ = fcn.__code__.co_filename
    wrapper.__dict__.update(fcn.__dict__)
    return wrapper

class Feff8L_XAFSPath(object):
    """Feff8 Scattering Path calculation

    A calculation requires a Potentials and Phase Shift calculation
    in PAD format from Feff8L, and a list of scattering paths

    Usage:
    ------
       # create path
       path  = Feff8L_XAFSPath(phase_file='phase.pad')

       # list 'ipot' and labels for absorber, scatterers
       path.list_scatterers()

       # set coords for absorbing atom
       path.set_absorber(x=0., y=0., z=0.)

       # add scattering atom
       path.add_scatterer(x=1.5, y=1.5, z=1.5, ipot=1)

       # calculate basic (unaltered) XAFS contributions
       path.calcuate_xafs()

    """
    def __init__(self, phase_file=None, title=''):
        global F8LIB
        if F8LIB is None:
            try:
                F8LIB = get_dll('feff8lpath')
            except:
                pass
        self.reset(phase_file=phase_file, title=title)

    def reset(self, phase_file=None, title=''):
        """reset all path data"""
        self.phase_file = None
        if phase_file is not None:
            self.phase_file = phase_file
        self.index   = 9999
        self.degen   = 1.
        self.nnnn_out = False
        self.json_out = False
        self.verbose  = False
        self.ipol   = 0
        self.ellip  = 0.
        self.nepts  = 0
        self.genfmt_order = 2
        self.version= ""
        self.exch   = ""
        self.title  = title
        self.filename  = "%s_%s" % (self.phase_file, self.title)
        self.rs_int = 0.
        self.vint   = 0.
        self.mu     = 0.
        self.edge   = 0.
        self.kf     = 0.
        self.rnorman = 0.
        self.gam_ch = 0.
        self.nepts  = FEFF_maxpts

        dargs = dict(dtype=np.float64, order='F')
        largs = dict(dtype=np.int32, order='F')

        self.evec   = np.zeros(3, **dargs)
        self.xivec  = np.zeros(3, **dargs)
        self.ipot   = np.zeros(1+FEFF_maxleg, **largs)
        self.beta   = np.zeros(1+FEFF_maxleg, **dargs)
        self.eta    = np.zeros(2+FEFF_maxleg, **dargs)
        self.ri     = np.zeros(FEFF_maxleg, **dargs)
        self.rat    = np.zeros((3, 2+FEFF_maxleg), **dargs)
        self.iz     = np.zeros(1+FEFF_maxpot, **largs)
        self.k      = np.zeros(FEFF_maxpts, **dargs)
        self.real_phc = np.zeros(FEFF_maxpts, **dargs)
        self.mag_feff = np.zeros(FEFF_maxpts, **dargs)
        self.pha_feff = np.zeros(FEFF_maxpts, **dargs)
        self.red_fact = np.zeros(FEFF_maxpts, **dargs)
        self.lam      = np.zeros(FEFF_maxpts, **dargs)
        self.rep      = np.zeros(FEFF_maxpts, **dargs)
        self.nleg = 1
        self.atoms = []

        if self.phase_file is not None:
            self.read_atoms()
            self.set_absorber()

    @with_phase_file
    def read_atoms(self):
        """read atoms ipot, iz, symbol"""
        self.atoms = []
        with open(self.phase_file,'r') as fh:
            line1_words = fh.readline().strip().split()
            text = fh.readlines()
        npots = int(line1_words[4])
        for line in text[4:]:
            if not line.startswith('$'):
                words = line.split()
                self.atoms.append((int(words[1]), words[2]))
            if len(self.atoms) > npots:
                break

    @with_phase_file
    def list_atoms(self):
        """list Feff Potentials atoms ('ipots') fo phase file"""
        if len(self.atoms) < 1:
            self.read_atoms()
        out = ["# Potential   Z   Symbol"]
        for ipot, atom in enumerate(self.atoms):
            out.append("    %2i      %3i     %s" % (ipot, atom[0], atom[1]))
        return "\n".join(out)

    @with_phase_file
    def set_absorber(self, x=0., y=0., z=0., phase_file=None):
        """set coordinates for absorbing atom ('ipot'=0)"""
        self.rat[0, 0] = x
        self.rat[1, 0] = y
        self.rat[2, 0] = z
        self.rat[0, self.nleg] = self.rat[0, 0]
        self.rat[1, self.nleg] = self.rat[1, 0]
        self.rat[2, self.nleg] = self.rat[2, 0]
        self.ipot[self.nleg]   = self.ipot[0]

    @with_phase_file
    def add_scatterer(self, x=0., y=0., z=0., ipot=1, phase_file=None):
        self.rat[0, self.nleg] = x
        self.rat[1, self.nleg] = y
        self.rat[2, self.nleg] = z
        self.ipot[self.nleg] = ipot
        self.nleg += 1
        # set final atom coords to same as absorber
        self.rat[0, self.nleg] = self.rat[0, 0]
        self.rat[1, self.nleg] = self.rat[1, 0]
        self.rat[2, self.nleg] = self.rat[2, 0]
        self.ipot[self.nleg]   = self.ipot[0]

    @with_phase_file
    def calculate_xafs(self, phase_file=None):
        if F8LIB is None:
            raise ValueError("Feff8 Dynamic library not found")

        if len(self.atoms) < 1:
            self.read_atoms()

        class args:
            pass

        # strings / char*.  Note fixed length to match Fortran
        args.phase_file     = (self.phase_file + ' '*256)[:256]
        args.exch_label     = ' '*8
        args.genfmt_version = ' '*30

        # integers, including booleans
        for attr in ('index', 'nleg', 'genfmt_order', 'ipol', 'nnnn_out',
                     'json_out', 'verbose', 'nepts'):
            setattr(args, attr, pointer(c_long(int(getattr(self, attr)))))

        # doubles
        for attr in ('degen', 'rs_int', 'vint', 'mu', 'edge', 'kf', 'rnorman',
                     'gam_ch', 'ellip'):
            setattr(args, attr, pointer(c_double(getattr(self, attr))))

        # integer arrays
        args.ipot = self.ipot.ctypes.data_as(POINTER(self.ipot.size*c_int))
        args.iz = self.iz.ctypes.data_as(POINTER(self.iz.size*c_int))

        # double arrays
        # print(" Rat 0  ", self.rat)
        for attr in ('evec', 'xivec', 'ri', 'beta', 'eta',
                     'k', 'real_phc', 'mag_feff', 'pha_feff',
                     'red_fact', 'lam', 'rep'):
            arr = getattr(self, attr)
            cdata = arr.ctypes.data_as(POINTER(arr.size*c_double))
            setattr(args, attr, cdata)
        # handle rat (in atomic units)
        rat_atomic = self.rat/BOHR
        args.rat = (rat_atomic).ctypes.data_as(POINTER(rat_atomic.size*c_double))

        onepath = F8LIB.onepath_
        # print(" Calc with onepath ", onepath, rat_atomic)
        # print(" args rat = ", args.rat.contents[:])
        x = onepath(args.phase_file, args.index, args.nleg, args.degen,
                    args.genfmt_order, args.exch_label, args.rs_int, args.vint,
                    args.mu, args.edge, args.kf, args.rnorman,
                    args.gam_ch, args.genfmt_version, args.ipot, args.rat,
                    args.iz, args.ipol, args.evec, args.ellip, args.xivec,
                    args.nnnn_out, args.json_out, args.verbose, args.ri,
                    args.beta, args.eta, args.nepts, args.k,
                    args.real_phc, args.mag_feff, args.pha_feff,
                    args.red_fact, args.lam, args.rep)

        self.exch   = args.exch_label.strip()
        self.version = args.genfmt_version.strip()
        # print(" Calc with onepath done")
        # unpack integers/floats
        for attr in ('index', 'nleg', 'genfmt_order', 'degen', 'rs_int',
                     'vint', 'mu', 'edge', 'kf', 'rnorman', 'gam_ch',
                     'ipol', 'ellip', 'nnnn_out', 'json_out', 'verbose',
                     'nepts'):
            setattr(self, attr, getattr(args, attr).contents.value)

        # some data needs recasting, reformatting
        self.mu *= (2*RYDBERG)
        self.nnnn_out = bool(self.nnnn_out)
        self.json_out = bool(self.json_out)
        self.verbose  = bool(self.verbose)

        # unpck energies
        for attr in ('evec', 'xivec'):
            cdata = getattr(args, attr).contents[:]
            setattr(self, attr, np.array(cdata))

        nleg = self.nleg
        nepts = self.nepts

        # arrays of length 'nepts'
        for attr in ('k', 'real_phc', 'mag_feff', 'pha_feff',
                     'red_fact', 'lam', 'rep'):
            cdata = getattr(args, attr).contents[:nepts]
            setattr(self, attr, np.array(cdata))
        self.pha = self.real_phc + self.pha_feff
        self.amp = self.red_fact * self.mag_feff

        # unpack arrays of length 'nleg':
        for attr in ('ipot', 'beta', 'eta', 'ri'):
            cdata = getattr(args, attr).contents[:]
            setattr(self, attr, np.array(cdata))

        # rat is sort of special, and calculate reff too:
        rat = args.rat.contents[:]
        rat = np.array(rat).reshape(2+FEFF_maxleg, 3).transpose()
        self.rat = BOHR*rat

        _rat = self.rat.T
        reff = 0.
        for i, atom in enumerate(_rat[1:]):
            prev = _rat[i,:]
            reff += np.sqrt( (prev[0]-atom[0])**2 +
                             (prev[1]-atom[1])**2 +
                             (prev[2]-atom[2])**2 )
        self.reff = reff /2.0

        self.geom = []
        rmass  = 0.
        for i in range(nleg):
            ipot = int(self.ipot[i])
            iz, sym = self.atoms[ipot]
            mass = atomic_mass(iz)

            x, y, z = _rat[i][0], _rat[i][1], _rat[i][2]
            self.geom.append((str(sym), iz, ipot, x, y, z))
            rmass += 1.0/max(1.0, mass)

        self.rmass = 1./rmass


def feff8_xafs(phase_file):
    return Feff8L_XAFSPath(phase_file=phase_file)



## def initializeLarchPlugin(_larch=None):
#     """initialize F8LIB"""
#     if _larch is not None:
#         global F8LIB
#         if F8LIB is None:
#             try:
#                 F8LIB = get_dll('feff8lpath')
#             except:
#                 pass
##
