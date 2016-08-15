#!/usr/bin/env python
"""
  Larch shell utilities:
    more()
    ls()
    cwd()
    cd()
"""

import os
import sys
from copy import copy, deepcopy
from glob import glob
import six
from larch import ValidateLarchPlugin

MODNAME = '_builtin'

def _copy(obj, **kws):
    """copy an object"""
    return copy(obj)

def _deepcopy(obj, **kws):
    """deep copy an object"""
    return deepcopy(obj)

@ValidateLarchPlugin
def _parent(name, _larch=None, **kw):
    "print out parent group name of an object"
    print(_larch.symtable._lookup(name, create=False))

@ValidateLarchPlugin
def _ls(directory='.', _larch=None, **kws):
    """return a list of files in the current directory"""
    directory.strip()
    if len(directory) == 0:
        arg = '.'
    if os.path.isdir(directory):
        ret = os.listdir(directory)
    else:
        ret = glob(directory)
    if sys.platform == 'win32':
        for i in range(len(ret)):
            ret[i] = ret[i].replace('\\','/')
    return ret

def _cwd(**kws):
    "return current working directory"
    ret = os.getcwd()
    if sys.platform == 'win32':
        ret = ret.replace('\\','/')
    return ret

def _cd(name, **kws):
    """change directory to specified directory"""
    name = name.strip()
    if name:
        os.chdir(name)

    ret = os.getcwd()
    if sys.platform == 'win32':
        ret = ret.replace('\\','/')
    return ret

def _mkdir(name, mode=0o777, **kws):
    """create directory (and any intermediate subdirectories

    Options:
    --------
      mode   permission mask to use for creating directory (default=0777)
    """
    return os.makedirs(name, mode=mode)

@ValidateLarchPlugin
def show_more(text, filename=None, writer=None,
              pagelength=30, prefix='', _larch=None, **kws):
    """show lines of text in the style of more """
    txt = text[:]
    if isinstance(txt, six.string_types):
        txt = txt.split('\n')
    if len(txt) <1:
        return
    prompt = '== hit return for more, q to quit'
    ps = "%s (%%.2f%%%%) == " % prompt
    if filename:
        ps = "%s (%%.2f%%%%  of %s) == " % (prompt, filename)

    if writer is None:
        writer = sys.stdout

    i = 0
    for i in range(len(txt)):
        if txt[i].endswith('\n'):
            _larch.writer.write("%s%s" % (prefix, txt[i]))
        else:
            writer.write("%s%s\n" % (prefix, txt[i]))
        i = i + 1
        if i % pagelength == 0:
            try:
                x = raw_input(ps %  (100.*i/len(txt)))
                if x in ('q','Q'): return
            except KeyboardInterrupt:
                writer.write("\n")
                return

@ValidateLarchPlugin
def _more(fname, pagelength=32, _larch=None, **kws):
    """list file contents:
    > more('file.txt')
by default, the file is shown 32 lines at a time.
You can specify the number of lines to show at a time
with the  pagelength option:
    > more('file.txt', pagelength=10)
    """
    output = _larch.writer.write
    if not os.path.exists(fname):
        output("File '%s' not found.\n" % fname)
        return

    elif not os.path.isfile(fname):
        output("'%s' not a file.\n" % fname)
        return

    try:
        text = open(fname, 'r').readlines()
    except IOError:
        output("cannot open file: %s\n" % fname)
        return

    show_more(text, filename=fname, _larch=_larch,
              pagelength=pagelength, **kws)

def initializeLarchPlugin(_larch=None):
    """initialize ls as a valid command"""
    cmds = ['ls', 'cd', 'more']
    if _larch is not None:
        _larch.symtable._sys.valid_commands.extend(cmds)

def registerLarchPlugin():
    return ('_builtin', {'copy': _copy, 'deepcopy': _deepcopy,
                         'more': _more, 'parent': _parent,
                         'ls': _ls,  'mkdir': _mkdir,
                         'cd': _cd,  'cwd': _cwd })
