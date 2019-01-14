#!/usr/bin/env python
"""
utilities for larch
"""
from __future__ import print_function
import re
import sys
from base64 import b64encode, b32encode
import hashlib
import random
from distutils.version import StrictVersion

if sys.version[0] == '3':
    maketrans = str.maketrans
    def bytes2str(s):
        if isinstance(s, str):
            return s
        elif isinstance(s, bytes):
            return s.decode(sys.stdout.encoding)
        return str(s, sys.stdout.encoding)
    def str2bytes(s):
        'string to byte conversion'
        if isinstance(s, bytes):
            return s
        return bytes(s, sys.stdout.encoding)

else:
    from string import maketrans
    bytes2str = str2bytes = str



RESERVED_WORDS = ('and', 'as', 'assert', 'break', 'class', 'continue',
                  'def', 'del', 'elif', 'else', 'eval', 'except', 'exec',
                  'execfile', 'finally', 'for', 'from', 'global', 'if',
                  'import', 'in', 'is', 'lambda', 'not', 'or', 'pass',
                  'print', 'raise', 'return', 'try', 'while', 'with',
                  'group', 'end', 'endwhile', 'endif', 'endfor', 'endtry',
                  'enddef', 'True', 'False', 'None')

NAME_MATCH = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$").match
VALID_SNAME_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
VALID_NAME_CHARS = '.%s' % VALID_SNAME_CHARS
VALID_CHARS1 = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'

BAD_FILECHARS = ';~,`!%$@$&^?*#:"/|\'\\\t\r\n (){}[]<>'
GOOD_FILECHARS = '_'*len(BAD_FILECHARS)

BAD_VARSCHARS = BAD_FILECHARS + '=+-.'
GOOD_VARSCHARS = '_'*len(BAD_VARSCHARS)

TRANS_FILE = maketrans(BAD_FILECHARS, GOOD_FILECHARS)
TRANS_VARS = maketrans(BAD_VARSCHARS, GOOD_VARSCHARS)


def PrintExceptErr(err_str, print_trace=True):
    " print error on exceptions"
    print('\n***********************************')
    print(err_str)
    #print 'PrintExceptErr', err_str
    try:
        print('Error: %s' % sys.exc_type)
        etype, evalue, tback = sys.exc_info()
        if print_trace == False:
            tback = ''
        sys.excepthook(etype, evalue, tback)
    except:
        print('Error printing exception error!!')
        raise
    print('***********************************\n')

def strip_comments(sinp, char='#'):
    "find character in a string, skipping over quoted text"
    if sinp.find(char) < 0:
        return sinp
    i = 0
    while i < len(sinp):
        tchar = sinp[i]
        if tchar in ('"',"'"):
            eoc = sinp[i+1:].find(tchar)
            if eoc > 0:
                i = i + eoc
        elif tchar == char:
            return sinp[:i].rstrip()
        i = i + 1
    return sinp

def strip_quotes(t):
    d3, s3, d1, s1 = '"""', "'''", '"', "'"
    if hasattr(t, 'startswith'):
        if ((t.startswith(d3) and t.endswith(d3)) or
            (t.startswith(s3) and t.endswith(s3))):
            t = t[3:-3]
        elif ((t.startswith(d1) and t.endswith(d1)) or
              (t.startswith(s1) and t.endswith(s1))):
            t = t[1:-1]
    return t

def isValidName(name):
    "input is a valid name"
    if name in RESERVED_WORDS:
        return False
    tnam = name[:].lower()
    return NAME_MATCH(tnam) is not None

def fixName(name, allow_dot=True):
    "try to fix string to be a valid name"
    if isValidName(name):
        return name

    if isValidName('_%s' % name):
        return '_%s' % name
    chars = []
    valid_chars = VALID_SNAME_CHARS
    if allow_dot:
        valid_chars = VALID_NAME_CHARS
    for s in name:
        if s not in valid_chars:
            s = '_'
        chars.append(s)
    name = ''.join(chars)
    # last check (name may begin with a number or .)
    if not isValidName(name):
        name = '_%s' % name
    return name


def fix_filename(s):
    """fix string to be a 'good' filename.
    This may be a more restrictive than the OS, but
    avoids nasty cases."""
    t = str(s).translate(TRANS_FILE)
    if t.count('.') > 1:
        for i in range(t.count('.') - 1):
            idot = t.find('.')
            t = "%s_%s" % (t[:idot], t[idot+1:])
    return t

def fix_varname(s):
    """fix string to be a 'good' variable name."""
    t = str(s).translate(TRANS_VARS)
    if t[0] not in VALID_CHARS1:
        t = '_%s' % t
    while t.endswith('_'):
        t = t[:-1]
    return t

def unique_name(name, nlist, max=1000):
    """return name so that is is not in list,
    by appending _1, _2, ... as necessary up to a max suffix

    >>> unique_name('foo', ['bar, 'baz'])
    'foo'

    >>> unique_name('foo', ['foo', 'bar, 'baz'])
    'foo_1'

    """
    out = name
    if name in nlist:
        for i in range(1, max+1):
            out = "%s_%i"  % (name, i)
            if out not in nlist:
                break
    return out


def isNumber(num):
    "input is a number"
    try:
        cnum = complex(num)
        return True
    except ValueError:
        return False

def isLiteralStr(inp):
    "is a literal string"
    return ((inp.startswith("'") and inp.endswith("'")) or
            (inp.startswith('"') and inp.endswith('"')))


def find_delims(s, delim='"',match=None):
    """find matching delimeters (quotes, braces, etc) in a string.
    returns
      True, index1, index2 if a match is found
      False, index1, len(s) if a match is not found
    the delimiter can be set with the keyword arg delim,
    and the matching delimiter with keyword arg match.

    if match is None (default), match is set to delim.

    >>> find_delims(mystr, delim=":")
    >>> find_delims(mystr, delim='<', match='>')
    """
    esc, dbesc = "\\", "\\\\"
    if match is None:
        match = delim
    j = s.find(delim)
    if j > -1 and s[j:j+len(delim)] == delim:
        p1, p2, k = None, None, j
        while k < j+len(s[j+1:]):
            k = k+1
            if k > 0: p1 = s[k-1:k]
            if k > 1: p2 = s[k-2:k]
            if (s[k:k+len(match)] == match and not (p1 == esc and p2 != dbesc)):
                return True, j, k+len(match)-1
            p1 = s[k:k+1]
    return False, j, len(s)

def version_ge(v1, v2):
    "returns whether version string 1 >= version_string2"
    return StrictVersion(bytes2str(v1)) >= StrictVersion(bytes2str(v2))


def b32hash(s):
    """return a base32 hash of a string"""
    _hash = hashlib.sha256()
    _hash.update(str2bytes(s))
    return bytes2str(b32encode(_hash.digest()))

def b64hash(s):
    """return a base64 hash of a string"""
    _hash = hashlib.sha256()
    _hash.update(str2bytes(s))
    return bytes2str(b64encode(_hash.digest()))

def file2groupname(filename, slen=5, symtable=None):
    """create a group name based of filename
    the group name will have a string component of
    length slen followed by a 4 digit number

    Arguments
    ---------
    filename  (str)  filename to use
    slen      (int)  length of string portion (default 4)
    symtable  (None or larch symbol table) symbol table for
              checking that the group name is unique
    """
    def randstr(n):
        return ''.join([chr(random.randint(97, 122)) for i in range(n)])

    gname = fix_varname(filename).lower() +  randstr(slen)
    if '_' in gname:
        gname = gname.replace('_', '')
        gname = fix_varname(gname)

    fmt, count, maxcount = "%s{:04d}", 1, 999
    fstr = fmt % (gname[:slen])
    gname = fstr.format(count)
    if symtable is not None:
        scount = 0
        while hasattr(symtable, gname):
            count += 1
            if count > maxcount:
                scount += 1
                count = 1
                fstr = fmt % randstr(slen)
            gname = fstr.format(count)
            if scount > 1000:
                raise ValueError("exhausted unique group names")
    return gname
