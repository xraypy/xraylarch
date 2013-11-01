import os
import numpy as np
import larch
larch.use_plugin_path('xray')
from chemparser import chemparse

MODNAME = '_xray'

def get_materials(_larch):
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

def lookup_material(name, _larch=None):
    """lookup material """
    if _larch is None:
        return
    return get_materials(_larch).get(name.lower(), None)

def save_material(name, formula, density, _larch=None):
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
    return ('_xray', {'lookup_material': lookup_material,
                      'save_material': save_material,
                      })
