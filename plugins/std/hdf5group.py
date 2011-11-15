import h5py

MODNAME = '_io'

def h5group(fname, larch=None):
    fh = h5py.File(fname, 'r')
    components = []
    new_group = larch.symtable.create_group
    fh.visit(components.append)
    topgroup = new_group()
    groupmap = {'root': topgroup}
    
    for cname in components:
        val = fh.get(cname)
        if isinstance(val, h5py.Group):
            print 'Group: ', cname
            groupmap[cname] = new_group()
            setattr(topgroup, cname, groupmap[cname])
        else:
            print 'MM ', cname # setattr(group, cname, fh.get(comp))
    return topgroup

def registerLarchPlugin():
    return (MODNAME, {'h5group': h5group})


