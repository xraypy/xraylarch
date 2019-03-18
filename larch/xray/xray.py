import sys
import numpy as np
from math import pi
import larch
from larch import Group
from larch.math import index_nearest
from ..utils.physical_constants import (R_ELECTRON_CM, AVOGADRO,
                                        PLANCK_HC)
from .xraydb import  XrayDB
from .chemparser import chemparse

_xraydb = None

MODNAME = '_xray'

_edge_energies = {'k': np.array([-1.0, 13.6, 24.6, 54.7, 111.5, 188.0,
                                 284.2, 409.9, 543.1, 696.7, 870.2, 1070.8,
                                 1303.0, 1559.0, 1839.0, 2145.5, 2472.0,
                                 2822.0, 3205.9, 3608.4, 4038.5, 4492.0,
                                 4966.0, 5465.0, 5989.0, 6539.0, 7112.0,
                                 7709.0, 8333.0, 8979.0, 9659.0, 10367.0,
                                 11103.0, 11867.0, 12658.0, 13474.0,
                                 14326.0, 15200.0, 16105.0, 17038.0,
                                 17998.0, 18986.0, 20000.0, 21044.0,
                                 22117.0, 23220.0, 24350.0, 25514.0,
                                 26711.0, 27940.0, 29200.0, 30491.0,
                                 31814.0, 33169.0, 34561.0, 35985.0,
                                 37441.0, 38925.0, 40443.0, 41991.0,
                                 43569.0, 45184.0, 46834.0, 48519.0,
                                 50239.0, 51996.0, 53789.0, 55618.0,
                                 57486.0, 59390.0, 61332.0, 63314.0,
                                 65351.0, 67416.0, 69525.0, 71676.0,
                                 73871.0, 76111.0, 78395.0, 80725.0,
                                 83102.0, 85530.0, 88005.0, 90526.0,
                                 93105.0, 95730.0, 98404.0, 101137.0,
                                 103922.0, 106755.0, 109651.0, 112601.0,
                                 115606.0, 118669.0, 121791.0, 124982.0,
                                 128241.0, 131556.0]),

                  'l3': np.array([-1.0, -1.0, -1.0, -1.0, 3.0, 4.7, 7.2,
                                  17.5, 18.2, 19.9, 21.6, 30.5, 49.2, 72.5,
                                  99.2, 135.0, 162.5, 200.0, 248.4, 294.6,
                                  346.2, 398.7, 453.8, 512.1, 574.1, 638.7,
                                  706.8, 778.1, 852.7, 932.7, 1021.8,
                                  1116.4, 1217.0, 1323.6, 1433.9, 1550.0,
                                  1678.4, 1804.0, 1940.0, 2080.0, 2223.0,
                                  2371.0, 2520.0, 2677.0, 2838.0, 3004.0,
                                  3173.0, 3351.0, 3538.0, 3730.0, 3929.0,
                                  4132.0, 4341.0, 4557.0, 4786.0, 5012.0,
                                  5247.0, 5483.0, 5723.0, 5964.0, 6208.0,
                                  6459.0, 6716.0, 6977.0, 7243.0, 7514.0,
                                  7790.0, 8071.0, 8358.0, 8648.0, 8944.0,
                                  9244.0, 9561.0, 9881.0, 10207.0, 10535.0,
                                  10871.0, 11215.0, 11564.0, 11919.0,
                                  12284.0, 12658.0, 13035.0, 13419.0,
                                  13814.0, 14214.0, 14619.0, 15031.0,
                                  15444.0, 15871.0, 16300.0, 16733.0,
                                  17166.0, 17610.0, 18057.0, 18510.0,
                                  18970.0, 19435.0]),

                  'l2': np.array([-1.0, -1.0, -1.0, -1.0, 3.0, 4.7, 7.2,
                                  17.5, 18.2, 19.9, 21.7, 30.4, 49.6, 72.9,
                                  99.8, 136.0, 163.6, 202.0, 250.6, 297.3,
                                  349.7, 403.6, 460.2, 519.8, 583.8, 649.9,
                                  719.9, 793.2, 870.0, 952.3, 1044.9,
                                  1143.2, 1248.1, 1359.1, 1474.3, 1596.0,
                                  1730.9, 1864.0, 2007.0, 2156.0, 2307.0,
                                  2465.0, 2625.0, 2793.0, 2967.0, 3146.0,
                                  3330.0, 3524.0, 3727.0, 3938.0, 4156.0,
                                  4380.0, 4612.0, 4852.0, 5107.0, 5359.0,
                                  5624.0, 5891.0, 6164.0, 6440.0, 6722.0,
                                  7013.0, 7312.0, 7617.0, 7930.0, 8252.0,
                                  8581.0, 8918.0, 9264.0, 9617.0, 9978.0,
                                  10349.0, 10739.0, 11136.0, 11544.0,
                                  11959.0, 12385.0, 12824.0, 13273.0,
                                  13734.0, 14209.0, 14698.0, 15200.0,
                                  15711.0, 16244.0, 16785.0, 17337.0,
                                  17907.0, 18484.0, 19083.0, 19693.0,
                                  20314.0, 20948.0, 21600.0, 22266.0,
                                  22952.0, 23651.0, 24371.0]),


                  'l1': np.array([-1.0, -1.0, -1.0, 5.3, 8.0, 12.6, 18.0,
                                  37.3, 41.6, 45.0, 48.5, 63.5, 88.6,
                                  117.8, 149.7, 189.0, 230.9, 270.0, 326.3,
                                  378.6, 438.4, 498.0, 560.9, 626.7, 696.0,
                                  769.1, 844.6, 925.1, 1008.6, 1096.7,
                                  1196.2, 1299.0, 1414.6, 1527.0, 1652.0,
                                  1782.0, 1921.0, 2065.0, 2216.0, 2373.0,
                                  2532.0, 2698.0, 2866.0, 3043.0, 3224.0,
                                  3412.0, 3604.0, 3806.0, 4018.0, 4238.0,
                                  4465.0, 4698.0, 4939.0, 5188.0, 5453.0,
                                  5714.0, 5989.0, 6266.0, 6548.0, 6835.0,
                                  7126.0, 7428.0, 7737.0, 8052.0, 8376.0,
                                  8708.0, 9046.0, 9394.0, 9751.0, 10116.0,
                                  10486.0, 10870.0, 11271.0, 11682.0,
                                  12100.0, 12527.0, 12968.0, 13419.0,
                                  13880.0, 14353.0, 14839.0, 15347.0,
                                  15861.0, 16388.0, 16939.0, 17493.0,
                                  18049.0, 18639.0, 19237.0, 19840.0,
                                  20472.0, 21105.0, 21757.0, 22427.0,
                                  23104.0, 23808.0, 24526.0, 25256.0]),

                  'm5': np.array([-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0,
                                  -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0,
                                  -1.0, -1.0, -1.0, -1.0, -1.0, -1.0,
                                  -1.0,-1.0, 2.0, 2.0, 2.0, 2.0, 2.0, 3.0,
                                  4.0, 5.0, 10.1, 18.7, 29.2, 41.7,
                                  54.6,69.0, 93.8, 112.0, 134.2, 155.8,
                                  178.8, 202.3, 227.9, 253.9, 280.0,
                                  307.2,335.2, 368.3, 405.2, 443.9, 484.9,
                                  528.2, 573.0, 619.3, 676.4, 726.6,780.5,
                                  836.0, 883.8, 928.8, 980.4, 1027.0,
                                  1083.4, 1127.5, 1189.6, 1241.1, 1292.0,
                                  1351.0, 1409.0, 1468.0, 1528.0, 1589.0,
                                  1662.0, 1735.0, 1809.0, 1883.0, 1960.0,
                                  2040.0, 2122.0, 2206.0, 2295.0, 2389.0,
                                  2484.0, 2580.0, 2683.0, 2787.0, 2892.0,
                                  3000.0, 3105.0, 3219.0, 3332.0, 3442.0,
                                  3552.0, 3664.0, 3775.0, 3890.0, 4009.0,
                                  4127.0])}


def get_xraydb(_larch=None):
    global _xraydb
    if _xraydb is None:
        _xraydb = XrayDB(dbname='xraydata.db')
    if _larch is not None:
        symname = '%s._xraydb' % MODNAME
        if not _larch.symtable.has_symbol(symname):
            _larch.symtable.set_symbol(symname, _xraydb)
    return _xraydb

def f0(ion, q, _larch=None):
    """returns elastic x-ray scattering factor, f0(q), for an ion.

    based on calculation from
       D. Waasmaier and A. Kirfel, Acta Cryst. A51 p416 (1995)
    and tables from International Tables for Crystallography, Vol. C.

    arguments
    ---------
    ion:  atomic number, atomic symbol or ionic symbol
           (case insensitive) of scatterer

    q:    single q value, list, tuple, or numpy array of q value
              q = sin(theta) / lambda
          theta = incident angle, lambda = x-ray wavelength
    Z values from 1 to 98 (and symbols 'H' to 'Cf') are supported.
    The list of ionic symbols can be read with the function .f0_ions()
    """
    xdb = get_xraydb(_larch)
    return xdb.f0(ion, q)

def f0_ions(element=None, _larch=None):
    """return list of ion names supported in the f0() calculation from
    Waasmaier and Kirfel.

    arguments
    ---------
    element:  atomic number, atomic symbol or ionic symbol
              (case insensitive) of scatterer

    if element is None, all 211 ions are returned.  If element is
    not None, the ions for that element (atomic symbol) are returned
    """
    xdb = get_xraydb(_larch)
    return xdb.f0_ions(element=element)

def chantler_energies(element, emin=0, emax=1.e9, _larch=None):
    """ return array of energies (in eV) at which data is
    tabulated in the Chantler tables for a particular element.

    arguments
    ---------
    element:  atomic number, atomic symbol for element

    emin:  lower bound of energies in eV returned (default=0)
    emax:  upper bound of energies in eV returned (default=1.e9)
    """
    xdb = get_xraydb(_larch)
    return xdb.chantler_energies(element, emin=emin, emax=emax)


def chantler_data(element, energy, column, _larch=None, **kws):
    """returns data from Chantler tables.

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    column:   one of 'f1', 'f2', 'mu_photo', 'mu_incoh', 'mu_total'
    """
    xdb = get_xraydb(_larch)
    return xdb._from_chantler(element, energy, column=column, **kws)


def f1_chantler(element, energy, _larch=None, **kws):
    """returns real part of anomalous x-ray scattering factor for
    a selected element and input energy (or array of energies) in eV.
    Data is from the Chantler tables.

    Values returned are in units of electrons

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    """
    xdb = get_xraydb(_larch)
    return xdb._from_chantler(element, energy, column='f1', **kws)


def f2_chantler(element, energy, _larch=None):
    """returns imaginary part of anomalous x-ray scattering factor for
    a selected element and input energy (or array of energies) in eV.
    Data is from the Chantler tables.

    Values returned are in units of electrons.

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    """
    xdb = get_xraydb(_larch)
    return xdb._from_chantler(element, energy, column='f2')


def mu_chantler(element, energy, incoh=False, photo=False, _larch=None):
    """returns x-ray mass attenuation coefficient, mu/rho, for a
    selected element and input energy (or array of energies) in eV.
    Data is from the Chantler tables.

    Values returned are in units of cm^2/gr.

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    photo=True: flag to return only the photo-electric contribution
    incoh=True: flag to return only the incoherent contribution

    The default is to return total attenuation coefficient.
    """
    xdb = get_xraydb(_larch)
    col = 'mu_total'
    if photo: col = 'mu_photo'
    if incoh: col = 'mu_incoh'
    return xdb._from_chantler(element, energy, column=col)


def mu_elam(element, energy, kind='total', _larch=None):
    """returns x-ray mass attenuation coefficient, mu/rho, for a
    selected element and input energy (or array of energies) in eV.
    Data is from the Elam tables.

    Values returned are in units of cm^2/gr.

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    kind:     one of 'total' (default) 'photo', 'coh', and 'incoh' for
              total, photo-absorption, coherent scattering, and
              incoherent scattering cross sections, respectively.

    Data from Elam, Ravel, and Sieber.
    """
    xdb = get_xraydb(_larch)
    return xdb.mu_elam(element, energy, kind=kind)


def coherent_cross_section_elam(element, energy, _larch=None):
    """returns coherent scattering cross section
    selected element and input energy (or array of energies) in eV.
    Data is from the Elam tables.

    Values returned are in units of cm^2/gr.

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    """
    xdb = get_xraydb(_larch)
    return xdb.coherent_cross_section_elam(element, energy)


def incoherent_cross_section_elam(element, energy, _larch=None):
    """returns incoherent scattering cross section
    selected element and input energy (or array of energies) in eV.
    Data is from the Elam tables.

    Values returned are in units of cm^2/gr.

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    """
    xdb = get_xraydb(_larch)
    return xdb.incoherent_cross_section_elam(element, energy)


def atomic_number(element, _larch=None):
    "return z for element name"
    xdb = get_xraydb(_larch)
    return int(xdb._elem_data(element).atomic_number)


def atomic_symbol(z, _larch=None):
    "return element symbol from z"
    xdb = get_xraydb(_larch)
    return xdb._elem_data(z).symbol


def atomic_mass(element, _larch=None):
    "return molar mass (amu) from element symbol or atomic number"
    xdb = get_xraydb(_larch)
    if isinstance(element, int):
        element = atomic_symbol(element)
    return xdb._elem_data(element).mass


def atomic_density(element, _larch=None):
    "return density (gr/cm^3) from element symbol or atomic number"
    xdb = get_xraydb(_larch)
    if isinstance(element, int):
        element = atomic_symbol(element)
    return xdb._elem_data(element).density


def xray_edges(element, _larch=None):
    """returns dictionary of all x-ray absorption edge energies
    (in eV), fluorescence yield, and jump ratio for an element.

    the returned dictionary has keys of edge (iupac symol),
    each with value containing a tuple of (energy,
    fluorescence_yield, edge_jump)

    Data from Elam, Ravel, and Sieber
    """
    xdb = get_xraydb(_larch)
    return xdb.xray_edges(element)


def xray_edge(element, edge, energy_only=False, _larch=None):
    """returns edge energy (in eV), fluorescence yield, and
    jump ratio for an element and edge.

    Data from Elam, Ravel, and Sieber
    """
    xdb = get_xraydb(_larch)
    out = xdb.xray_edge(element, edge)
    if energy_only:
        out = out[0]
    return out


def xray_lines(element, initial_level=None, excitation_energy=None,
               _larch=None):
    """returns dictionary of x-ray emission lines of an element, with
    key = siegbahn symbol (Ka1, Lb1, etc)  and
    value = (energy (in eV), intensity, initial_level, final_level)

    arguments
    ---------
    element:           atomic number, atomic symbol for element
    initial_level:     limit output to an initial level(s) -- a string or list of strings
    excitation_energy: limit output to those excited by given energy (in eV)

    Note that excitation energy will overwrite initial_level, as it means
       'all intial levels with below this energy/

    Data from Elam, Ravel, and Sieber.
    """
    xdb = get_xraydb(_larch)
    return xdb.xray_lines(element, initial_level=initial_level,
                          excitation_energy=excitation_energy)


def xray_line(element, line='Ka', _larch=None):
    """returns data for an  x-ray emission lines of an element, given
    the siegbahn notation for the like (Ka1, Lb1, etc).  Returns:
         energy (in eV), intensity, initial_level, final_level

    arguments
    ---------
    element:   atomic number, atomic symbol for element
    line:      siegbahn notation for emission line

    if line is 'Ka', 'Kb', 'La', 'Lb', 'Lg', without number,
    the weighted average for this family of lines is returned.

    Data from Elam, Ravel, and Sieber.
    """
    xdb = get_xraydb(_larch)
    lines = xdb.xray_lines(element)

    family = line.lower()
    if family == 'k': family = 'ka'
    if family == 'l': family = 'la'
    if family in ('ka', 'kb', 'la', 'lb', 'lg'):
        scale = 1.e-99
        value = 0.0
        linit, lfinal =  None, None
        for key, val in lines.items():
            if key.lower().startswith(family):
                value += val[0]*val[1]
                scale += val[1]
                if linit is None:
                    linit = val[2]
                if lfinal is None:
                    lfinal = val[3][0]
        return (value/scale, scale, linit, lfinal)
    else:
        return lines.get(line.title(), None)


def fluo_yield(symbol, edge, emission, energy,
               energy_margin=-150, _larch=None):
    """Given
         atomic_symbol, edge, emission family, and incident energy,

    where 'emission' is the family of emission lines ('Ka', 'Kb', 'Lb', etc)
    returns

    fluorescence_yield, weighted-average fluorescence energy, net_probability

    fyield = 0  if energy < edge_energy + energy_margin (default=-150)

    > fluo_yield('Fe', 'K', 'Ka', 8000)
    0.350985, 6400.752419799043, 0.874576096

    > fluo_yield('Fe', 'K', 'Ka', 6800)
    0.0, 6400.752419799043, 0.874576096

    > fluo_yield('Ag', 'L3', 'La', 6000)
    0.052, 2982.129655446868, 0.861899000000000

    compare to xray_lines() which gives the full set of emission lines
    ('Ka1', 'Kb3', etc) and probabilities for each of these.

    Adapted for Larch from code by Yong Choi
    """
    e0, fyield, jump = xray_edge(symbol, edge)
    trans  = xray_lines(symbol, initial_level=edge)

    lines = []
    net_ener, net_prob = 0., 0.
    for name, vals in trans.items():
        en, prob = vals[0], vals[1]
        if name.startswith(emission):
            lines.append([name, en, prob])

    for name, en, prob in lines:
        if name.startswith(emission):
            net_ener += en*prob
            net_prob += prob
    if net_prob <= 0:
        net_prob = 1
    net_ener = net_ener / net_prob
    if energy < e0 + energy_margin:
        fyield = 0
    return fyield, net_ener, net_prob


def ck_probability(element, initial, final, total=True, _larch=None):
    """return transition probability for an element, initial, and final levels.

    arguments
    ---------
    element:     atomic number, atomic symbol for element
    initial:     initial level ('K', 'L1', ...)
    final:       final level ('L1', 'L2', ...)
    total:       whether to include transitions via possible intermediate
                 levels (default = True)

    Data from Elam, Ravel, and Sieber.
    """
    xdb = get_xraydb(_larch)
    return xdb.ck_probability(element, initial, final, total=total)

CK_probability = ck_probability

def core_width(element, edge=None, _larch=None):
    """returns core hole width for an element and edge

    arguments
    ---------
    if edge is None, values are return for all edges


    Data from Krause and Oliver (1979) and
    Keski-Rahkonen and Krause (1974)
    """
    xdb = get_xraydb(_larch)
    return xdb.corehole_width(element, edge=edge)

def guess_edge(energy, edges=['K', 'L3', 'L2', 'L1', 'M5'], _larch=None):
    """guess an element and edge based on energy (in eV)

    Arguments
    ---------
    energy (float) : approximate edge energy (in eV)
    edges (list of strings) : edges to consider ['K', 'L3', 'L2', 'L1', 'M5']

    Returns
    -------
      (element symbol, edge)
    """
    xdb = get_xraydb(_larch)
    ret = []
    min_diff = 1e9

    for edge in edges:
        ename =  edge.lower()
        # if not already in _edge_energies, look it up and save it now

        if ename not in _edge_energies:
            energies = [-1000]*150
            maxz = 0
            for row in xdb.tables['xray_levels'].select().execute().fetchall():
                ir, elem, edgename, en, eyield, xjump = row
                iz = xdb.atomic_number(elem)
                maxz = max(iz, maxz)
                if ename == edgename.lower():
                    energies[iz] = en
            _edge_energies[ename] = np.array(energies[:maxz])
            if _larch is not None:
                symname = '%s._edges_%s'  % (MODNAME, ename)
                _larch.symtable.set_symbol(symname, _edge_energies[ename])

        energies = _edge_energies[ename]
        iz = int(index_nearest(energies, energy))
        diff = energy - energies[iz]
        if diff < 0: # prefer positive errors
            diff = -2.0*diff
        if iz < 10 or iz > 92: # penalize extreme elements
            diff = 2.0*diff
        if edge == 'K': # prefer K edge
            diff = 0.25*diff
        elif edge in ('L1', 'M5'): # penalize L1 and M5 edges
            diff = 2.0*diff
        if diff < min_diff:
            min_diff = diff
        ret.append((edge, iz, diff))

    for edge, iz, diff in ret:
        if abs(diff - min_diff) < 2:
            return (atomic_symbol(iz), edge)
    return (None, None)


class Scatterer:
    """Scattering Element

    lamb=PLANCK_HC /(eV0/1000.)*1e-11    # in cm, 1e-8cm = 1 Angstrom
    Xsection=2* R_ELECTRON_CM *lamb*f2/BARN    # in Barns/atom
    """
    def __init__(self, symbol, energy=10000, _larch=None):
        # atomic symbol and incident x-ray energy (eV)
        self.symbol = symbol
        self.number = atomic_number(symbol)
        self.mass   = atomic_mass(symbol)
        self.f1     = chantler_data(symbol, energy, 'f1')
        self.f1     = self.f1 + self.number
        self.f2     = chantler_data(symbol, energy, 'f2')
        self.mu_photo = chantler_data(symbol, energy, 'mu_photo')
        self.mu_total = chantler_data(symbol, energy, 'mu_total')

def xray_delta_beta(material, density, energy, photo_only=False, _larch=None):
    """
    return anomalous components of the index of refraction for a material,
    using the tabulated scattering components from Chantler.

    arguments:
    ----------
       material:   chemical formula  ('Fe2O3', 'CaMg(CO3)2', 'La1.9Sr0.1CuO4')
       density:    material density in g/cm^3
       energy:     x-ray energy in eV
       photo_only: boolean for returning photo cross-section component only
                   if False (default), the total cross-section is returned
    returns:
    ---------
      (delta, beta, atlen)

    where
      delta :  real part of index of refraction
      beta  :  imag part of index of refraction
      atlen :  attenuation length in cm

    These are the anomalous scattering components of the index of refraction:

    n = 1 - delta - i*beta = 1 - lambda**2 * r0/(2*pi) Sum_j (n_j * fj)

    Adapted for Larch from code by Yong Choi
    """
    lamb_cm = 1.e-8 * PLANCK_HC / energy # lambda in cm
    elements = []
    for symbol, number in chemparse(material).items():
        elements.append((number, Scatterer(symbol, energy, _larch=_larch)))

    total_mass, delta, beta_photo, beta_total = 0, 0, 0, 0
    for (number, scat) in elements:
        weight      = density*number*AVOGADRO
        delta      += weight * scat.f1
        beta_photo += weight * scat.f2
        beta_total += weight * scat.f2*(scat.mu_total/scat.mu_photo)
        total_mass += number * scat.mass

    scale = lamb_cm * lamb_cm * R_ELECTRON_CM / (2*pi * total_mass)
    delta = delta * scale
    beta  = beta_total * scale
    if photo_only:
        beta  = beta_photo * scale
    return delta, beta, lamb_cm/(4*pi*beta)
