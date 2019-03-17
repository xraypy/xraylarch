import os
import numpy as np
from larch import site_config
from .chemparser import chemparse
from .xray import mu_elam, atomic_mass

MODNAME = '_xray'
_materials = None

def get_materials(_larch=None):
    """return _materials dictionary, creating it if needed"""
    global _materials
    if _materials is None:
        # initialize materials table
        _materials = {}

        def read_materialsfile(fname):
            with open(fname, 'r') as fh:
                lines = fh.readlines()
            for line in lines:
                line = line.strip()
                if len(line) > 2 and not line.startswith('#'):
                    try:
                        name, f, den = [i.strip() for i in line.split('|')]
                        name = name.lower()
                        _materials[name] = (f.replace(' ', ''), float(den))
                    except:
                        pass

        # first, read from standard list
        local_dir, _ = os.path.split(__file__)
        fname = os.path.join(local_dir, 'materials.dat')
        if os.path.exists(fname):
            read_materialsfile(fname)

        # next, read from local materials file, if defined
        fname = os.path.join(site_config.usr_larchdir, 'materials.dat')
        if os.path.exists(fname):
            read_materialsfile(fname)

        if _larch is not None :
            symname = '%s._materials' % MODNAME
            _larch.symtable.set_symbol(symname, _materials)
    return _materials

def material_mu(name, energy, density=None, kind='total', _larch=None):
    """
    material_mu(name, energy, density=None, kind='total')

    return X-ray attenuation length (in 1/cm) for a material by name or formula

    arguments
    ---------
     name:     chemical formul or name of material from materials list.
     energy:   energy or array of energies in eV
     density:  material density (gr/cm^3).  If None, and material is a
               known material, that density will be used.
     kind:     'photo' or 'total' (default) for whether to
               return photo-absorption or total cross-section.
    returns
    -------
     mu, absorption length in 1/cm

    notes
    -----
      1.  material names are not case sensitive,
          chemical compounds are case sensitive.
      2.  mu_elam() is used for mu calculation.

    example
    -------
      >>> print(material_mu('H2O', 10000.0))
      5.32986401658495
    """
    _materials = get_materials(_larch)
    formula = None
    mater = _materials.get(name.lower(), None)
    if mater is not None:
        formula, density = mater
    else:
        for key, val in _materials.items():
            if name.lower() == val[0].lower(): # match formula
                formula, density = val
                break
    # default to using passed in name as a formula
    if formula is None:
        formula = name
    if density is None:
        raise Warning('material_mu(): must give density for unknown materials')

    mass_tot, mu = 0.0, 0.0
    for elem, frac in chemparse(formula).items():
        mass  = frac * atomic_mass(elem)
        mu   += mass * mu_elam(elem, energy, kind=kind)
        mass_tot += mass
    return density*mu/mass_tot


def material_mu_components(name, energy, density=None, kind='total', _larch=None):
    """material_mu_components: absorption coefficient (in 1/cm) for a compound

    arguments
    ---------
     name:     material name or compound formula
     energy:   energy or array of energies at which to calculate mu
     density:  compound density in gr/cm^3
     kind:     cross-section to use ('total', 'photo') for mu_elam())

    returns
    -------
     dictionary of data for constructing mu per element,
     with elements 'mass' (total mass), 'density', and
     'elements' (list of atomic symbols for elements in material).
     For each element, there will be an item (atomic symbol as key)
     with tuple of (stoichiometric fraction, atomic mass, mu)

     larch> material_mu_components('quartz', 10000)
     {'Si': (1, 28.0855, 33.879432430185062), 'elements': ['Si', 'O'],
     'mass': 60.0843, 'O': (2.0, 15.9994, 5.9528248152970837), 'density': 2.65}
     """
    _materials = get_materials(_larch)
    mater = _materials.get(name.lower(), None)
    if mater is None:
        formula = name
        if density is None:
            raise Warning('material_mu(): must give density for unknown materials')
    else:
        formula, density = mater


    out = {'mass': 0.0, 'density': density, 'elements':[]}
    for atom, frac in chemparse(formula).items():
        mass  = atomic_mass(atom)
        mu    = mu_elam(atom, energy, kind=kind)
        out['mass'] += frac*mass
        out[atom] = (frac, mass, mu)
        out['elements'].append(atom)
    return out

def material_get(name, _larch=None):
    """lookup material """
    return get_materials(_larch).get(name.lower(), None)


def material_add(name, formula, density, _larch=None):
    """ save material in local db"""
    global _materials
    if _materials is not None:
        _materials = get_materials()
    formula = formula.replace(' ', '')
    _materials[name.lower()] = (formula, float(density))

    if _larch is not None:
        symname = '%s._materials' % MODNAME
        _larch.symtable.set_symbol(symname, _materials)


    fname = os.path.join(site_config.usr_larchdir, 'materials.dat')
    if os.path.exists(fname):
        fh = open(fname, 'r')
        text = fh.readlines()
        fh.close()
    else:
        text = ['# user-specific database of materials\n',
                '# name, formula, density\n']

    text.append(" %s | %s | %g\n" % (name, formula, density))

    fh = open(fname, 'w')
    fh.write(''.join(text))
    fh.close()
