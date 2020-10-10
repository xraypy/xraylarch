#!/usr/bin/env python
# models for debye-waller factors for xafs

import ctypes
import numpy as np
from larch.larchlib import get_dll

import scipy.constants as consts

# EINS_FACTOR  = hbarc*hbarc/(2 * k_boltz * amu) = 24.254360157751783
#    k_boltz = 8.6173324e-5  # [eV / K]
#    amu     = 931.494061e6  # [eV / (c*c)]
#    hbarc   = 1973.26938    # [eV * A]
EINS_FACTOR = 1.e20*consts.hbar**2/(2*consts.k*consts.atomic_mass)

FEFF6LIB = None


def sigma2_eins(t, theta, path):
    """calculate sigma2 for a Feff Path wih the einstein model

    sigma2 = sigma2_eins(t, theta, path)

    Parameters:
    -----------
      t        sample temperature (in K)
      theta    Einstein temperature (in K)
      path     FeffPath to calculate sigma2 for

    Notes:
       sigma2 = FACTOR*coth(2*t/theta)/(theta * mass_red)

    mass_red = reduced mass of Path (in amu)
    FACTOR  = hbarc*hbarc/(2*k_boltz*amu) ~= 24.25 Ang^2 * K * amu
    """
    feffpath = path._feffdat
    if feffpath is None:
        return 0.
    theta = max(float(theta), 1.e-5)
    t     = max(float(t), 1.e-5)
    rmass = 0.
    for sym, iz, ipot, amass, x, y, z in feffpath.geom:
        rmass = rmass + 1.0/max(0.1, amass)
    rmass = 1.0/max(1.e-12, rmass)
    return EINS_FACTOR/(theta * rmass * np.tanh(theta/(2.0*t)))

def sigma2_debye(t, theta, path):
    """calculate sigma2 for a Feff Path wih the correlated Debye model

    sigma2 = sigma2_debye(t, theta, path)

    Parameters:
    -----------
      t        sample temperature (in K)
      theta    Debye temperature (in K)
      path     FeffPath to calculate sigma2 for 
    """
    feffpath = path._feffdat
    if feffpath is None:
        return 0.
    thetad = max(float(theta), 1.e-5)
    tempk  = max(float(t), 1.e-5)
    natoms = len(feffpath.geom)
    rnorm  = feffpath.rnorman
    atomx, atomy, atomz, atomm = [], [], [], []
    for sym, iz, ipot, am, x, y, z in feffpath.geom:
        atomx.append(x)
        atomy.append(y)
        atomz.append(z)
        atomm.append(am)

    return sigma2_correldebye(natoms, tempk, thetad, rnorm,
                              atomx, atomy, atomz, atomm)

def sigma2_correldebye(natoms, tk, theta, rnorm, x, y, z, atwt):
    """
    internal sigma2 calc for a Feff Path wih the correlated Debye model

    these routines come courtesy of jj rehr and si zabinsky.

    Arguments:
      natoms  *int, lengths for x, y, z, atwt        [in]
      tk      *double, sample temperature (K)        [in]
      theta   *double, Debye temperature (K)         [in]
      rnorm   *double, Norman radius (Ang)           [in]
      x       *double, array of x coord (Ang)        [in]
      y       *double, array of y coord (Ang)        [in]
      x       *double, array of z coord (Ang)        [in]
      atwt    *double, array of atomic_weight (amu)  [in]

   Returns:
      sig2_cordby  double, calculated sigma2
    """
    global FEFF6LIB
    if FEFF6LIB is None:
        FEFF6LIB = get_dll('feff6')
        FEFF6LIB.sigma2_debye.restype = ctypes.c_double

    na = ctypes.pointer(ctypes.c_int(natoms))
    t  = ctypes.pointer(ctypes.c_double(tk))
    th = ctypes.pointer(ctypes.c_double(theta))
    rs = ctypes.pointer(ctypes.c_double(rnorm))

    ax = (natoms*ctypes.c_double)()
    ay = (natoms*ctypes.c_double)()
    az = (natoms*ctypes.c_double)()
    am = (natoms*ctypes.c_double)()

    for i in range(natoms):
        ax[i], ay[i], az[i], am[i] = x[i], y[i], z[i], atwt[i]

    return FEFF6LIB.sigma2_debye(na, t, th, rs, ax, ay, az, am)


def sigma2_correldebye_py(natoms, tk, theta, rnorm, x, y, z, atwt):
    """calculate the XAFS debye-waller factor for a path based
    on the temperature, debye temperature, average norman radius,
    atoms in the path, and their positions.

    these routines come courtesy of jj rehr and si zabinsky.

    Arguments:
      natoms  *int, lengths for x, y, z, atwt        [in]
      tk      *double, sample temperature (K)        [in]
      theta   *double, Debye temperature (K)         [in]
      rnorm   *double, Norman radius (Ang)           [in]
      x       *double, array of x coord (Ang)        [in]
      y       *double, array of y coord (Ang)        [in]
      x       *double, array of z coord (Ang)        [in]
      atwt    *double, array of atomic_weight (amu)  [in]

   Returns:
      sig2_cordby  double, calculated sigma2

   Notes:
     1. natoms must be >= 2.
     2. rnorman is the wigner-seitz or norman radius,
        averaged over entire problem:
             (4pi/3)*rs**3 = sum( (4pi/3)rnrm**3 ) / n
             (sum is over all atoms in the problem)
     3. all distances are in Angstroms

    moved from Feff6 sigms.f, original copyright:
    copyright 1993  university of washington
                    john rehr, steve zabinsky, matt newville
    """
    sig2 = 0.0
    for i0 in range(natoms):
        i1 = (i0 + 1) % natoms
        for j0 in range(i0, natoms):
            j1 = (j0 + 1) %  natoms
            # calculate r_i-r_i-1 and r_j-r_j-1 and the rest of the
            # distances, and get the partial cosine term:
            #   cosine(i,j) = r_i.r_j / ((r_i0- r_i-1) * (r_j - r_j-1))
            ri0j0  = dist(x[i0], y[i0], z[i0], x[j0], y[j0], z[j0])
            ri1j1  = dist(x[i1], y[i1], z[i1], x[j1], y[j1], z[j1])
            ri0j1  = dist(x[i0], y[i0], z[i0], x[j1], y[j1], z[j1])
            ri1j0  = dist(x[i1], y[i1], z[i1], x[j0], y[j0], z[j0])
            ri0i1  = dist(x[i0], y[i0], z[i0], x[i1], y[i1], z[i1])
            rj0j1  = dist(x[j0], y[j0], z[j0], x[j1], y[j1], z[j1])
            ridotj = ( (x[i0] - x[i1]) * (x[j0] - x[j1]) +
                       (y[i0] - y[i1]) * (y[j0] - y[j1]) +
                       (z[i0] - z[i1]) * (z[j0] - z[j1]) )

            #  call corrfn to get the correlations between atom pairs
            ci0j0 = corrfn(ri0j0, theta, tk, atwt[i0], atwt[j0], rnorm)
            ci1j1 = corrfn(ri1j1, theta, tk, atwt[i1], atwt[j1], rnorm)
            ci0j1 = corrfn(ri0j1, theta, tk, atwt[i0], atwt[j1], rnorm)
            ci1j0 = corrfn(ri1j0, theta, tk, atwt[i1], atwt[j0], rnorm)

            # combine outputs of corrfn to give the debye-waller factor for
            # this atom pair. !! note: don't double count (i.eq.j) terms !!!
            sig2ij = ridotj*(ci0j0 + ci1j1 - ci0j1 - ci1j0)/(ri0i1*rj0j1)
            if j0 == i0:
                sig2ij /= 2.0
            sig2 += sig2ij

    return sig2/2.0



def dist(x0, y0, z0, x1, y1, z1):
    """find distance between cartesian points
    (x, y, z)0 and (x, y, z)1
    port of Fortran from feff6 sigms.f
    """
    return np.sqrt( (x0-x1)**2 + (y0-y1)**2 + (z0-z1)**2 )

def corrfn(rij, theta, tk, am1, am2, rs):
    """calculate correlation function
    c(ri, rj) = <xi xj> in the debye approximation

    ported from feff6 sigms.f

    copyright 1993  university of washington
                    john rehr, steve zabinsky, matt newville

    subroutine calculates correlation function
    c(ri, rj) = <xi xj> in the debye approximation
              = (1/n)sum_k exp(ik.(ri-rj)) (1/sqrt(mi*mj))*
                               (hbar/2w_k)*coth(beta hbar w_k/2)

              = (3kt/mu w_d**2) * sqrt(mu**2/mi*mj) * int
    where :
        x        k_d*r (distance parameter)  r distance in angstroms
        theta    debye temp in degrees k
        tk       temperature in degrees k
        temper   theta / tk = hbar omegad/kt
        k_d      debye wave number = (6*pi**2 n/v)
        n/v      free electron number density = 1/(4pi/3rs**3)
        rs       wigner seitz or norman radius in bohr
        ami      atomic mass at sites i in amu
        amj      atomic mass at sites j in amu
        int      int_0^1 (temper/x) dw sin(wx)coth(w*temper/2)

    solution by numerical integration, with parameters pi, bohr, con:
      con=hbar**2/kb*amu)*10**20   in ang**2 units
      k_boltz = 8.6173324e-5  # [eV / K]
      amu     = 931.494061e6  # [eV / (c*c)]
      hbarc   = 1973.26938    # [eV * A]
      bohr    = 0.52917721    # [A]
    conh = (3/2.)* hbar**2 / (kb*amu) ~= 72.76
    conr = (9*pi/2)**(1/3.0) / bohr   ~=  4.57

    NOTE: for backward compatibility, the constants used by feff6 are
    retained, even though some have been refined later.
    """
    conh = 72.7630804732553
    conr = 4.5693349700844

    # theta in degrees k, t temperature in degrees k
    rx     = conr  * rij / rs
    tx     = theta / tk
    rmass  = theta * np.sqrt(am1 * am2)
    return conh  * debint(rx, tx) / rmass

def debfun(w, rx, tx):
    """ debye function, ported from feff6 sigms.f

    copyright 1993  university of washington
                    john rehr, steve zabinsky, matt newville

    debfun = (sin(w*rx)/rx) * coth(w*tx/2)
    """
    # print(" debfun ", w, rx, tx)
    wmin = 1.e-20
    argmax = 50.0
    result = 2.0 / tx
    #  allow t = 0 without bombing
    if w > wmin:
        result = w
        if rx > 0:
            result = np.sin(w*rx) / rx
        emwt = np.exp( -min(w*tx, argmax))
        result *=  (1 + emwt) / (1 - emwt)
    return result

def debint(rx, tx):
    """ calculates integrals between [0,1]  b = int_0^1 f(z) dz
    by trapezoidal rule and binary refinement  (romberg integration)
    ported from feff6 sigms.f:

    copyright 1993  university of washington
                   john rehr, steve zabinsky, matt newville

    subroutine calculates integrals between [0,1]  b = int_0^1 f(z) dz
    by trapezoidal rule and binary refinement  (romberg integration)
    coded by j rehr (10 feb 92)   see, e.g., numerical recipes
    for discussion and a much fancier version
    """
    MAXITER = 12
    tol = 1.e-9
    itn = 1
    step = 1.0
    result = 0.0
    bo = bn = (debfun(0.0, rx, tx) + debfun(1.0, rx, tx))/2.0
    for iter in range(MAXITER):
        #  nth iteration
        #   b_n+1=(b_n)/2+deln*sum_0^2**n f([2n-1]deln)
        step = step / 2.
        sum = 0
        for i in range(itn):
            sum += debfun(step*(2*i + 1), rx, tx)
        itn  = 2*itn
        #  bnp1=b_n+1 is current value of integral
        #  cancel leading error terms b=[4b-bn]/3
        #  note: this is the first term in the neville table - remaining
        #        errors were found too small to justify the added code
        bnp1   = step * sum + (bn / 2.0)
        result = (4 * bnp1 - bn) / 3.0
        if (abs( (result - bo) / result) < tol):
            break
        bn = bnp1
        bo = result
    return result


####################################################
## sigma2_eins and sigma2_debye are defined here to
## be injected as Procedures within lmfit's asteval
## for calculating XAFS sigma2 for a scattering path
## these use `reff` or `feffpath.geom` which will be updated
## for each path during an XAFS path calculation
##
_sigma2_funcs = """
def sigma2_eins(t, theta):
    if feffpath is None:
         return 0.
    theta = max(float(theta), 1.e-5)
    t     = max(float(t), 1.e-5)
    rmass = 0.
    for sym, iz, ipot, amass, x, y, z in feffpath.geom:
        rmass = rmass + 1.0/max(0.1, amass)
    rmass = 1.0/max(1.e-12, rmass)
    return EINS_FACTOR/(theta * rmass * tanh(theta/(2.0*t)))

def sigma2_debye(t, theta):
    if feffpath is None:
         return 0.
    thetad = max(float(theta), 1.e-5)
    tempk  = max(float(t), 1.e-5)
    natoms = len(feffpath.geom)
    rnorm  = feffpath.rnorman
    atomx, atomy, atomz, atomm = [], [], [], []
    for sym, iz, ipot, am, x, y, z in feffpath.geom:
        atomx.append(x)
        atomy.append(y)
        atomz.append(z)
        atomm.append(am)

    return sigma2_correldebye(natoms, tempk, thetad, rnorm,
                              atomx, atomy, atomz, atomm)
"""
def add_sigma2funcs(params):
    """set sigma2funcs into Parameters' asteval"""
    f_eval = params._asteval
    f_eval.symtable['EINS_FACTOR'] = EINS_FACTOR
    f_eval.symtable['sigma2_correldebye'] = sigma2_correldebye
    f_eval.symtable['feffpath'] = None
    f_eval(_sigma2_funcs)
