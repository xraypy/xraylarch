# Useful physical constants
# most of these are put into common X-ray units (Angstroms, ev)

import scipy.constants as consts
from numpy import pi

RAD2DEG  = 180.0/pi
DEG2RAD  = pi/180.0

# cross-section unit
BARN     = 1.e-24   # cm^2

# atoms/mol =  6.0221413e23  atoms/mol
AVOGADRO = consts.Avogadro

# ATOMIC MASS in grams
AMU = consts.atomic_mass * 1000.0

# Planck's Constant
#   h*c    ~= 12398.42 eV*Ang
#   hbar*c ~=  1973.27 eV*Ang
PLANCK_HC    = 1.e10 * consts.Planck * consts.c / consts.e
PLANCK_HBARC = PLANCK_HC / (2*pi)

# classical electron radius in cm
R_ELECTRON_CM  = 100.0 * consts.codata.physical_constants['classical electron radius'][0]
R_ELECTRON_ANG = 1.e10 * consts.codata.physical_constants['classical electron radius'][0]
