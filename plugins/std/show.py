#!/usr/bin/env python
"""
  Larch show() function
"""
import sys
import types
import numpy
from larch.symboltable import HAS_NUMPY

def _show(sym=None, larch=None, **kws):
    """display group members"""
    if larch is None:
        raise Warning("cannot show group -- larch broken?")
    if sym is None:
        sym = '_main'
    group = None
    symtable = larch.symtable
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
        larch.writer.write("%s\n" % repr(sym))
        return

    if title.startswith(symtable.top_group):
        title = title[6:]

    if group == symtable:
        title = 'SymbolTable _main'

    members = dir(group)
    out = ['== %s: %i symbols ==' % (title, len(members))]
    for item in members:
        if not (item.startswith('_Group__') or
                item == '__name__' or
                item.startswith('_SymbolTable__')):
            # out.append('  %s: %s' % (item, repr(getattr(group, item))))
            obj = getattr(group, item)
            dval = repr(obj)

            if HAS_NUMPY and isinstance(obj, numpy.ndarray):
                if len(obj) > 20 or len(obj.shape)>1:
                    dval = "array<shape=%s, type=%s>" % (repr(obj.shape),
                                                         repr(obj.dtype))
            out.append('  %s: %s' % (item, dval))

    larch.writer.write("%s\n" % '\n'.join(out))


def registerLarchPlugin():
    return ('_builtin', {'pshow': _show})
