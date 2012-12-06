import numpy as np
import json
import h5py
from larch import Group,  Parameter, isParameter, param_value

class H5PySaveFile(object):
    def __init__(self, fname, _larch=None):
        self.fname = fname
        self._larch = _larch
        self.symtable = _larch.symtable
        self.isgroup =  _larch.symtable.isgroup
        self._searched = []
        self._subgroups = []
        self._ids = []
        self.out = {}

    def search(self, group):
        """search for objects to save,
        populating self.out
        """
        for nam in dir(group):
            obj = getattr(group, nam)
            if (id(obj) in self._ids and
                obj not in self.out.values()):
                self.out[nam] = obj
            if len(self.out) == len(self._ids):
                return
            if (self.isgroup(obj) and
                obj not in self._searched and
                obj not in self._subgroups):
                self._subgroups.append(obj)
        if group in self._subgroups:
            self._subgroups.pop(group)
        for group in self._subgroups:
            self.searchgroup(group)


    def add_h5group(self, group, name, dat=None, attrs=None):
        """add an hdf5 group to group"""
        g = group.create_group(name)
        if isinstance(dat, dict):
            for key, val in dat.items():
                g[key] = val
        if isinstance(attrs, dict):
            for key, val in attrs.items():
                g.attrs[key] = val
        return g

    def add_h5dataset(self, group, name, data, attrs=None, **kws):
        """creata an hdf5 dataset"""
        kwargs = {}
        if isinstance(data, np.ndarray):
            kwargs = {'compression':4}
        kwargs.update(kws)
        try:
            d = group.create_dataset(name, data=data, **kwargs)
        except TypeError:
            d = group.create_dataset(name, data=repr(data), **kwargs)
        if isinstance(attrs, dict):
            for key, val in attrs.items():
                d.attrs[key] = val
        return d

    def add_data(self, group, name, data):
        if self.isgroup(data):
            g = self.add_h5group(group, name, attrs={'larchtype': 'Group'})
            for comp in dir(data):
                self.add_data(g, comp, getattr(data, comp))
        elif isinstance(data, (list, tuple)):
            dtype = 'list'
            if isinstance(data, tuple): dtype = 'tuple'
            g = self.add_h5group(group, name, attrs={'larchtype': dtype})
            for ix, comp in enumerate(data):
                iname = 'item%i' % ix
                self.add_data(g, iname, comp)
        elif isinstance(data, dict):
            g = self.add_h5group(group, name, attrs={'larchtype': 'dict'})
            for key, val in data.items():
                self.add_data(g, key, val)
        elif isParameter(data):
            d = self.add_h5dataset(group, name, data=data.asjson())
            d.attrs['larchtype'] = 'parameter'
        else:
            d = self.add_h5dataset(group, name, data)

    def save(self, *args):
        self._ids = [id(a) for a in args]
        self.search(self.symtable)
        self.fh = h5py.File(self.fname, 'a')
        self.fh.attrs['datatype'] = 'LarchSaveFile'
        self.fh.attrs['version'] = '1.0.0'
        for t in self._ids:
            for nam, obj in self.out.items():
                if t == id(obj):
                    self.add_data(self.fh, nam, obj)
        self.fh.close()

def save(fname,  *args, **kws):
    _larch = kws.get('_larch', None)
    symtable = _larch.symtable
    saver = H5PySaveFile(fname, _larch=_larch)
    saver.save(*args)

def restore(fname,  _larch=None):
    if _larch is None:
        print 'larch broken'
        return
    symtable = _larch.symtable
    saver = H5PySaveFile(fname, _larch=_larch)
    print 'restore not yet implemented....'
    # saver.restore()

def registerLarchPlugin():
    return ('_io', {'save': save, 'restore': restore})

