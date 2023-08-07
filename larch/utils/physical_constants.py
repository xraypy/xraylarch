# Useful physical constants
# most of these are put into common X-ray units (Angstroms, ev)

import scipy.constants as consts
from numpy import pi

I = 0.0 + 1.0j

RAD2DEG = 180.0/pi
DEG2RAD = pi/180.0
PI = pi
TAU = 2*pi

# cross-section unit
BARN     = 1.e-24   # cm^2

# atoms/mol =  6.0221413e23  atoms/mol
AVOGADRO = consts.Avogadro

# ATOMIC MASS in grams
AMU = consts.atomic_mass * 1000.0

# electron rest mass in eV
E_MASS = consts.electron_mass * consts.c**2 / consts.e

# Planck's Constant
#   h*c    ~= 12398.42 eV*Ang
#   hbar*c ~=  1973.27 eV*Ang
PLANCK_HC    = 1.e10 * consts.Planck * consts.c / consts.e
PLANCK_HBARC = PLANCK_HC / TAU

# Rydberg constant in eV (~13.6 eV)
RYDBERG = consts.Rydberg * consts.Planck * consts.c/ consts.e

# classical electron radius in cm and Ang
R_ELECTRON_CM  = 100.0 * consts.physical_constants['classical electron radius'][0]
R_ELECTRON_ANG = 1.e8 * R_ELECTRON_CM


# a few standard lattice constants
STD_LATTICE_CONSTANTS = {'Si': 5.4310205, 'C': 3.567095, 'Ge': 5.64613}


# will be able to import these from xraydb when v 4.5.1 is required
ATOM_SYMS = ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg',
           'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr',
           'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br',
           'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd',
           'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La',
           'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er',
           'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au',
           'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
           'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md',
           'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn',
           'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og']

ATOM_NAMES = ['hydrogen', 'helium', 'lithium', 'beryllium', 'boron', 'carbon',
            'nitrogen', 'oxygen', 'fluorine', 'neon', 'sodium', 'magnesium',
            'aluminum', 'silicon', 'phosphorus', 'sulfur', 'chlorine', 'argon',
            'potassium', 'calcium', 'scandium', 'titanium', 'vanadium',
            'chromium', 'manganese', 'iron', 'cobalt', 'nickel', 'copper',
            'zinc', 'gallium', 'germanium', 'arsenic', 'selenium', 'bromine',
            'krypton', 'rubidium', 'strontium', 'yttrium', 'zirconium',
            'niobium', 'molybdenum', 'technetium', 'ruthenium', 'rhodium',
            'palladium', 'silver', 'cadmium', 'indium', 'tin', 'antimony',
            'tellurium', 'iodine', 'xenon', 'cesium', 'barium', 'lanthanum',
            'cerium', 'praseodymium', 'neodymium', 'promethium', 'samarium',
            'europium', 'gadolinium', 'terbium', 'dysprosium', 'holmium',
            'erbium', 'thulium', 'ytterbium', 'lutetium', 'hafnium',
            'tantalum', 'tungsten', 'rhenium', 'osmium', 'iridium', 'platinum',
            'gold', 'mercury', 'thallium', 'lead', 'bismuth', 'polonium',
            'astatine', 'radon', 'francium', 'radium', 'actinium', 'thorium',
            'protactinium', 'uranium', 'neptunium', 'plutonium', 'americium',
            'curium', 'berkelium', 'californium', 'einsteinium', 'fermium',
            'mendelevium', 'nobelium', 'lawrencium', 'rutherfordium',
            'dubnium', 'seaborgium', 'bohrium', 'hassium', 'meitnerium',
            'darmstadtium', 'roentgenium', 'copernicium', 'nihonium',
            'flerovium', 'moscovium', 'livermorium', 'tennessine', 'oganesson']
