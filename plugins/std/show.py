#!/usr/bin/env python
"""
  Larch show() function
"""
import sys
import types
import numpy
from larch import Group

def _get(sym=None, _larch=None, **kws):
    """get object from symbol table from symbol name:

    >>> g = group(a = 1,  b=2.3, z = 'a string')
    >>> print get('g.z')
    'a string'

    """
    if _larch is None:
        raise Warning("cannot show group -- larch broken?")
    if sym is None:
        sym = '_main'
    group = None
    symtable = _larch.symtable
    if symtable.isgroup(sym):
        group = sym
    elif isinstance(sym, types.ModuleType):
        group = sym
    elif isinstance(sym, (str, unicode)):
        group = symtable._lookup(sym, create=False)

    return group


def _show(sym=None, _larch=None, with_private=False, **kws):
    """display group members.
    Options
    -------
    with_private:  show 'private' members ('__private__')

    See Also:  show_tree()
    """
    if _larch is None:
        raise Warning("cannot show group -- larch broken?")
    if sym is None:
        sym = '_main'
    group = None
    symtable = _larch.symtable
    title = sym
    if symtable.isgroup(sym):
        group = sym
        title = repr(sym)[1:-1]
    elif isinstance(sym, types.ModuleType):
        group = sym
        title = sym.__name__
    elif isinstance(sym, (str, unicode)):
        group = symtable._lookup(sym, create=False)

    if group is None:
        _larch.writer.write("%s\n" % repr(sym))
        return
    if title.startswith(symtable.top_group):
        title = title[6:]

    if group == symtable:
        title = 'SymbolTable _main'

    members = dir(group)
    out = ['== %s: %i symbols ==' % (title, len(members))]
    for item in members:
        if (item.startswith('__') and item.endswith('__') and
            not with_private):
            continue
        obj = getattr(group, item)
        dval = None
        if isinstance(obj, numpy.ndarray):
            if len(obj) > 10 or len(obj.shape)>1:
                dval = "array<shape=%s, type=%s>" % (repr(obj.shape),
                                                         repr(obj.dtype))
        if dval is None:
            dval = repr(obj)
        out.append('  %s: %s' % (item, dval))
#         if not (item.startswith('_Group__') or
#                 item == '__name__' or item == '_larch' or
#                 item.startswith('_SymbolTable__')):

    _larch.writer.write("%s\n" % '\n'.join(out))


def show_tree(group, _larch=None, indent=0, **kws):
    """show members of a Group, with a tree structure for sub-groups

    > show_tree(group1)

    """
    for item in dir(group):
        if (item.startswith('__') and item.endswith('__')):
            continue
        obj = getattr(group, item)
        dval = None
        if _larch.symtable.isgroup(obj):
            _larch.writer.write('%s %s: %s\n' % (indent*' ', item, obj))
            show_tree(obj, indent=indent+3, _larch=_larch)
        else:
            dval = repr(obj)
            if isinstance(obj, numpy.ndarray):
                if len(obj) > 10 or len(obj.shape)>1:
                    dval = "array<shape=%s, type=%s>" % (repr(obj.shape),
                                                         repr(obj.dtype))
            _larch.writer.write('%s %s: %s\n' % (indent*' ', item, dval))

def group2dict(group, _larch=None):
    "return dictionary of group members"
    return group.__dict__

def dict2group(d, _larch=None):
    "return group created from a dictionary"
    return Group(**d)

def initializeLarchPlugin(_larch=None):
    """initialize show and friends"""
    cmds = ['show', 'show_tree']
    if _larch is not None:
        _larch.symtable._sys.valid_commands.extend(cmds)

def registerLarchPlugin():
    return ('_builtin', {'show': _show, 'get': _get,
                         'group2dict': group2dict,
                         'dict2group': dict2group,
                         'show_tree': show_tree})
