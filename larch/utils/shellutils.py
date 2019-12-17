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

def _copy(obj):
    """copy an object"""
    return copy(obj)

def _deepcopy(obj):
    """deep copy an object"""
    return deepcopy(obj)

def _parent(name, _larch=None):
    "return parent group name of an object"
    return _larch.symtable._lookup(name)

def _ls(directory='.'):
    """return a list of files in the current directory,
    optionally using '*' to match file names

    Returns
    -------
    a : list of strings
       matching file names

    Examples
    --------
    to list all files::

        larch> ls('.')

    to list all files that end with '.xdi'::

        larch> ls('*.xdi')


    """
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

def _cwd():
    "return current working directory"
    ret = os.getcwd()
    if sys.platform == 'win32':
        ret = ret.replace('\\','/')
    return ret

def _cd(name):
    """change directory to specified directory"""
    name = name.strip()
    if name:
        os.chdir(name)

    ret = os.getcwd()
    if sys.platform == 'win32':
        ret = ret.replace('\\','/')
    return ret

def _mkdir(name, mode=0o777):
    """create directory (and any intermediate subdirectories

    Options:
    --------
      mode   permission mask to use for creating directory (default=0777)
    """
    return os.makedirs(name, mode=mode)

def show_more(text, filename=None, writer=None,
              pagelength=30, prefix='', _larch=None):
    """show lines of text in the style of more """
    txt = text[:]
    if isinstance(txt, str):
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
                x = input(ps %  (100.*i/len(txt)))
                if x in ('q','Q'): return
            except KeyboardInterrupt:
                writer.write("\n")
                return

def _more(fname, pagelength=32, _larch=None):
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
              pagelength=pagelength)
