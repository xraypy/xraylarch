'''SymbolTable for Larch interpreter
'''

from __future__ import print_function
import os
import sys
import types
from .closure import Closure
from . import site_config
try:
    import numpy
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def isgroup(grp):
    "tests if input is a Group"
    return isinstance(grp, Group)

class Group(object):
    """Group: a container for variables, modules, and subgroups.

    Methods
    ----------
       _subgroups(): return sorted list of subgroups
       _members():   return sorted list of all members
       _publicmembers():   return sorted list of 'public' members

    """
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
        return (id(self))

    def __setattr__(self, attr, val):
        """set group attributes."""
        self.__dict__[attr] = val

    def __dir__(self):
        "return sorted list of names of member"
        return sorted([key for key in list(self.__dict__.keys())
                       if (not key.startswith('_Group__') and
                           not key.startswith('_SymbolTable__') and
                           not key == '_main' and                           
                           not key == '__name__')])
   
    def _subgroups(self):
        "return sorted list of names of members that are sub groups"
        return sorted([k for k, v in list(self.__dict__.items())
                       if isgroup(v)])
    
    def _members(self):
        "sorted member list"
        return sorted(list(self.__dict__.keys()))

    def _publicmembers(self):
        "sorted member list"
        r = {}
        for key in self._members():
            if not (key.startswith('_Group__') or
                    key.startswith('_SymbolTable__') or
                    key == '_main' or key == '__name__'):
                r[key] = self.__dict__[key]
        return r

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

    def __init__(self, larch=None):
        Group.__init__(self, name=self.top_group)
        # self.__writer = writer  or sys.stdout.write
        self.__interpreter = larch
        self._sys = None
        setattr(self, self.top_group, self)
        
        for gname in self.core_groups:
            setattr(self, gname, Group(name=gname))

        self._sys.frames = []
        self._sys.searchNames  = []
        self._sys.searchGroups = []
        self._sys.localGroup   = self
        self._sys.moduleGroup  = self
        self._sys.groupCache  = {'localGroup':None, 'moduleGroup':None,
                                 'searchNames':None, 'searchGroups': None}

        self._sys.path         = ['.']
        
        if site_config.module_path is not None:
            for idir in site_config.module_path:
                if idir not in self._sys.path and os.path.exists(idir):
                    self._sys.path.append(idir)

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
        "set current frame (localGroup, moduleGroup)"
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

        #  print('FIX SG1 ', sys.localGroup   == cache['localGroup'],
        #         sys.moduleGroup  == cache['moduleGroup'],
        #         sys.searchGroups == cache['searchNames'])

        if (sys.localGroup   != cache['localGroup'] or
            sys.moduleGroup  != cache['moduleGroup'] or
            sys.searchGroups != cache['searchNames']):

            # print('FIX SG2 ', sys.localGroup,
            # sys.moduleGroup,
            #       sys.searchGroups, cache['searchNames'])
            
            if sys.moduleGroup is None:
                sys.moduleGroup = self.top_group
            if sys.localGroup is None:
                sys.localGroup = self.moduleGroup

            cache['localGroup']  = sys.localGroup 
            cache['moduleGroup'] = sys.moduleGroup

            if cache['searchNames'] is None:
                cache['searchNames'] = []

            for gname in sys.searchGroups:
                if gname not in cache['searchNames']:
                    cache['searchNames'].append(gname)
            for gname in self.core_groups:
                if gname not in cache['searchNames']:
                    cache['searchNames'].append(gname)                    

            sys.searchGroups = cache['searchNames'][:]
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
                        
            cache['searchGroups'] = sgroups[:]
        return cache

    def list_groups(self, group=None):
        "list groups"
        if group in (self.top_group, None):
            grp = self
            group = 'SymbolTable'
        elif hasattr(self, group):
            grp = getattr(self, group)
        else:
            grp = None
            msg = '%s not found' % group
            
        if isgroup(grp):
            names = dir(grp)
            out = ['== %s ==' % group]
            for item in names:
                if not (item.startswith('_Group__') or
                        item.startswith('_SymbolTable__')):
                    out.append('  %s: %s' % (item, repr(getattr(grp, item))))
            msg = '\n'.join(out)
        else:
            msg = '%s is not a Subgroup' % group
        return "%s\n" % msg  ### self.__writer("%s\n" % msg)
    
    def _lookup(self, name=None, create=False):
        """looks up symbol in search path
        returns symbol given symbol name,
        creating symbol if needed (and create=True)"""

        cache = self._fix_searchGroups()

        searchGroups = [cache['localGroup'], cache['moduleGroup']]
        searchGroups.extend(cache['searchGroups'])

        if self not in searchGroups:
            searchGroups.append(self)

        parts = name.split('.')
        if len(parts) == 1:
            for grp in searchGroups:
                if hasattr(grp, name):
                    return getattr(grp, name)

        # more complex case: not immediately found in Local or Module Group

        parts.reverse()
        top   = parts.pop()
        out   = self.__invalid_name
        if top == self.top_group:
            out = self
        else:
            for grp in searchGroups:
                if hasattr(grp, top):
                    out = getattr(grp, top)

        if out is self.__invalid_name:
            raise LookupError("cannot locate symbol '%s'" % name)

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
        except ValueError, LookupError:
            return False

    def has_group(self, gname):
        try:
            g = self.get_group(gname)
            return True
        except LookupError:
            return False

    def get_group(self, gname):
        "find group by name"
        sym = self._lookup(gname, create=False)
        if isgroup(sym):
            return sym
        else:
            raise LookupError(
                "symbol '%s' found, but not a group" % (gname))

    def show_group(self, gname=None):
        "show groups"

        if gname is None:
            gname = '_main'
        if isgroup(gname): 
            grp = gname
            title = repr(grp)[1:-1]
        elif isinstance(gname, types.ModuleType):
            grp = gname
            title = gname.__name__
        else:
            grp = self._lookup(gname, create=False)
            title = gname
            
        if title.startswith(self.top_group):
            title = title[6:]

        if grp == self:
            title = 'SymbolTable _main'

        mem = dir(grp)
        out = ['== %s: %i symbols ==' % (title, len(mem))]
        for item in mem:
            if not (item.startswith('_Group__') or
                    item == '__name__' or
                    item.startswith('_SymbolTable__')):
                out.append('  %s: %s' % (item, repr(getattr(grp, item))))
        msg = '\n'.join(out)
        return "%s\n" % msg  

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
        names = name.split('.')
        child = names.pop()
        for nam in names:
            if hasattr(grp, nam):
                grp = getattr(grp, nam)
                if not isgroup(grp):
                    raise ValueError(
                "cannot create subgroup of non-group '%s'" % grp)
            else:
                setattr(grp, nam, Group())
        if HAS_NUMPY and isinstance(value, list):
            try:
                v1 = numpy.array(value)
                value = v1
            except:
                pass

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

    def AddPlugins(self, plugins, **kw):
        """Add a list of plugins"""
        for plugin in plugins:
            groupname, insearchGroup, syms = plugin()
            sym = None
            try:
                sym = self._lookup(groupname, create=False)
            except LookupError:
                pass
            if sym is None:
                self.new_group(groupname)

            # print("Add Plugin! ", groupname, insearchGroup, syms)
            if insearchGroup:
                self._sys.searchGroups.append(groupname)
                self._fix_searchGroups()

            for key, val in syms.items():
                if callable(val):
                    val = Closure(func=val, **kw)
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
