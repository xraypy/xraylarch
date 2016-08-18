import json
import numpy as np
import h5py
from larch import Group, Parameter, isParameter
from larch import ValidateLarchPlugin
from larch.utils import fixName
from larch_plugins.io import fix_varname


class H5PySaveFile(object):
    def __init__(self, fname, _larch=None):
        self.fname = fname
        self._larch = _larch
        self.symtable = _larch.symtable
        self.isgroup =  _larch.symtable.isgroup
        self._searched = []
        self._subgroups = []
        self._ids  = []
        self._objs = []
        self.out = {}
        self.savednames = []

    def search(self, group):
        """search for objects to save,
        populating self.out
        """
        if len(self._ids) == 0:
            return

        for nam in dir(group):
            self._searched.append(group)
            obj = getattr(group, nam)
            if (id(obj) in self._ids and
                obj not in self.out.values()):
                self.out[nam] = obj
                self._ids.remove(id(obj))
                self._objs.remove(obj)
            if (self.isgroup(obj) and
                obj not in self._searched and
                obj not in self._subgroups):
                self._subgroups.append(obj)
        if group in self._subgroups:
            self._subgroups.remove(group)
        for group in self._subgroups:
            self.search(group)

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
        try:
            d = group.create_dataset(name, data=data, **kws)
        except TypeError:
            d = group.create_dataset(name, data=repr(data), **kws)
        if isinstance(attrs, dict):
            for key, val in attrs.items():
                d.attrs[key] = val
        return d

    def add_data(self, group, name, data):
        name = fix_varname(name)
        if self.isgroup(data):
            g = self.add_h5group(group, name,
                                 attrs={'larchtype': 'group',
                                        'class': data.__class__.__name__})
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
            g = self.add_h5group(group, name, attrs={'larchtype': 'parameter'})
            self.add_h5dataset(g, 'json', data.asjson())
        else:
            d = self.add_h5dataset(group, name, data)

    def save(self, *args):
        self._ids  = [id(a) for a in args]
        self._objs = list(args)
        self.search(self.symtable)
        self.fh = h5py.File(self.fname, 'a')
        try:
            self.fh.attrs['datatype'] = 'LarchSaveFile'
            self.fh.attrs['version'] = '1.0.0'
        except:
            pass
        for nam, obj in self.out.items():
            onam = getattr(obj, '__name__', None)
            if onam is not None:
                nam = onam
            self.add_data(self.fh, nam, obj)

        for obj in self._objs:
            nam = getattr(obj, '__name__', hex(id(obj)))
            if nam.startswith('0x'):
                nam = 'obj_%s' % nam[2:]
            self.add_data(self.fh, nam, obj)

        self.fh.close()

@ValidateLarchPlugin
def save(fname,  *args, **kws):
    """save groups and data into a portable, hdf5 file

    save(fname, arg1, arg2, ....)

    Parameters
    ----------
       fname   name of output save file.
       args    list of groups, data items to be saved.

   See Also:  restore()
    """
    _larch = kws.get('_larch', None)

    saver = H5PySaveFile(fname, _larch=_larch)
    saver.save(*args)

@ValidateLarchPlugin
def restore(fname,  group=None, _larch=None):
    """restore groups and data from an hdf5 Larch Save file

    restore(fname, group=None)

    Parameters
    ----------
       fname   name of output Larch save file (required)
       group   top-level group to put data in [None]

   Returns
   -------
       top-level grouop containing restored subgroups and data.

   If group is None, a group will be created and returned.

   See Also:  save()
   """
    symtable = _larch.symtable
    msg  = _larch.writer.write
    fh = h5py.File(fname, 'r')

    if fh.attrs.get('datatype', None) != 'LarchSaveFile':
        msg("File  '%s' is not a valid larch save file\n" % fname)
        return
    create_group = _larch.symtable.create_group

    from larch_plugins.xafs import (FeffPathGroup, FeffDatFile,
                                    FeffitDataSet, TransformGroup)

    def make_group(h5group):
        creators = {'TransformGroup': TransformGroup,
                    'FeffDatFile':    FeffDatFile,
                    'FeffitDataSet':  FeffitDataSet,
                    'FeffPathGroup':  FeffPathGroup}
        gtype = h5group.attrs.get('class', None)
        return creators.get(gtype, create_group)(_larch=_larch)

    def get_component(val):
        if isinstance(val, h5py.Group):
            ltype = val.attrs.get('larchtype', None)
            if ltype == 'group':
                me = make_group(val)
                for skey, sval in val.items():
                    setattr(me, skey, get_component(sval))
                return me
            elif ltype == 'parameter':
                kws = json.loads(val['json'].value)
                if kws['expr'] is not None:
                    kws.pop('val')
                kws['_larch'] = _larch
                return Parameter(**kws)
            elif ltype in ('list', 'tuple'):
                me = []
                for skey, sval in  val.items():
                    me.append(get_component(sval))
                if ltype == 'tuple':
                    me = tuple(me)
                return me
            elif ltype == 'dict':
                me = {}
                for skey, sval in  val.items():
                    me[skey] = get_component(sval)
                return me
        elif isinstance(val, h5py.Dataset):
            return val.value

    # walk through items in hdf5 save file
    if group is None:
        group = create_group()
    for  key, val in fh.items():
        setattr(group, key, get_component(val))
    fh.close()
    return group

def registerLarchPlugin():
    return ('_io', {'save': save, 'restore': restore})
