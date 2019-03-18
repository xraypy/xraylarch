#!/usr/bin/env python
"""
  Larch column file reader: read_ascii
"""
import os
import sys
import time
import string
import numpy as np
from dateutil.parser import parse as dateparse
from math import log10
from larch import Group
from larch.symboltable import isgroup
from .fileutils import fix_varname


MODNAME = '_io'
TINY = 1.e-7
MAX_FILESIZE = 100*1024*1024  # 100 Mb limit
COMMENTCHARS = '#;%*!$'

def getfloats(txt, allow_times=True):
    """convert a line of numbers into a list of floats,
    as for reading a file with columnar numerical data.

    Arguments
    ---------
      txt           str, line of text to parse
      allow_times   bool, whether to support time stamps [True]

    Returns
    -------
      list, each entry either a float or None

    Notes
    -----
      The `allow_times` will try to support common date-time strings
      using the dateutil module, returning a numerical value as the
      Unix timestamp, using
          time.mktime(dateutil.parser.parse(word).timetuple())
    """
    words = [w.strip() for w in txt.replace(',', ' ').split()]
    mktime = time.mktime
    for i, w in enumerate(words):
        val = None
        try:
            val = float(w)
        except ValueError:
            try:
                val = mktime(dateparse(w).timetuple())
            except ValueError:
                pass
        words[i] = val
    return words

def colname(txt):
    return fix_varname(txt.strip().lower()).replace('.', '_')


def lformat(val, length=12):
    """Format a number with fixed-length format, somewhat like '%g' except that

        a) the length of the output string will be the requested length.
        b) positive numbers will have a leading blank.
        b) the precision will be as high as possible.
        c) trailing zeros will not be trimmed.

    The precision will typically be length-7, but may be better than
    that for values with absolute value between 1.e-5 and 1.e8.

    Arguments
    ---------
    val       value to be formatted
    length    length of output string

    Returns
    -------
    string of specified length.

    Notes
    ------
     Positive values will have leading blank.

    """
    try:
        expon = int(log10(abs(val)))
    except (OverflowError, ValueError):
        expon = 0
    length = max(length, 7)
    form = 'e'
    prec = length - 7
    if abs(expon) > 99:
        prec -= 1
    elif ((expon > 0 and expon < (prec+4)) or
          (expon <= 0 and -expon < (prec-1))):
        form = 'f'
        prec += 4
        if expon > 0:
            prec -= expon
    fmt = '{0: %i.%i%s}' % (length, prec, form)
    return fmt.format(val)

def read_ascii(filename, labels=None, simple_labels=False,
               sort=False, sort_column=0, delimeter=None, _larch=None):
    """read a column ascii column file, returning a group containing the data
    extracted from the file.

    read_ascii(filename, labels=None, simple_labels=False, sort=False, sort_column=0)

    Arguments
    ---------
     filename (str)        name of file to read
     labels (list or None) list of labels to use for column labels [None]
     simple_labels (bool)  whether to force simple column labels (note 1) [False]
     delimeter (str)       string to use to split label line
     sort (bool)           whether to sort row data (note 2) [False]
     sort_column (int)     column to use for sorting (note 2) [0]

    Returns
    --------
      group containing data read from file

    Notes
    -----
      1. column labels.  If `labels` is left the default value of `None`,
         column labels will be tried to be created from the line
         immediately preceeding the data and the provided delimeter, and may
         use 'col1', 'col2', etc if suitable column labels cannot be figured out.
         The labels will be used as names for the 1-d arrays for each column.
         If `simple_labels` is  `True`, the names 'col1', 'col2' etc will be used
         regardless of the column labels found in the file.

      2. sorting.  Data can be sorted to be in increasing order of any column,
         by giving the column index (starting from 0).

      3. header parsing. If header lines are of the forms of
            KEY : VAL
            KEY = VAL
         these will be parsed into a 'attrs' dictionary in the returned group.


    The returned group will have a number of members:

       GROUP.filename: text name of the file
       GROUP.array_labels: array labels, names of 1-D arrays
       GROUP.data:     2-dimensional data (ncolumns, nrows)
       GROUP.header:   array of text lines of the header.
       GROUP.footer:   array of text lines of the footer (text after the block of numerical data)
       GROUP.attrs :   group of attributes parsed from header lines
    """
    if not os.path.isfile(filename):
        raise OSError("File not found: '%s'" % filename)
    if os.stat(filename).st_size > MAX_FILESIZE:
        raise OSError("File '%s' too big for read_ascii()" % filename)

    with open(filename, 'r') as fh:
        text = fh.read()

    text = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')

    labelline = None
    ncol = None
    data, footers, headers = [], [], []

    text.reverse()
    section = 'FOOTER'

    for line in text:
        line = line.strip()
        if len(line) < 1:
            continue
        # look for section transitions (going from bottom to top)
        if section == 'FOOTER' and not None in getfloats(line):
            section = 'DATA'
        elif section == 'DATA' and None in getfloats(line):
            section = 'HEADER'
            labelline = line
            if labelline[0] in COMMENTCHARS:
                labelline = labelline[1:].strip()
        # act of current section:
        if section == 'FOOTER':
            footers.append(line)
        elif section == 'HEADER':
            headers.append(line)
        elif section == 'DATA':
            rowdat  = getfloats(line)
            if ncol is None:
                ncol = len(rowdat)
            elif ncol > len(rowdat):
                rowdat.extend([np.nan]*(ncol-len(rowdat)))
            elif ncol < len(rowdat):
                for i in data:
                    i.extend([np.nan]*(len(rowdat)-ncol))
                ncol = len(rowdat)
            data.append(rowdat)

    # reverse header, footer, data, convert to arrays
    footers.reverse()
    headers.reverse()
    data.reverse()
    data = np.array(data).transpose()

    # try to parse attributes from header text
    header_attrs = {}
    for hline in headers:
        hline = hline.strip().replace('\t', ' ')
        if len(hline) < 1: continue
        if hline[0] in COMMENTCHARS:
            hline = hline[1:].strip()
        keywds = []
        if ':' in hline: # keywords in  'x: 22'
            words = hline.split(':', 1)
            keywds = words[0].split()
        elif '=' in hline: # keywords in  'x = 22'
            words = hline.split('=', 1)
            keywds = words[0].split()
        if len(keywds) == 1:
            key = colname(keywds[0])
            if key.startswith('_'):
                key = key[1:]
            if len(words) > 1:
                header_attrs[key] = words[1].strip()

    if sort and sort_column >= 0 and sort_column < ncol:
         data = data[:, np.argsort(data[sort_column])]

    path, fname = os.path.split(filename)
    attrs = {'filename': filename}
    group = Group(name='ascii_file %s' % filename,
                  path=filename,
                  filename=fname,
                  header=headers,
                  data=data)

    if len(footers) > 0:
        group.footer = footers

    group.attrs = Group(name='header attributes from %s' % filename)
    for key, val in header_attrs.items():
        setattr(group.attrs, key, val)

    if isinstance(labels, str):
        labelline = labels
        labels = None
    set_array_labels(group, labels=labels, simple_labels=simple_labels,
                     labelline=labelline, delimeter=delimeter)

    return group

def set_array_labels(group, labels=None, labelline=None, delimeter=None,
                     simple_labels=False, save_oldarrays=False, _larch=None):
    """set array names for a group from its 2D `data` array.

    Arguments
    ----------
      labels (list of strings or None)  array of labels to use
      labelline (string or None): text to parse for labels
      delimeter (string or None): delimeter to split labelline (None)
      simple_labels (bool):   flag to use ('col1', 'col2', ...) [False]
      save_oldarrays (bool):  flag to save old array names [False]


    Returns
    -------
       group with newly named attributes of 1D array data, and
       an updated `array_labels` giving the mapping of `data`
       columns to attribute names.

    Notes
    ------
      1. The order for resolution is: `simple_labels=True`, followed
         by `labels`, then `labelline`.

      2. When using `labelline`, the `delimeter` will be used to split
         the line of text. If left as `None`, any whitespace will be used.
         Also, when using `labelline` and `delimeter`, more than half of
         the columns must have an explicit label.

      3. Array labels must be valid python names. If not enough labels
         are specified, or if name clashes arise, the array names may be
         modified, often by appending an underscore and letter or by using
         ('col1', 'col2', ...) etc.

      4. When `save_oldarrays` is `False` (the default), arrays named in the
         current `group.array_labels` will be erased.  Other arrays and
         attributes will not be changed.

    """
    write = sys.stdout.write
    if _larch is not None:
        write = _larch.writer.write
    if not hasattr(group, 'data'):
        write("cannot set array labels for group '%s': no `data`\n" % repr(group))
        return

    # clear old arrays, if desired
    oldlabels = getattr(group, 'array_labels', None)
    if oldlabels is not None and not save_oldarrays:
        for attr in oldlabels:
            if hasattr(group, attr):
                delattr(group, attr)

    ncols, nrow = group.data.shape

    ####
    # step 1: determine user-defined labels from input options
    # generating array `tlabels` for test labelsaZA
    #
    # generate simple column labels, used as backup
    clabels = ['col%i' % (i+1) for i in range(ncols)]

    # allow labels to really be 'labelline
    if isinstance(labels, str) and labelline is None:
        labelline = labels
        labels = None

    # convert user input into candidate labels
    tlabels = None

    # if labelline provided, split with provided delimeter
    # or the best delimeter of '\t', ',', '|', or whitespace
    delim = delimeter
    if labelline is not None:
        if delim is None:
            for dtest in ('\t', ',', '|', '&'):
                if  labelline.count(dtest) > int(ncols/2.0)-1:
                    delim = dtest
                    break
        tlabels = [colname(l) for l in labelline.split(delim)]
    elif labels is not None:
        tlabels = labels
    # if simple column names requested or above failed, use simple column names
    if simple_labels or tlabels is None:
        tlabels = clabels

    ####
    # step 2: check input and correct problems
    # 2.a: check for not enough and too many labels
    if len(tlabels) < ncols:
        for i in range(len(tlabels), ncols):
            tlabels.append("col%i" % (i+1))
    elif len(tlabels) > ncols:
        tlabels = tlabels[:ncols]

    # 2.b: check for names that clash with group attributes
    # or that are repeated, append letter.
    reserved_names = ('data', 'array_labels', 'filename',
                      'attrs', 'header', 'footer')
    extras = string.ascii_lowercase
    labels = []
    for i in range(ncols):
        lname = tlabels[i]
        if lname in reserved_names or lname in labels:
            lname = lname + '_a'
            j = 0
            while lname in labels:
                j += 1
                if j == len(extras):
                    break
                lname = "%s_%s" % (tlabels[i], extras[j])
        if lname in labels:
            lname = clabels[i]
        labels.append(lname)

    ####
    # step 3: assign attribue names, set 'array_labels'
    for i, name in enumerate(labels):
        setattr(group, name, group.data[i])
    group.array_labels = labels
    return group


def write_ascii(filename, *args, **kws):
    """write a list of items to an ASCII column file

    write_ascii(filename, arg1, arg2, arg3, ... **args)

    arguments
    ---------
    commentchar: character for comment ('#')
    label:       array label line (autogenerated)
    header:      array of strings for header

    """
    ARRAY_MINLEN = 2
    _larch = kws.get('_larch', None)
    write = sys.stdout.write
    if _larch is not None:
        write = _larch.writer.write

    com = kws.get('commentchar', '#')
    label = kws.get('label', None)
    header = kws.get('header', [])

    arrays = []
    arraylen = None

    for arg in args:
        if isinstance(arg, np.ndarray):
            if len(arg) > ARRAY_MINLEN:
                if arraylen is None:
                    arraylen = len(arg)
                else:
                    arraylen = min(arraylen, len(arg))
                arrays.append(arg)
            else:
                header.append(repr(arg))

        else:
            header.append(repr(arg))

    if arraylen is None:
        raise ValueError("write_ascii() need %i or more elements in arrays." % ARRAY_MINLEN)

    buff = []
    if header is None:
        buff = ['%s Output from Larch %s' % (com, time.ctime())]
    for s in header:
        buff.append('%s %s' % (com, s))
    buff.append('%s---------------------------------'% com)
    if label is None:
        label = (' '*13).join(['col%i' % (i+1) for i in range(len(arrays))])
    buff.append('#  %s' % label)

    arrays = np.array(arrays)
    for i in range(arraylen):
        w = [" %s" % lformat(val[i], length=14) for val in arrays]
        buff.append('  '.join(w))

    try:
        fout = open(filename, 'w')
    except:
        write("cannot open file %s'\n" % filename)
        return

    try:
        fout.write('\n'.join(buff))
        fout.write('\n')
    except:
        write("cannot write to file %s'\n" % filename)
        return
    write("wrote to file '%s'\n" % filename)


def write_group(filename, group, scalars=None, arrays=None,
                arrays_like=None, commentchar='#', _larch=None):
    """write components of a group to an ASCII column file

    write_group(filename, group, commentchar='#')

    Warning: This is pretty minimal and may work poorly
    for large groups of complex data.
    """

    items = dir(group)
    npts = 0
    if arrays is None:
        arrays = []
    if scalars is None:
        scalars = []

    if arrays_like is not None and arrays_like in items:
        array = getattr(group, arrays_like)
        if isinstance(array, np.ndarray):
            npts = len(array)

    for name in items:
        val = getattr(group, name)
        if isinstance(val, np.ndarray):
            if npts != 0 and npts == len(val) and name not in arrays:
                arrays.append(name)

    header =[]
    for s in scalars:
        if s in items:
            val = getattr(group, s)
            header.append("%s = %s" % (s, val))

    label = '  '.join(arrays)

    args = []
    for name in arrays:
        if name in items:
            args.append(getattr(group, name))

    write_ascii(filename, *args, commentchar=commentchar,
                label=label, header=header, _larch=_larch)


def guess_filereader(filename, _larch=None):
    """guess function name to use to read an ASCII data file based
    on the file header

    Arguments
    ---------
    filename (str)   name of file to be read

    Returns
    -------
      name of function (as a string) to use to read file
    """
    with open(path, 'r') as fh:
        line1 = fh.readline()
    line1 = lines[0].lower()

    reader = 'read_ascii'
    if 'xdi' in line1:
        reader = 'read_xdi'
        if ('epics stepscan' in line1 or 'gse' in line1):
            reader = 'read_gsexdi'
    elif 'epics scan' in line1:
        reader = 'read_gsescan'
    return reader
