import os
import numpy as np
import larch
larch.use_plugin_path('xray')
from xraydb_plugin import mu_elam, atomic_mass

from chemparser import chemparse
MODNAME = '_xray'

def get_materials(_larch):
    """return _materials dictionary, creating it if needed"""
    symname = '%s._materials' % MODNAME
    if _larch.symtable.has_symbol(symname):
        return _larch.symtable.get_symbol(symname)
    mat = {}
    conf = larch.site_config
    paths = [os.path.join(conf.sys_larchdir, 'plugins', 'xray'),
             os.path.join(conf.usr_larchdir)]

    for dirname in paths:
        fname = os.path.join(dirname, 'materials.dat')
        if os.path.exists(fname):
            fh = open(fname, 'r')
            lines = fh.readlines()
            fh.close()
            for line in lines:
                line = line.strip()
                if len(line) > 2 and not line.startswith('#'):
                    try:
                        name, f, den = [i.strip() for i in line.split('|')]
                        mat[name.lower()] = (f.replace(' ', ''), float(den))
                    except:
                        pass
    _larch.symtable.set_symbol(symname, mat)
    return mat

def material_mu(name, energy, density=None, kind='total', _larch=None):
    """
    return X-ray attenuation length (in 1/cm) for a material by name or formula

    arguments
    ---------
     name:     name of material  from materials list or chemical compound
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
      >>> print material_mu('H2O', 1.0, 10000.0)
      5.32986401658495
    """
    if _larch is None:
        return

    _materials = get_materials(_larch)
    mater = _materials.get(name.lower(), None)
    if mater is None:
        if density is None:
            density = 1.0
        formula = name
    else:
        formula, density = mater

    msum, mu = 0.0, 0.0
    for elem, weight in chemparse(formula).items():
        mass  = weight * atomic_mass(elem, _larch=_larch)
        msum += mass
        mu   += mass * mu_elam(elem, energy, kind=kind, _larch=_larch)
    return density*mu/msum

def material_mu_components(name, energy, density=None, kind='total',
                           _larch=None):
   """material_mu_components: absorption coefficient (in 1/cm) for a compound

   arguments
   ---------
    name:     material name or compound formula
    energy:   energy or array of energies at which to calculate mu
    density:  compound density in gr/cm^3
    kind:     cross-section to use ('total', 'photo') for mu_elam())

   returns
   -------
     dictionary of component of mu per element,

   >>> print mu_compound('H2O', 1.0, 10000.0)
   5.32986401658495
   """
   mtot, mu = 0.0, 0.0
   out = {}
   for atom, num in chemparse(formula).items():
       atmass = atomic_mass(atom, _larch=_larch)
       mu     = mu_elam(atom, energies, kind=kind, _larch=_larch)
       out[atom] = (num, atmass, mu)
       mass  = atmass * num
       mu   += mass*mu
       mtot += mass
   out['mass'] = mtot
   out['density'] = density
   return out

def material_get(name, _larch=None):
    """lookup material """
    if _larch is None:
        return
    return get_materials(_larch).get(name.lower(), None)

def material_add(name, formula, density, _larch=None):
    """ save material in personal db"""
    if _larch is None:
        return
    materials = get_materials(_larch)
    formula = formula.replace(' ', '')
    materials[name.lower()] = (formula, float(density))

    symname = '%s._materials' % MODNAME
    _larch.symtable.set_symbol(symname, materials)

    fname = os.path.join(larch.site_config.usr_larchdir, 'materials.dat')
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

def initializeLarchPlugin(_larch=None):
    """initialize xraydb"""
    if _larch is not None:
         get_materials(_larch)

def registerLarchPlugin():
    return ('_xray', {'material_get': material_get,
                      'material_add': material_add,
                      'material_mu':  material_mu,
                      })
