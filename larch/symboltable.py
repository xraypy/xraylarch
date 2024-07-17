#!/usr/bin/env python
'''
SymbolTable for Larch interpreter
'''
import copy
import numpy
from lmfit.printfuncs import gformat
from . import site_config
from .utils import fixName, isValidName

def repr_value(val):
    """render a repr-like value for ndarrays, lists, etc"""
    if (isinstance(val, numpy.ndarray) and
            (len(val) > 6 or len(val.shape)>1)):
        sval = f"shape={val.shape}, type={val.dtype} range=[{gformat(val.min())}:{gformat(val.max())}]"
    elif isinstance(val, list) and len(val) > 6:
        sval = f"length={len(val)}: [{val[0]}, {val[1]}, ... {val[-2]}, {val[-1]}]"
    elif isinstance(val, tuple) and len(val) > 6:
        sval = f"length={len(val)}: ({val[0]}, {val[1]}, ... {val[-2]}, {val[-1]})"
    else:
        try:
            sval = repr(val)
        except:
            sval = val
    return sval


class Group():
    """
    Generic Group: a container for variables, modules, and subgroups.
    """
    __private = ('_main', '_larch', '_parents', '__name__', '__doc__',
                 '__private', '_subgroups', '_members', '_repr_html_')

    __generic_functions = ('keys', 'values', 'items')

    def __init__(self, name=None, **kws):
        if name is None:
            name = hex(id(self))
        self.__name__ = name
        for key, val in kws.items():
            setattr(self, key, val)

    def __len__(self):
        return len(dir(self))

    def __repr__(self):
        if self.__name__ is not None:
            return f'<Group {self.__name__}>'
        return '<Group>'

    def __copy__(self):
        out = Group()
        for key, val in self.__dict__.items():
            if key != '__name__':
                setattr(out, key,  copy.copy(val))
        return out

    def __deepcopy__(self, memo):
        out = Group()
        for key, val in self.__dict__.items():
            if key != '__name__':
                setattr(out, key,  copy.deepcopy(val, memo))
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
                    not key.startswith(f'_{cname}_') and
                    not (key.startswith('__') and key.endswith('__')) and
                    key not in self.__generic_functions and
                    key not in self.__private)]

    def __getitem__(self, key):

        if isinstance(key, int):
            raise IndexError("Group does not support Integer indexing")

        return getattr(self, key)

    def __setitem__(self, key, value):

        if isinstance(key, int):
            raise IndexError("Group does not support Integer indexing")

        return setattr(self, key, value)

    def __iter__(self):
        return iter(self.keys())

    def keys(self):
        return self.__dir__()

    def values(self):
        return [getattr(self, key) for key in self.__dir__()]

    def items(self):
        return [(key, getattr(self, key)) for key in self.__dir__()]

    def _subgroups(self):
        "return list of names of members that are sub groups"
        return [k for k in self._members() if isgroup(self.__dict__[k])]

    def _members(self):
        "return members"
        out = {}
        for key in self.__dir__():
            if key in self.__dict__:
                out[key] = self.__dict__[key]
        return out

    def _repr_html_(self):
        """HTML representation for Jupyter notebook"""
        html = [f"Group {self.__name__}", "<table>",
                "<tr><td><b>Attribute</b></td><td><b>Type</b></td>",
                "<td><b>Value</b></td></tr>"]
        attrs = self.__dir__()
        for attr in self.__dir__():
            obj = getattr(self, attr)
            atype = type(obj).__name__
            sval = repr_value(obj)
            html.append(f"<tr><td>{attr}</td><td><i>{atype}</i></td><td>{sval}</td></tr>")
        html.append("</table>")
        return '\n'.join(html)


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
                'get_parent', '_path', '__parents')

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
        for grp in self.core_groups:
            self._sys.searchGroups.append(grp)
        self._sys.core_groups = tuple(self._sys.searchGroups[:])

        self._sys.modules = {'_main':self}
        for gname in self.core_groups:
            self._sys.modules[gname] = getattr(self, gname)
        self._fix_searchGroups()

        self._sys.config = Group(home_dir    = site_config.home_dir,
                                 history_file= site_config.history_file,
                                 init_files  = site_config.init_files,
                                 user_larchdir= site_config.user_larchdir,
                                 larch_version= site_config.larch_version,
                                 release_version = site_config.larch_release_version)

    def save_frame(self):
        " save current local/module group"
        self._sys.frames.append((self._sys.localGroup, self._sys.moduleGroup))

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
            sys.localGroup = sys.moduleGroup

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
        if debug:
            print( '====\nLOOKUP ', name)
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
        top = parts.pop()
        out = self.__invalid_name
        if top == self.top_group:
            out = self
        else:
            for grp in searchGroups:
                if public_attr(grp, top):
                    self.__parents.append(grp)
                    out = getattr(grp, top)
        if out is self.__invalid_name:
            raise NameError(f"'{name}' is not defined")

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
                    f"cannot locate member '{prt}' of '{out}'")
        return out

    def has_symbol(self, symname):
        try:
            _ = self.get_symbol(symname)
            return True
        except (LookupError, NameError, ValueError):
            return False

    def has_group(self, gname):
        try:
            _ = self.get_group(gname)
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
        raise LookupError(f"symbol '{gname}' found, but not a group")

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
                raise SyntaxError(f"invalid symbol name '{n}'")
            names.append(n)

        child = names.pop()
        for nam in names:
            if hasattr(grp, nam):
                grp = getattr(grp, nam)
                if not isgroup(grp):
                    raise ValueError(
                        f"cannot create subgroup of non-group '{grp}'")
            else:
                setattr(grp, nam, Group())

        setattr(grp, child, value)
        return value

    def del_symbol(self, name):
        "delete a symbol"
        sym = self._lookup(name, create=False)
        parent, child = self.get_parent(name)
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

    def show_group(self, groupname):
        """display group members --- simple version for tests"""
        out = []
        try:
            group = self.get_group(groupname)
        except (NameError, LookupError):
            return 'Group %s not found' % groupname

        members = dir(group)
        out = ['f== {group.__name__}: {len(members)} symbols ==']
        for item in members:
            obj = getattr(group, item)
            dval = repr_value(obj)
            out.append(f'  {item}: {dval}')
        out.append('\n')
        self._larch.writer.write('\n'.join(out))
