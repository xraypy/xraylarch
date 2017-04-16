#!/usr/bin/env python
"""
  Larch show() function
"""
import sys
import types
import numpy
from larch import Group, ValidateLarchPlugin
from termcolor import colored
import inspect

@ValidateLarchPlugin
def display(sym=None, _larch=None, with_private=False, with_color=True, color='cyan', truncate=True, with_methods=True, **kws):
    """display group members, like show() but with more features.
    Options
    -------
    with_private:  show 'private' members ('__private__') if True
    with_color:    show alternating lines in color if True
    truncate:      truncate representation of lengthy lists and tuples if True
    with_methods:  suppress display of methods if False

    """
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

    if group is None:
        _larch.writer.write("%s\n" % repr(sym))
        return
    if title.startswith(symtable.top_group):
        title = title[6:]

    if group == symtable:
        title = 'Group _main'

    ## these are the 8 allowed colors in termcolor
    if (not color in ('grey', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')):
        color = 'cyan'

        
    members = dir(group)
    out = ['== %s: %i symbols ==' % (title, len(members))]
    count = 0
    for item in members:
        if (item.startswith('__') and item.endswith('__') and
            not with_private):
            continue
        obj = getattr(group, item)
        if (inspect.ismethod(obj) and not with_methods):
            continue
        count = count+1
        dval = None
        if isinstance(obj, numpy.ndarray):
            if len(obj) > 10 or len(obj.shape)>1:
                dval = "array<shape=%s, type=%s>" % (repr(obj.shape),
                                                         repr(obj.dtype))
        if ((isinstance(obj, list) or isinstance(obj, tuple)) and truncate):
            if len(repr(obj)) > 50:
                dval = "[%s, %s, ... %s, %s]" % (repr(obj[0]), repr(obj[1]),
                                                 repr(obj[-2]), repr(obj[-1]))
        if dval is None:
            dval = repr(obj)
        if ((not with_color) or (count % 2)):
            string = '  %s: %s' % (item, dval)
        else:
            string = colored('  %s: %s' % (item, dval), color)
        out.append(string)

    if not with_methods:
        out[0] = '== %s: %i methods, %i attributes ==' % (title, len(members)-count, count)
    _larch.writer.write("%s\n" % '\n'.join(out))


def initializeLarchPlugin(_larch=None):
    """initialize display"""
    cmds = ['_cshow',]
    if _larch is not None:
        _larch.symtable._sys.valid_commands.extend(cmds)

def registerLarchPlugin():
    return ('_local', {'display': display})
