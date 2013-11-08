import os
import numpy as np
import larch
larch.use_plugin_path('xray')
from xraydb_plugin import mu_elam, atomic_mass

from chemparser import chemparse
from physical_constants import AMU, BARN
AMUBARN = AMU*BARN
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

def material_mu(name, energy, kind='total', _larch=None):
    """
    return X-ray attenuation (in 1/cm) for a material by name

    arguments
    ---------
     name:    name of material, known from materials list
     energy:  energy or array of energies in eV
     kind:    'photo' or 'total' (default) for whether to
              return photo-absorption or total cross-section.

     Data from Elam, Ravel, and Sieber.
    """
    if _larch is None:
        return

    _materials = get_materials(_larch)
    mater = _materials.get(name.lower(), None)
    if mater is None:
        for key, val in _materials.items():
            if val[0].lower() == name.lower():
                mater = _materials[key]
                break
    if mater is None:
        _larch.writer.write("Material '%s' is not known\n" % name)
    density = mater[1]
    formula = chemparse(mater[0])
    wt_tot, mu_tot = 0.0, 0.0
    for elem, weight in formula.items():
        mu = mu_elam(elem, energy, kind=kind, _larch=_larch)
        wt = AMUBARN * weight * atomic_mass(elem, _larch=_larch)
        mu_tot += mu * wt
        wt_tot += wt
    return density*mu_tot/wt_tot

def material_get(name, _larch=None):
    """lookup material """
    if _larch is None:
        return
    return get_materials(_larch).get(name.lower(), None)

def material_save(name, formula, density, _larch=None):
    """ save material in personal db"""
    if _larch is None:
        return
    materials = get_materials(_larch)
    formula = formula.replace(' ', '')
    materials[name.lower()] = (formula, float(density))
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
                      'material_save': material_save,
                      'material_mu': material_mu,
                      })
