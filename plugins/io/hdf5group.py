import h5py

MODNAME = '_io'

def h5group(fname, larch=None):
    fh = h5py.File(fname, 'r')
    components = []
    fh.visit(components.append)
    group = larch.symtable.create_group()
    for comp in components:
        setattr(group, comp, fh.get(comp).value)
    return group

def registerLarchPlugin():
    return (MODNAME, {'h5group': h5group})


