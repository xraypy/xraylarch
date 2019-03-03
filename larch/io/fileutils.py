#!/usr/bin/env python
"""
general purpose file utilities
"""
import time
import os
import sys
from random import seed, randrange
from string import printable
from ..utils.strutils import fix_filename, fix_varname, strip_quotes

def asciikeys(adict):
    """ensure a dictionary has ASCII keys (and so can be an **kwargs)"""
    return dict((k.encode('ascii'), v) for k, v in adict.items())

def get_timestamp(with_t=False):
    """return ISO format of current timestamp:
    argument
    --------
    with_t    boolean (False)

    when with_t is True, the returned string
    will match 'YYYY-mm-ddTHH:MM:SS'
    otherwise  'YYYY-mm-dd HH:MM:SS'
    """
    if with_t:
        time.strftime('%Y-%m-%dT%H:%M:%S')
    return time.strftime('%Y-%m-%d %H:%M:%S')

def random_string(n):
    """  random_string(n)
    generates a random string of length n, that will match:
       [a-z][a-z0-9](n-1)
    """
    seed(time.time())
    s = [printable[randrange(0,36)] for i in range(n-1)]
    s.insert(0, printable[randrange(10,36)])
    return ''.join(s)

def pathOf(dir, base, ext, delim='.'):
    """return the normalized path name of file created with
    a directory, base, extension, and delimiter"""
    p = os.path
    return p.normpath(p.join(dir,"%s%s%s" % (base, delim, ext)))

def unixpath(d):
    "ensure path uses unix delimiters"
    d = d.replace('\\','/')
    if not d.endswith('/'): d = '%s/' % d
    return d

def winpath(d):
    "ensure path uses windows delimiters"
    if d.startswith('//'): d = d[1:]
    d = d.replace('/','\\')
    if not d.endswith('\\'): d = '%s\\' % d
    return d

def nativepath(d):
    "ensure path uses delimiters for current OS"
    if os.name == 'nt':
        return winpath(d)
    return unixpath(d)

def get_homedir():
    """return home directory, or best approximation
    On Windows, this returns the Roaming Profile APPDATA
    (use CSIDL_LOCAL_APPDATA for Local Profile)
    """
    homedir = '.'
    if os.name == 'nt':
        # For Windows, ask for parent of Roaming 'Application Data' directory
        try:
            from win32com.shell import shellcon, shell
            homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        except ImportError: # if win32com is not found
            homedir = os.get_environ('HOME', '.')
    else:
        try:
            os.path.expanduser("~")
        except:
            pass
    return homedir

def gformat(val, length=11):
    """format a number with '%g'-like format, except that
    the return will be length ``length`` (default=12)
    and have at least length-6 significant digits
    """
    length = max(length, 7)
    fmt = '{: .%ig}' % (length-6)
    if isinstance(val, int):
        out = ('{: .%ig}' % (length-2)).format(val)
        if len(out) > length:
            out = fmt.format(val)
    else:
        out = fmt.format(val)
    if len(out) < length:
        if 'e' in out:
            ie = out.find('e')
            if '.' not in out[:ie]:
                out = out[:ie] + '.' + out[ie:]
            out = out.replace('e', '0'*(length-len(out))+'e')
        else:
            fmt = '{: .%ig}' % (length-1)
            out = fmt.format(val)[:length]
            if len(out) < length:
                pad = '0' if '.' in  out else ' '
                out += pad*(length-len(out))
    return out

def increment_filename(inpfile, ndigits=3, delim='.'):
    """
    increment a data filename, returning a new (non-existing) filename

       first see if a number is before '.'.  if so, increment it.
       second look for number in the prefix. if so, increment it.
       lastly, insert a '_001' before the '.', preserving suffix.

    the numerical part of the file name will contain at least three digits.

    >>> increment_filename('a.002')
    'a.003'
    >>> increment_filename('a.999')
    'a.1000'
    >>> increment_filename('b_017.xrf')
    'b_018.xrf'
    >>> increment_filename('x_10300243.dat')
    'x_10300244.dat'

    >>> increment_filename('x.dat')
    'x_001.dat'

    >>> increment_filename('C:/program files/oo/data/x.002')
    'C:/program files/ifeffit/data/x.003'

    >>> increment_filename('a_001.dat')
    'a_002.dat'

    >>> increment_filename('a.001.dat')
    'a.002.dat'

    >>> increment_filename('a_6.dat')
    'a_007.dat'

    >>> increment_filename('a_001.002')
    'a_001.003'

    >>> increment_filename("path/a.003")
    'path/a.004'
"""

    dirname, filename = os.path.split(inpfile)
    base, ext = os.path.splitext(filename)
    if ext == '':
        ext = '.000'

    if ext.startswith('.'):
        ext   = ext[1:]
    if ndigits < 3:
        ndigits = 3
    form  = "%%.%ii" % (ndigits)

    def _incr(base, ext):
        if ext.isdigit():
            ext = form % (int(ext)+1)
        else:
            found = False
            if '_' in base:
                parts = base.split('_')
                for iw, word in enumerate(parts[::-1]):
                    if word.isdigit():
                        parts[len(parts)-iw-1] = form % (int(word)+1)
                        found = True
                        break
                base = '_'.join(parts)
            if not found and '.' in base:
                parts = base.split('.')
                for iw, word in enumerate(parts[::-1]):
                    if word.isdigit():
                        parts[len(parts)-iw-1] = form % (int(word)+1)
                        found = True
                        break
                base = '.'.join(parts)
            if not found:
                base = "%s_001" % base
        return (base, ext)

    # increment once
    base, ext = _incr(base, ext)
    fout = pathOf(dirname, base, ext, delim=delim)

    # then gaurantee that file does not exist,
    # continuing to increment if necessary
    while (os.path.exists(fout)):
        base, ext = _incr(base, ext)
        fout = pathOf(dirname, base, ext, delim=delim)
    return fout

def new_filename(fname=None, ndigits=3):
    """ generate a new file name, either based on
    filename or generating a random one

    >>> new_filename(fname='x.001')
    'x.002'
    # if 'x.001' exists
    """
    if fname is None:
        ext = ("%%.%ii" % ndigits) % 1
        fname = "%s.%s" % (random_string(6), ext)

    if os.path.exists(fname):
        fname = increment_filename(fname, ndigits=ndigits)

    return fname

def new_dirname(dirname=None, ndigits=3):
    """ generate a new subdirectory name (no '.' in name), either
    based on dirname or generating a random one

    >>> new_dirname('x.001')
    'x_002'
    # if 'x_001' exists
    """
    if dirname is None:
        ext = ("%%_%ii" % ndigits) % 1
        dirname = "%s_%s" % (random_string(6), ext)

    dirname = dirname.replace('.', '_')
    if os.path.exists(dirname):
        dirname = increment_filename(dirname, ndigits=ndigits, delim='_')
    return dirname

def test_incrementfilename():
    tests = (('a.002', 'a.003'),
             ('a.999', 'a.1000'),
             ('b_017.xrf',  'b_018.xrf'),
             ('x_10300243.dat', 'x_10300244.dat'),
             ('x.dat' , 'x_001.dat'),
             ('C:/program files/data/x.002',
              'C:/program files/data/x.003'),
             ('a_001.dat', 'a_002.dat'),
             ('a_6.dat', 'a_007.dat'),
             ('a_001.002', 'a_001.003'),
             ('path/a.003',  'path/a.004'))
    npass = nfail = 0
    for inp,out in tests:
        tval = increment_filename(inp)
        if tval != out:
            print( "Error converting " , inp)
            print( "Got '%s'  expected '%s'" % (tval, out))
            nfail = nfail + 1
        else:
            npass = npass + 1
    print('Passed %i of %i tests' % (npass, npass+nfail))
