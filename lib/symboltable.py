'''
SymbolTable for Larch interpreter
'''
from __future__ import print_function
import os
import sys
import types
from .utils import Closure, fixName, isValidName
from . import site_config

class Group(object):
    """Group: a container for variables, modules, and subgroups.

    Methods
    ----------
       _subgroups(): return list of subgroups
       _members():   return dict of members
    """
    __private = ('_main', '_larch', '_parents', '__name__', '__private')
    def __init__(self, name=None, **kws):
        self.__name__ = name
        for key, val in kws.items():
            setattr(self, key, val)

    def __len__(self):
        return max(1, len(dir(self))-1)

    def __repr__(self):
        if self.__name__ is not None:
            return '<Group %s>' % self.__name__
        return '<Group>'

    def __id__(self):
        return id(self)

    def __setattr__(self, attr, val):
        """set group attributes."""
        self.__dict__[attr] = val

    def __dir__(self):
        "return list of member names"
        return [key for key in list(self.__dict__.keys())
                if (not key.startswith('_SymbolTable_') and
                    key not in self.__private)]

    def _subgroups(self):
        "return list of names of members that are sub groups"
        return [k for k in dir(self) if isgroup(self.__dict__[k])]

    def _members(self):
        "return members"
        r = {}
        for key in self.__dir__():
            r[key] = self.__dict__[key]
        return r

def isgroup(grp):
    "tests if input is a Group"
    return isinstance(grp, Group)

class InvalidName:
    """ used to create a value that will NEVER be a useful symbol.
    symboltable._lookup() uses this to check for invalid names"""
    pass

class SymbolTable(Group):
    """Main Symbol Table for Larch.
    """
    top_group   = '_main'
    core_groups = ('_sys', '_builtin', '_math')
    __invalid_name = InvalidName()
    _private = ('save_frame', 'restore_frame', 'set_frame',
                'has_symbol', 'has_group', 'get_group',
                'create_group', 'new_group',
                'get_symbol', 'set_symbol',  'del_symbol',
                'get_parent', 'add_plugin', 'path', '__parents')

    def __init__(self, larch=None):
        Group.__init__(self, name=self.top_group)
        # self.__writer = writer  or sys.stdout.write
        self._larch = larch
        self._sys = None
        setattr(self, self.top_group, self)

        for gname in self.core_groups:
            setattr(self, gname, Group(name=gname))

        self._sys.frames      = []
        self._sys.searchGroups = []
        self._sys.path        = ['.']
        self._sys.localGroup  = self
        self._sys.moduleGroup = self
        self._sys.groupCache  = {'localGroup':None, 'moduleGroup':None,
                                 'searchGroups':None, 'searchGroupObjects': None}

        self._sys.historyfile = site_config.history_file
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

        self._sys.modules      = {'_main':self}
        for gname in self.core_groups:
            self._sys.modules[gname] = getattr(self, gname)
        self._fix_searchGroups()

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

    def _fix_searchGroups(self):
        """resolve list of groups to search for symbol names:

        The variable self._sys.searchGroups holds the list of group
        names for searching for symbol names.  A user can set this
        dynamically.  The names need to be absolute (relative to
        _main).

        The variable self._sys.groupCache['searchGroups'] holds the list of
        actual group objects resolved from this name.

        _sys.localGroup,_sys.moduleGroup come first in the search list,
        followed by any search path associated with that module (from
        imports for that module)
        """
        ##
        # check (and cache) whether searchGroups needs to be changed.
        sys = self._sys
        cache = self._sys.groupCache
        if (sys.localGroup   != cache['localGroup'] or
            sys.moduleGroup  != cache['moduleGroup'] or
            sys.searchGroups != cache['searchGroups']):

            if sys.moduleGroup is None:
                sys.moduleGroup = self.top_group
            if sys.localGroup is None:
                sys.localGroup = self.moduleGroup

            cache['localGroup']  = sys.localGroup
            cache['moduleGroup'] = sys.moduleGroup

            if cache['searchGroups'] is None:
                cache['searchGroups'] = []

            for gname in sys.searchGroups:
                if gname not in cache['searchGroups']:
                    cache['searchGroups'].append(gname)
            for gname in self.core_groups:
                if gname not in cache['searchGroups']:
                    cache['searchGroups'].append(gname)

            sys.searchGroups = cache['searchGroups'][:]
            #
            sgroups = []
            smod_keys = list(self._sys.modules.keys())
            smod_vals = list(self._sys.modules.values())
            for gname in sys.searchGroups:
                grp = None
                if gname in smod_keys:
                    grp = self._sys.modules[gname]
                elif hasattr(self, gname):
                    gtest = getattr(self, gname)
                    if isinstance(gtest, Group):
                        grp = gtest
                else:
                    for sgrp in smod_vals:
                        if hasattr(sgrp, gname):
                            grp = getattr(grp, gname)
                if grp is not None and grp not in sgroups:
                    sgroups.append(grp)

            cache['searchGroupObjects'] = sgroups[:]
        return cache

    def get_parentpath(self, sym):
        """ get parent path for a symbol"""
        obj = self._lookup(sym)
        if obj is None:
            return
        out = []
        for s in reversed(self.__parents):
            if s.__name__ is not '_main' or '_main' not in out:
                out.append(s.__name__)
        out.reverse()
        return '.'.join(out)

    def _lookup(self, name=None, create=False):
        """looks up symbol in search path
        returns symbol given symbol name,
        creating symbol if needed (and create=True)"""
        cache = self._fix_searchGroups()
        searchGroups = [cache['localGroup'], cache['moduleGroup']]
        searchGroups.extend(cache['searchGroupObjects'])
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

    def new_group(self, name, **kw):
        g = Group(__name__ = name, **kw)
        self.set_symbol(name, value=g)
        return g

    def get_symbol(self, sym, create=False):
        "lookup and return a symbol by name"
        return self._lookup(sym, create=create)

    def set_symbol(self, name, value=None, group=None):
        "set a symbol in the table"
        grp = self._fix_searchGroups()['localGroup']
        if group is not None:
            grp = self.get_group(group)
        names = []
        for n in name.split('.'):
            if not isValidName(n):
                raise SyntaxError("invalid symbol name '%s'" %s)
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
        return getattr(grp, child)

    def del_symbol(self, name):
        "delete a symbol"
        sym = self._lookup(name, create=False)
        parent, child = self.get_parent(name)
        if isgroup(sym):
            raise LookupError("symbol '%s' is a group" % (name))
        parent, child = self.get_parent(name)
        if child is not None:
            delattr(parent, child)

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

    def add_plugin(self, plugin, **kws):
        """Add a plugin: a module that includes a
        registerLarchPlugin function that returns
        larch_group_name, dict_of_symbol/functions
        """
        if not isinstance(plugin, types.ModuleType):
            raise Warning(" %s is not a valid larch plugin" % repr(plugin))

        registrar = getattr(plugin, 'registerLarchPlugin', None)
        if registrar is None:
            raise Warning(" %s has no registerLarchPlugin method" %
                          plugin.__name__)

        groupname, syms = registrar()
        if not self.has_group(groupname):
            self.new_group(groupname)

        self._sys.searchGroups.append(groupname)
        self._fix_searchGroups()

        for key, val in syms.items():
            if hasattr(val, '__call__'):
                # test whether plugin func has a '_larch' kw arg
                #    func_code.co_flags & 8 == 'uses **kws'
                nvars = val.func_code.co_argcount
                if ((val.func_code.co_flags &8 != 0) or
                    '_larch' in val.func_code.co_varnames[:nvars]):
                    val = Closure(func=val, _larch=self._larch, _name=key, **kws)
                else:
                    val = Closure(func=val, _name=key, **kws)

            self.set_symbol("%s.%s" % (groupname, key), val)

# if __name__ == '__main__':
#     symtab = SymbolTable()
#     symtab.group1 = Group(name='group1')
#     symtab.group2 = Group(name='group2')
#
#     symtab.show_group('_sys')
#     symtab.group1.x = 12.0
#     symtab.group1.g1 = Group('g1')
#
#     symtab.show_group('group1')
#     symtab.group1.g1.title = 'a string here'
#     symtab.group1.g1.x = 99120.102
#     symtab.group1.g1.e = 8980.0
#
#     symtab.show_group('group1.g1')
#     symtab.list_groups()
#
#     print('group1 members , subgroups: ', dir(symtab.group1),
#           symtab.group1._subgroups())
