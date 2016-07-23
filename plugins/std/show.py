#!/usr/bin/env python
"""
  Larch show() function
"""
import os
import sys
import types
import numpy
import six
from larch import Group, ValidateLarchPlugin

TERMCOLOR_COLORS = ('grey', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')

@ValidateLarchPlugin
def get(sym=None, _larch=None, **kws):
    """get object from symbol table from symbol name:

    >>> g = group(a = 1,  b=2.3, z = 'a string')
    >>> print get('g.z')
    'a string'

    """
    if sym is None:
        sym = _larch.symtable
    group = None
    symtable = _larch.symtable
    if symtable.isgroup(sym):
        group = sym
    elif isinstance(sym, types.ModuleType):
        group = sym
    elif isinstance(sym, six.string_types):
        group = symtable._lookup(sym, create=False)
    return group


@ValidateLarchPlugin
def show_tree(group, _larch=None, indent=0, groups_shown=None, **kws):
    """show members of a Group, with a tree structure for sub-groups

    > show_tree(group1)

    """
    if groups_shown is None:
        groups_shown = []
    for item in dir(group):
        if (item.startswith('__') and item.endswith('__')):
            continue
        obj = getattr(group, item)
        dval = None
        if _larch.symtable.isgroup(obj):
            _larch.writer.write('%s %s: %s\n' % (indent*' ', item, obj))
            if id(obj) in groups_shown:
                _larch.writer.write('%s     (shown above)\n' % (indent*' '))
            else:
                groups_shown.append(id(obj))
                show_tree(obj, indent=indent+3, _larch=_larch, groups_shown=groups_shown)
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

@ValidateLarchPlugin
def show(sym=None, _larch=None, with_private=False, with_color=True,
          color=None, color2=None, truncate=True, with_methods=True, **kws):
    """show group members:
    Options
    -------
    with_private:  show 'private' members ('__private__') if True
    with_color:    show alternating lines in color if True and color is available.
    truncate:      truncate representation of lengthy lists and tuples if True
    with_methods:  suppress display of methods if False

    """
    if sym is None:
        sym = _larch.symtable
    group = None
    symtable = _larch.symtable
    display  = symtable._sys.display
    get_termcolor_opts = symtable._builtin.get_termcolor_opts
    with_color = with_color and display.use_color

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

    ## set colors for output
    colopts1 = get_termcolor_opts('text', _larch=_larch)
    colopts2 = get_termcolor_opts('text2', _larch=_larch)
    if with_color:
        if color is not None:
            colopts1['color'] = color
        if color2 is not None:
            colopts2['color'] = color2

    _copts = {1: colopts1, 0: colopts2}

    members = dir(group)
    dmembers = []
    nmethods = 0
    for item in members:
        if (item.startswith('__') and item.endswith('__') and
            not with_private):
            continue
        obj = getattr(group, item)
        if callable(obj):
            nmethods +=1
            if not with_methods:
                continue
        dmembers.append((item, obj))
    write = _larch.writer.write

    title_fmt = '== %s: %i methods, %i attributes ==\n'
    write(title_fmt % (title, nmethods, len(dmembers)-nmethods))

    count = 0
    for item, obj in dmembers:
        if (isinstance(obj, numpy.ndarray) and
            (len(obj) > 10 or len(obj.shape)>1)):
            dval = "array<shape=%s, type=%s>" % (repr(obj.shape),
                                                 repr(obj.dtype))
        elif isinstance(obj, (list, tuple)) and truncate and len(obj) > 5:
            dval = "[%s, %s, ... %s, %s]" % (repr(obj[0]), repr(obj[1]),
                                             repr(obj[-2]), repr(obj[-1]))
        else:
            try:
                dval = repr(obj)
            except:
                dval = obj
        count += 1
        copts = _copts[count % 2]
        write('  %s: %s\n' % (item, dval), **copts)
    _larch.writer.flush()

@ValidateLarchPlugin
def get_termcolor_opts(dtype, _larch=None):
    """ get color options suitable for passing to
    larch's writer.write() for color output

    first argument should be string of
    'text', 'text2', 'error', 'comment'"""
    out = {'color': None}
    display  = _larch.symtable._sys.display
    if display.use_color:
        out['color'] = getattr(display.colors, dtype, None)
        for attr in getattr(display.colors, '%s_attrs' % dtype, []):
            out[attr] = True
    return out

def initialize_sys_display(_larch=None):
    """initialize the _sys.display group, holding runtime data
     on display (colors, terminals, etc).
    """
    if _larch is None:
        return
    symtable = _larch.symtable
    if not symtable.has_group('_sys.display'):
        symtable.new_group('_sys.display')
    display = symtable._sys.display

    defaults = dict(text=None, text2='cyan',
                    error='red', comment='green')
    display.colors = Group()
    for key, val in defaults.items():
        setattr(display.colors, key, val)
        setattr(display.colors, "%s_attrs" % key, [])

    display.colors.error_attrs = ['bold']
    display.use_color = True
    display.terminal = 'xterm'

def initializeLarchPlugin(_larch=None):
    """initialize show and friends"""
    cmds = ['show', 'show_tree']
    if _larch is not None:
        _larch.symtable._sys.valid_commands.extend(cmds)
        initialize_sys_display(_larch=_larch)


def registerLarchPlugin():
    return ('_builtin', {'show': show,
                         'get': get,
                         'get_termcolor_opts': get_termcolor_opts,
                         'group2dict': group2dict,
                         'dict2group': dict2group,
                         'show_tree': show_tree})
