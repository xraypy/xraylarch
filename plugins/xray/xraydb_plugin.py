import sys
import larch
from larch import Group
from larch.larchlib import plugin_path

# put the 'std' and 'xafs' (this!) plugin directories into sys.path
sys.path.insert(0, plugin_path('xray'))

from xraydb import xrayDB

MODNAME = '_xray'

def get_xraydb(_larch):
    symname = '%s._xrayrefdb_' % MODNAME
    if not _larch.symtable.has_symbol(symname):
        _larch.symtable.set_symbol(symname, xrayDB())
    return _larch.symtable.get_symbol(symname)

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
    if _larch is None:  return
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
    if _larch is None:  return
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
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb.chantler_energies(element, emin=emain, emax=emax)

def f1_chantler(element, energy, _larch=None):
    """returns real part of anomalous x-ray scattering factor for
    a selected element and input energy (or array of energies) in eV.
    Data is from the Chantler tables.

    Values returned are in units of electrons

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    """
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb._getChantler(element, energy, column='f1')

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
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb._getChantler(element, energy, column='f2')

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
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    col = 'mu_total'
    if photo: col = 'mu_photo'
    if incoh: col = 'mu_incoh'
    return xdb._getChantler(element, energy, column=col)

def mu_elam(element, energy, _larch=None):
    """returns x-ray mass attenuation coefficient, mu/rho, for a
    selected element and input energy (or array of energies) in eV.
    Data is from the Elam tables.

    Values returned are in units of cm^2/gr.

    arguments
    ---------
    element:  atomic number, atomic symbol for element
    energy:   energy or array of energies in eV
    """
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb.mu_elam(element, energy)

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
    if _larch is None:
        return
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
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb.incoherent_cross_section_elam(element, energy)

def atomic_number(element, _larch=None):
    "return z for element name"
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return int(xdb._getElementData(element).atomic_number)

def atomic_symbol(z, _larch=None):
    "return element symbol from z"
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb._getElementData(z).element

def atomic_mass(element, _larch=None):
    "return molar mass (amu) from element symbol or atomic number"
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    if isinstance(element, int):
        element = symbol(element, _larch=_larch)
    return xdb._getElementData(element).molar_mass

def atomic_density(element, _larch=None):
    "return density (gr/cm^3) from element symbol or atomic number"
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    if isinstance(element, int):
        element = symbol(element, _larch=_larch)
    return xdb._getElementData(element).density

def xray_edges(element, _larch=None):
    """returns dictionary of all x-ray absorption edge energies
    (in eV), fluorescence yield, and jump ratio for an element.

    the returned dictionary has keys of edge (iupac symol),
    each with value containing a tuple of (energy,
    fluorescence_yield, edge_jump)

    Data from Elam, Ravel, and Sieber
    """
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb.xray_edges(element)

def xray_edge(element, edge, _larch=None):
    """returns edge energy (in eV), fluorescence yield, and
    jump ratio for an element and edge.

    Data from Elam, Ravel, and Sieber
    """
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb.xray_edge(element, edge)

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
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb.xray_lines(element, initial_level=initial_level,
                          excitation_energy=excitation_energy)

def CK_probability(element, initial, final, total=True, _larch=None):
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
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb.CK_probability(element, initial, final, total=total)

def core_width(element=None, edge=None, _larch=None):
    """returns core hole width for an element and edge

    arguments
    ---------
    if element is None, values are returned for all elements
    if edge is None, values are return for all edges


    Data from Keski-Rahkonen and Krause
    """
    if _larch is None:
        return
    xdb = get_xraydb(_larch)
    return xdb.corehole_width(element=element, edge=edge)


def registerLarchPlugin():
    return (MODNAME, {'f0': f0, 'f0_ions': f0_ions,
                      'f1_chantler': f1_chantler,
                      'f2_chantler': f2_chantler,
                      'mu_chantler': mu_chantler,
                      'mu_elam': mu_elam,
                      'coherent_cross_section_elam': coherent_cross_section_elam,
                      'incoherent_cross_section_elam': incoherent_cross_section_elam,
                      'atomic_number': atomic_number,
                      'atomic_symbol': atomic_symbol,
                      'atomic_mass':   atomic_mass,
                      'atomic_density': atomic_density,
                      'xray_edges': xray_edges,
                      'xray_edge': xray_edge,
                      'xray_lines': xray_lines,
                      'core_width':  core_width,
                      'CK_probability': CK_probability,
                      })


