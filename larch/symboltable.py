#!/usr/bin/env python
'''
SymbolTable for Larch interpreter
'''
from __future__ import print_function
import os
import sys
import types
import numpy
import copy
from . import site_config
from .closure import Closure
from .utils import fixName, isValidName


class Group(object):
    """
    Generic Group: a container for variables, modules, and subgroups.
    """
    __private = ('_main', '_larch', '_parents', '__name__', '__doc__',
                 '__private', '_subgroups', '_members', '_repr_html_')

    def __init__(self, name=None, **kws):
        if name is None:
            name = hex(id(self))
        self.__name__ = name
        for key, val in kws.items():
            setattr(self, key, val)

    def __len__(self):
        return max(1, len(dir(self))-1)

    def __repr__(self):
        if self.__name__ is not None:
            return '<Group %s>' % self.__name__
        return '<Group>'

    def __copy__(self):
        out = Group()
        for k, v in self.__dict__.items():
            if k != '__name__':
                setattr(out, k,  copy.copy(v))
        return out

    def __deepcopy__(self, memo):
        out = Group()
        for k, v in self.__dict__.items():
            if k != '__name__':
                setattr(out, k,  copy.deepcopy(v, memo))
        return out

    def __id__(self):
        return id(self)

    def __dir__(self):
        "return list of member names"
        cls_members = []
        cname = self.__class__.__name__
        if cname != 'SymbolTable' and hasattr(self, '__class__'):
            cls_members = dir(self.__class__)

        dict_keys = [key for key in self.__dict__ if key not in cls_members]

        return [key for key in cls_members + dict_keys
                if (not key.startswith('_SymbolTable_') and
                    not key.startswith('_Group_') and
                    not key.startswith('_%s_' % cname) and
                    not (key.startswith('__') and key.endswith('__')) and
                    key not in self.__private)]

    def _subgroups(self):
        "return list of names of members that are sub groups"
        return [k for k in self._members() if isgroup(self.__dict__[k])]

    def _members(self):
        "return members"
        r = {}
        for key in self.__dir__():
            if key in self.__dict__:
                r[key] = self.__dict__[key]
        return r

    def _repr_html_(self):
        """HTML representation for Jupyter notebook"""

        html = [f"Group {self.__name__}"]
        html.append("<table>")
        html.append("<tr><td><b>Attribute</b></td><td><b>Type</b></td></tr>")
        attrs = self.__dir__()
        atypes = [type(getattr(self, attr)).__name__ for attr in attrs]
        html.append(''.join([f"<tr><td>{attr}</td><td><i>{atp}</i></td></tr>" for attr, atp in zip(attrs, atypes)]))
        html.append("</table>")
        return ''.join(html)


def isgroup(grp, *args):
    """tests if input is a Group

    With additional arguments (all must be strings), it also tests
    that the group has an an attribute named for each argument. This
    can be used to test not only if a object is a Group, but whether
    it a group with expected arguments.
    """
    ret = isinstance(grp, Group)
    if ret and len(args) > 0:
        try:
            ret = all([hasattr(grp, a) for a in args])
        except TypeError:
            return False
    return ret


class InvalidName:
    """ used to create a value that will NEVER be a useful symbol.
    symboltable._lookup() uses this to check for invalid names"""
    pass

GroupDocs = {}
GroupDocs['_sys'] = """
Larch system-wide status variables, including
configuration variables and lists of Groups used
for finding variables.
"""

GroupDocs['_builtin'] = """
core built-in functions, most taken from Python
"""

GroupDocs['_math'] = """
Mathematical functions, including a host of functtion from numpy and scipy
"""


class SymbolTable(Group):
    """Main Symbol Table for Larch.
    """
    top_group   = '_main'
    core_groups = ('_sys', '_builtin', '_math')
    __invalid_name = InvalidName()
    _private = ('save_frame', 'restore_frame', 'set_frame',
                'has_symbol', 'has_group', 'get_group',
                'create_group', 'new_group', 'isgroup',
                'get_symbol', 'set_symbol',  'del_symbol',
                'get_parent', 'add_plugin', '_path', '__parents')

    def __init__(self, larch=None):
        Group.__init__(self, name=self.top_group)
        self._larch = larch
        self._sys = None
        setattr(self, self.top_group, self)

        for gname in self.core_groups:
            thisgroup = Group(name=gname)
            if gname in GroupDocs:
                thisgroup.__doc__ = GroupDocs[gname]

            setattr(self, gname, thisgroup)

        self._sys.frames      = []
        self._sys.searchGroups = [self.top_group]
        self._sys.path        = ['.']
        self._sys.localGroup  = self
        self._sys.valid_commands = []
        self._sys.moduleGroup = self
        self._sys.__cache__  = [None]*4
        self._sys.saverestore_groups = []
        for g in self.core_groups:
            self._sys.searchGroups.append(g)
        self._sys.core_groups = tuple(self._sys.searchGroups[:])

        self.__callbacks = {}
        orig_sys_path = sys.path[:]

        if site_config.modules_path is not None:
            for idir in site_config.modules_path:
                idirfull = os.path.abspath(idir)
                if idirfull not in self._sys.path and os.path.exists(idirfull):
                    self._sys.path.append(idirfull)

        sys.path = self._sys.path[:]
        for idir in orig_sys_path:
            idirfull = os.path.abspath(idir)
            if idirfull not in sys.path:
                sys.path.append(idirfull)

        self._sys.modules = {'_main':self}
        for gname in self.core_groups:
            self._sys.modules[gname] = getattr(self, gname)
        self._fix_searchGroups()

        self._sys.config = Group(home_dir    = site_config.home_dir,
                                 history_file= site_config.history_file,
                                 init_files  = site_config.init_files,
                                 modules_path= site_config.modules_path,
                                 plugins_path= site_config.plugins_path,
                                 user_larchdir= site_config.usr_larchdir,
                                 larch_version= site_config.larch_version)

    def save_frame(self):
        " save current local/module group"
        self._sys.frames.append((self._sys.localGroup,
                                 self._sys.moduleGroup))

    def restore_frame(self):
        "restore last saved local/module group"
        try:
            lgrp, mgrp = self._sys.frames.pop()
            self._sys.localGroup = lgrp
            self._sys.moduleGroup  = mgrp
            self._fix_searchGroups()
        except:
            pass

    def set_frame(self, groups):
        "set current execution frame (localGroup, moduleGroup)"
        self._sys.localGroup, self._sys.moduleGroup  = groups
        self._fix_searchGroups()


    def _fix_searchGroups(self, force=False):
        """resolve list of groups to search for symbol names:

        The variable self._sys.searchGroups holds the list of group
        names for searching for symbol names.  A user can set this
        dynamically.  The names need to be absolute (that is, relative to
        _main, and can omit the _main prefix).

        This calclutes and returns self._sys.searchGroupObjects,
        which is the list of actual group objects (not names) resolved from
        the list of names in _sys.searchGroups)

        _sys.localGroup,_sys.moduleGroup come first in the search list,
        followed by any search path associated with that module (from
        imports for that module)
        """
        ##
        # check (and cache) whether searchGroups needs to be changed.
        sys = self._sys
        cache = sys.__cache__
        if len(cache) < 4:
            cache = [None]*4
        if (sys.localGroup   == cache[0] and
            sys.moduleGroup  == cache[1] and
            sys.searchGroups == cache[2] and
            cache[3] is not None and not force):
            return cache[3]

        if sys.moduleGroup is None:
            sys.moduleGroup = self.top_group
        if sys.localGroup is None:
            sys.localGroup = self.moduleGroup

        cache[0] = sys.localGroup
        cache[1] = sys.moduleGroup
        snames  = []
        sgroups = []
        for grp in (sys.localGroup, sys.moduleGroup):
            if grp is not None and grp not in sgroups:
                sgroups.append(grp)
                snames.append(grp.__name__)

        sysmods = list(self._sys.modules.values())
        searchGroups  = sys.searchGroups[:]
        searchGroups.extend(self._sys.core_groups)
        for name in searchGroups:
            grp = None
            if name in self._sys.modules:
                grp = self._sys.modules[name]
            elif hasattr(self, name):
                gtest = getattr(self, name)
                if isinstance(gtest, Group):
                    grp = gtest
            elif '.' in name:
                parent, child= name.split('.')
                for sgrp in sysmods:
                    if (parent == sgrp.__name__ and
                        hasattr(sgrp, child)):
                        grp = getattr(sgrp, child)
                        break
            else:
                for sgrp in sysmods:
                    if hasattr(sgrp, name):
                        grp = getattr(sgrp, name)
                        break
            if grp is not None and grp not in sgroups:
                sgroups.append(grp)
                snames.append(name)

        self._sys.searchGroups = cache[2] = snames[:]
        sys.searchGroupObjects = cache[3] = sgroups[:]
        return sys.searchGroupObjects

    def get_parentpath(self, sym):
        """ get parent path for a symbol"""
        obj = self._lookup(sym)
        if obj is None:
            return
        out = []
        for s in reversed(self.__parents):
            if s.__name__ != '_main' or '_main' not in out:
                out.append(s.__name__)
        out.reverse()
        return '.'.join(out)

    def _lookup(self, name=None, create=False):
        """looks up symbol in search path
        returns symbol given symbol name,
        creating symbol if needed (and create=True)"""
        debug = False # not ('force'in name)
        if debug:  print( '====\nLOOKUP ', name)
        searchGroups = self._fix_searchGroups()
        self.__parents = []
        if self not in searchGroups:
            searchGroups.append(self)

        def public_attr(grp, name):
            return (hasattr(grp, name)  and
                    not (grp is self and name in self._private))

        parts = name.split('.')
        if len(parts) == 1:
            for grp in searchGroups:
                if public_attr(grp, name):
                    self.__parents.append(grp)
                    return getattr(grp, name)

        # more complex case: not immediately found in Local or Module Group
        parts.reverse()
        top   = parts.pop()
        out   = self.__invalid_name
        if top == self.top_group:
            out = self
        else:
            for grp in searchGroups:
                if public_attr(grp, top):
                    self.__parents.append(grp)
                    out = getattr(grp, top)
        if out is self.__invalid_name:
            raise NameError("'%s' is not defined" % name)

        if len(parts) == 0:
            return out

        while parts:
            prt = parts.pop()
            if hasattr(out, prt):
                out = getattr(out, prt)
            elif create:
                val = None
                if len(parts) > 0:
                    val = Group(name=prt)
                setattr(out, prt, val)
                out = getattr(out, prt)
            else:
                raise LookupError(
                    "cannot locate member '%s' of '%s'" % (prt,out))
        return out

    def has_symbol(self, symname):
        try:
            g = self.get_symbol(symname)
            return True
        except (LookupError, NameError, ValueError):
            return False

    def has_group(self, gname):
        try:
            g = self.get_group(gname)
            return True
        except (NameError, LookupError):
            return False

    def isgroup(self, sym):
        "test if symbol is a group"
        return isgroup(sym)

    def get_group(self, gname):
        "find group by name"
        sym = self._lookup(gname, create=False)
        if isgroup(sym):
            return sym
        else:
            raise LookupError(
                "symbol '%s' found, but not a group" % (gname))

    def create_group(self, **kw):
        "create a new Group, not placed anywhere in symbol table"
        return Group(**kw)

    def new_group(self, name, **kws):
        name = fixName(name)
        grp = Group(__name__ = name, **kws)
        self.set_symbol(name, value=grp)
        return grp

    def get_symbol(self, sym, create=False):
        "lookup and return a symbol by name"
        return self._lookup(sym, create=create)

    def set_symbol(self, name, value=None, group=None):
        "set a symbol in the table"
        grp = self._sys.localGroup
        if group is not None:
            grp = self.get_group(group)
        names = []

        for n in name.split('.'):
            if not isValidName(n):
                raise SyntaxError("invalid symbol name '%s'" % n)
            names.append(n)

        child = names.pop()
        for nam in names:
            if hasattr(grp, nam):
                grp = getattr(grp, nam)
                if not isgroup(grp):
                    raise ValueError(
                "cannot create subgroup of non-group '%s'" % grp)
            else:
                setattr(grp, nam, Group())

        setattr(grp, child, value)
        if (grp, child) in self.__callbacks:
            for func, args, kws in self.__callbacks[(grp, child)]:
                kws.update({'group': grp, 'value': value,
                            'symbolname': child})
                func(*args, **kws)
        return getattr(grp, child)

    def del_symbol(self, name):
        "delete a symbol"
        sym = self._lookup(name, create=False)
        parent, child = self.get_parent(name)
        self.clear_callbacks(name)
        delattr(parent, child)

    def clear_callbacks(self, name, index=None):
        """clear 1 or all callbacks for a symbol
        """
        parent, child = self.get_parent(name)
        if child is not None and (parent, child) in self.__callbacks:
            if index is not None and index <= len(self.__callbacks[(parent, child)]):
                self.__callbacks[(parent, child)].pop(index)
            else:
                while self.__callbacks[(parent, child)]:
                    self.__callbacks[(parent, child)].pop()

    def add_callback(self, name, func, args=None, kws=None):
        """set a callback to be called when set_symbol() is called
        for a named variable
        """
        try:
            var = self.get_symbol(name)
        except NameError:
            raise NameError(
                "cannot locate symbol '%s' for callback" % (name))
        key = self.get_parent(name)
        if key not in self.__callbacks:
            self.__callbacks[key] = []
        if args is None: args = ()
        if kws is None: kws = {}

        self.__callbacks[key].append((func, args, kws))

    def get_parent(self, name):
        """return parent group, child name for an absolute symbol name
        (as from _lookup) that is, a pair suitable for hasattr,
        getattr, or delattr
        """
        tnam = name.split('.')
        if len(tnam) < 1 or name == self.top_group:
            return (self, None)
        child = tnam.pop()
        sym = self
        if len(tnam) > 0:
            sym = self._lookup('.'.join(tnam))
        return sym, child

    def add_plugin(self, plugin, on_error, **kws):
        """Add a plugin: a module that includes a
        registerLarchPlugin function that returns
        larch_group_name, dict_of_symbol/functions
        """
        if not isinstance(plugin, types.ModuleType):
            on_error("%s is not a valid larch plugin" % repr(plugin))

        group_registrar = getattr(plugin, 'registerLarchGroups', None)
        if callable(group_registrar):
            savegroups = group_registrar()
            for group in savegroups:
                self._sys.saverestore_groups.append(group)

        registrar = getattr(plugin, 'registerLarchPlugin', None)
        if registrar is None:
            return

        groupname, syms = registrar()
        if not isinstance(syms, dict):
            raise ValueError('add_plugin requires dictionary of plugins')

        if not self.has_group(groupname):
            self.new_group(groupname)

        if groupname not in self._sys.searchGroups:
            self._sys.searchGroups.append(groupname)
        self._fix_searchGroups(force=True)

        for key, val in syms.items():
            if hasattr(val, '__call__') and hasattr(val, '__code__'): # is a function
                # test whether plugin func has a '_larch' kw arg
                #    __code__.co_flags & 8 == 'uses **kws'
                kws.update({'func': val, '_name':key})
                try:
                    nvars = val.__code__.co_argcount
                    if ((val.__code__.co_flags &8 != 0) or
                        '_larch' in val.__code__.co_varnames[:nvars]):
                        kws.update({'_larch':  self._larch})
                    val = Closure(**kws)
                except AttributeError: # cannot make a closure
                    pass
            self.set_symbol("%s.%s" % (groupname, key), val)

        plugin_init = getattr(plugin, 'initializeLarchPlugin', None)
        if plugin_init is not None:
            plugin_init(_larch=self._larch)
        return (groupname, syms)

    def show_group(self, groupname):
        """display group members --- simple version for tests"""
        out = []
        try:
            group = self.get_group(groupname)
        except (NameError, LookupError):
            return 'Group %s not found' % groupname

        title = group.__name__
        members = dir(group)
        out = ['== %s: %i symbols ==' % (title, len(members))]
        for item in members:
            obj = getattr(group, item)
            dval = None
            if isinstance(obj, numpy.ndarray):
                if len(obj) > 10 or len(obj.shape)>1:
                    dval = "array<shape=%s, type=%s>" % (repr(obj.shape),
                                                         repr(obj.dtype))
            if dval is None:
                dval = repr(obj)
            out.append('  %s: %s' % (item, dval))
        self._larch.writer.write("%s\n" % '\n'.join(out))
