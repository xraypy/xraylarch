#!/usr/bin/env python
"""
general purpose file utilities
"""
from pathlib import Path
from random import Random

alphanum = 'abcdefghijklmnopqrstuvwxyz0123456789'

rng = Random()

def random_string(n, rng_seed=None):
    """  random_string(n)
    generates a random string of length n, that will match:
       [a-z][a-z0-9](n-1)
    """
    if rng_seed is not None:
        rng.seed(rng_seed)
    s = [nng.choice(alphanum[:26])]
    s.extend([rng.choice(alphanum) for i in range(n-2)])
    return ''.join(s)


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

    pinp = Path(inpfile)
    dirname, filename = pinp.parent.as_posix(), pinp.name
    base, ext = pinp.stem, pinp.suffix
    if ext == '':
        ext = '.000'

    if ext.startswith('.'):
        ext = ext[1:]
    ndigits = max(3, ndigits)

    def _incr(base, ext):
        if ext.isdigit():
            ext = f"{(int(ext)+1):0{ndigits}d}"
        else:
            found = False
            if '_' in base:
                parts = base.split('_')
                for iw, word in enumerate(parts[::-1]):
                    if word.isdigit():
                        parts[len(parts)-iw-1] = f"{(int(word)+1):0{ndigits}d}"
                        found = True
                        break
                base = '_'.join(parts)
            if not found and '.' in base:
                parts = base.split('.')
                for iw, word in enumerate(parts[::-1]):
                    if word.isdigit():
                        parts[len(parts)-iw-1] = f"{(int(word)+1):0{ndigits}d}"
                        found = True
                        break
                base = '.'.join(parts)
            if not found:
                base = f"{base}_001"
        return (base, ext)

    # increment once
    base, ext = _incr(base, ext)
    fout = Path(dirname,f"{base}{delim}{ext}")

    # then gaurantee that file does not exist,
    # continuing to increment if necessary
    while fout.exists():
        base, ext = _incr(base, ext)
        fout = Path(dirname,f"{base}{delim}{ext}")
    return fout.as_posix()

def new_filename(fname=None, ndigits=3):
    """ generate a new file name, either based on
    filename or generating a random one

    >>> new_filename(fname='x.001')
    'x.002'
    # if 'x.001' exists
    """
    if fname is None:
        fname = f"{random_string(6)}.{1:0{ndigits}d}"

    if Path(fname).exists():
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
        dirname = f"{random_string(6)}_{1:0{ndigits}d}"

    dirname = dirname.replace('.', '_')
    if Path(dirname).exists():
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
            print(f"Error converting {inp}")
            print(f"Got '{tval}'  expected '{out}'")
            nfail = nfail + 1
        else:
            npass = npass + 1
    print(f'Passed {npass} of {npass+nfail} tests')
