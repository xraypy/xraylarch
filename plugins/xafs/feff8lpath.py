import numpy as np
import ctypes
from ctypes import POINTER, pointer, c_int, c_long, c_char, c_char_p, c_double

## from matplotlib import pylab

LIBFEFF8 = '/Users/Newville/local/lib/libonepath.dylib'

F8LIB = ctypes.cdll.LoadLibrary(LIBFEFF8)

FEFF_maxpts = 150  # nex
FEFF_maxpot = 11   # nphx
FEFF_maxleg = 9    # legtot
BOHR = 0.52917721067

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

       # list 'ipot' and labels for absorber, scattererers
       path.list_scatterers()

       # set coords for absorbing atom
       path.set_absorber(x=0., y=0., z=0.)

       # add scattering atom
       path.add_scatterer(x=1.5, y=1.5, z=1.5, ipot=1)

       # calculate basic (unaltered) XAFS contributions
       path.calcuate_xafs()

    """
    def __init__(self, phase_file=None):
        self.phase_file = phase_file
        self.clear()

    def clear(self):
        """reset all path data"""

        self.index   = 9999
        self.degen   = 1.
        self.nnnn_out = False
        self.json_out = False
        self.verbose  = False
        self.ipol   = 0
        self.ellip  = 0.
        self.nepts  = 0
        self.genfmt_order = 2
        self.genfmt_vers  = ""
        self.exch_label   = ""
        self.rs     = 0.
        self.vint   = 0.
        self.xmu    = 0.
        self.edge   = 0.
        self.kf     = 0.
        self.rnorman = 0.
        self.gamach = 0.
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
        self.kfeff  = np.zeros(FEFF_maxpts, **dargs)
        self.real_phc = np.zeros(FEFF_maxpts, **dargs)
        self.mag_feff = np.zeros(FEFF_maxpts, **dargs)
        self.pha_feff = np.zeros(FEFF_maxpts, **dargs)
        self.red_fact = np.zeros(FEFF_maxpts, **dargs)
        self.lam      = np.zeros(FEFF_maxpts, **dargs)
        self.rep      = np.zeros(FEFF_maxpts, **dargs)
        self.nleg = 1

        if self.phase_file is not None:
            self.set_absorber()


    @with_phase_file
    def list_scatterers(self, phase_file=None):
        """list Feff Potentials atoms ('ipots') fo phase file"""
        atoms = []
        with open(self.phase_file,'r') as fh:
            line1_words = fh.readline().strip().split()
            text = fh.readlines()
        nphases = int(line1_words[4])
        for line in text[4:]:
            if line.startswith('$'): continue
            words = line.split()
            atoms.append((int(words[1]), words[2]))
            if len(atoms) > nphases:
                break
        out = ["# Potential   Z   Symbol"]
        for ipot, atom in enumerate(atoms):
            out.append("    %2i      %3i     %s" % (ipot, atom[0], atom[1]))
        return "\n".join(out)

    @with_phase_file
    def set_absorber(self, x=0., y=0., z=0., phase_file=None):
        """set coordinates for absorbing atom ('ipot'=0)"""
        self.rat[0, 0] = x
        self.rat[1, 0] = y
        self.rat[2, 0] = z

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
        print 'calculate xafs ', self.phase_file, self.nleg
        # print 'Atom  IPOT   X, Y, Z'
        # for i in range(self.nleg):
        #    print i, self.ipot[i], self.rat[:,i]

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
        for attr in ('degen', 'rs', 'vint', 'xmu', 'edge', 'kf', 'rnorman',
                     'gamach', 'ellip'):
            setattr(args, attr, pointer(c_double(getattr(self, attr))))

        # integer arrays
        for attr in ('ipot', 'iz'):
            arr = getattr(self, attr)
            cdata = arr.ctypes.data_as(POINTER(arr.size*c_int))
            setattr(args, attr, cdata)

        # double arrays
        self.rat = self.rat/BOHR
        for attr in ('evec', 'xivec', 'rat', 'ri', 'beta', 'eta',
                     'kfeff', 'real_phc', 'mag_feff', 'pha_feff',
                     'red_fact', 'lam', 'rep'):
            arr = getattr(self, attr)
            cdata = arr.ctypes.data_as(POINTER(arr.size*c_double))
            setattr(args, attr, cdata)

        x = F8LIB.onepath_(args.phase_file, args.index, args.nleg,
                           args.degen, args.genfmt_order, args.exch_label,
                           args.rs, args.vint, args.xmu, args.edge, args.kf,
                           args.rnorman, args.gamach, args.genfmt_version,
                           args.ipot, args.rat, args.iz, args.ipol,
                           args.evec, args.ellip, args.xivec, args.nnnn_out,
                           args.json_out, args.verbose, args.ri, args.beta,
                           args.eta, args.nepts, args.kfeff, args.real_phc,
                           args.mag_feff, args.pha_feff, args.red_fact,
                           args.lam, args.rep)

        self.exch_label   = args.exch_label.strip()
        self.genfmt_version = args.genfmt_version.strip()

        # unpack integers/floats
        for attr in ('index', 'nleg', 'genfmt_order', 'degen', 'rs',
                     'vint', 'xmu', 'edge', 'kf', 'rnorman', 'gamach',
                     'ipol', 'ellip', 'nnnn_out', 'json_out', 'verbose',
                     'nepts'):
            setattr(self, attr, getattr(args, attr).contents.value)

        # some data needs recasting, reformatting
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
        for attr in ('kfeff', 'mag_feff', 'pha_feff', 'red_fact',
                     'lam', 'rep'):
            cdata = getattr(args, attr).contents[:nepts]
            setattr(self, attr, np.array(cdata))

        # unpack arrays of length 'nleg':
        for attr in ('ipot', 'iz', 'beta', 'eta', 'ri'):
            cdata = getattr(args, attr).contents[:nleg]
            setattr(self, attr, np.array(cdata))

        # rat is sort of special, and calculate reff too:
        rat = getattr(args, 'rat').contents[:]
        rat = np.array(rat).reshape(2+FEFF_maxleg, 3).transpose()
        self.rat = BOHR*self.rat[:, :nleg+1].transpose()

        reff = 0.
        for i, atom in enumerate(self.rat[1:]):
            prev = self.rat[i,:]
            reff += np.sqrt( (prev[0]-atom[0])**2 +
                             (prev[1]-atom[1])**2 +
                             (prev[2]-atom[2])**2 )

        self.reff = reff /2.0


def feff8_xafs(phase_file, _larch=None):
    return Feff8L_XAFSPath(phase_file=phase_file)

def registerLarchPlugin():
    return ('_xafs', {'feff8_xafs': feff8_xafs})


#     path = Feff8l_Path(phase_file='../fortran/phase.pad')
#     path.set_absorber(x=0.01, y=0.1, z=0.01)
#     path.add_scatterer(x=1.806, y=0.1, z=1.806, ipot=1)
#     path.degen = 12
#     path.calculate_xafs()
#
#
#     pylab.plot(path.kfeff[:path.nepts], path.mag_feff[:path.nepts])
#     pylab.show()
