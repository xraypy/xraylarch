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
from glob import glob
from .paths import get_cwd

def _parent(name, _larch=None):
    "return parent group name of an object"
    return _larch.symtable._lookup(name)

def ls(directory='.'):
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
    if sys.platform.startswith('win'):
        for i in range(len(ret)):
            ret[i] = ret[i].replace('\\','/')
    return ret

def cwd():
    "return current working directory"
    ret = get_cwd()
    if sys.platform.startswith('win'):
        ret = ret.replace('\\','/')
    return ret

def cd(name):
    """change directory to specified directory"""
    os.chdir(name.strip())
    return cwd()


def mkdir(name, mode=0o775):
    """create directory (and any intermediate subdirectories)

    Options:
    --------
      mode   permission mask to use for creating directory (default=0775)
    """
    if os.path.exists(name):
        if os.path.isdir(name):
            os.chmod(name, mode)
        else:
            raise FileExistsError(f"'{name}' is a file, cannot make folder with that name")
    else:
        os.makedirs(name, mode=mode)


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
