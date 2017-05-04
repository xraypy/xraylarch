#!/usr/bin/env python
"""
  Larch column file reader: read_ascii
"""
import os
import time
from  dateutil.parser import parse as dateparse
import numpy as np
from larch import ValidateLarchPlugin, Group
from larch.utils import fixName
from larch.symboltable import isgroup


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
    return fixName(txt.strip().lower()).replace('.', '_')


def iso8601_time(ts):
    tzone = '-%2.2i:00' % (time.timezone/3600)
    s = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))
    return "%s%s" % (s, tzone)

def read_ascii(filename, labels=None, simple_labels=False,
               sort=False, sort_column=0, _larch=None):
    """read a column ascii column file, returning a group containing the data
    extracted from the file.

    read_ascii(filename, labels=None, simple_labels=False, sort=False, sort_column=0)

    Arguments
    ---------
     filename (str)           name of file to read
     labels (list or None) list of labels to use for column labels [None]
     simple_labels (bool)  whether to force simple column labels (note 1) [False]
     sort (bool)           whether to sort row data (note 2) [False]
     sort_column (int)     column to use for sorting (note 2) [0]

    Returns
    --------
      group containing data read from file

    Notes
    -----
      1. column labels.  If `labels` is left the default value of `None`,
         column labels will be tried to be created from the line
         immediately preceeding the data, or using 'col1', 'col2', etc if
         column labels cannot be figured out.  The labels will be used as
         names for the 1-d arrays for each column.  If `simple_labels` is
         `True`, the names 'col1', 'col2' etc will be used regardless of
         the column labels found in the file.

      2. sorting.  Data can be sorted to be in increasing order of any column,
         by giving the column index (starting from 0).

      3. header parsing. If header lineas are of the forms of
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

    _labelline = None
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
            _labelline = line
            if _labelline[0] in COMMENTCHARS:
                _labelline = _labelline[1:].strip()
        # act of current section:
        if section == 'FOOTER':
            footers.append(line)
        elif section == 'HEADER':
            headers.append(line)
        elif section == 'DATA':
            rowdat  = getfloats(line)
            if ncol is None:
                ncol = len(rowdat)
            if ncol == len(rowdat):
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

    ncols, nrow = data.shape

    # set column labels from label line
    _labels = None
    _clabels = ['col%i' % (i+1) for i in range(ncols)]
    if labels is not None:
        labels = labels.replace(',', ' ').replace('\t', ' ')
        _labels = [colname(l) for l in labels.split()]
    elif simple_labels or _labelline is None:
        _labels = _clabels
    else:
        _labelline = _labelline.lower()
        for delim in ('\t', ','):
            if delim in _labelline:
                _labs = [colname(l) for l in _labelline.split(delim)]
                if len(_labs) > int(1 + ncols/2.0):
                    _labels = _labs
                    break
        if _labels is None:
            _labelline = _labelline.replace(', ', '  ').replace('\t', ' ')
            _labels = [colname(l) for l in _labelline.split()]

    if _labels is None:
        _labels = _clabels
    if len(_labels) < ncols:
        for i in range(len(_labels), ncols):
            _labels.append("col%i" % (i+1))
    elif len(_labels) > ncols:
        _labels = _labels[:ncols]


    attrs = {'filename': filename}
    attrs['column_labels'] = attrs['array_labels'] = _labels
    if sort and sort_column >= 0 and sort_column < ncol:
         data = data[:, np.argsort(data[sort_column])]

    group = Group(name='ascii_file %s' % filename,
                  filename=filename, header=headers, data=data,
                  array_labels=_labels, column_labels=_labels)
    if len(footers) > 0:
        group.footer = footers
    for i in range(ncols):
        nam = _labels[i].lower()
        if nam in ('data', 'array_labels', 'filename',
                   'attrs', 'header', 'footer'):
            nam = "%s_" % nam
        setattr(group, nam, data[i])
    group.attrs = Group(name='header attributes from %s' % filename)
    for key, val in header_attrs.items():
        setattr(group.attrs, key, val)
    return group

@ValidateLarchPlugin
def write_ascii(filename, *args, **kws):
    """write a list of items to an ASCII column file

    write_ascii(filename, arg1, arg2, arg3, ... **args)

    arguments
    ---------
    commentchar: character for comment ('#')
    label:       array label line (autogenerated)
    header:      array of strings for header

    """
    ARRAY_MINLEN = 5
    _larch = kws['_larch']
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


    buff = []
    if header is None:
        buff = ['%s Output from Larch %s' % (com, time.ctime())]
    for s in header:
        buff.append('%s %s' % (com, s))
    buff.append('%s---------------------------------'% com)
    if label is None:
        label = '  '.join(['col%i' % (i+1) for i in range(len(arrays))])
    buff.append('#  %s' % label)

    arrays = np.array(arrays)
    for i in range(arraylen):
        w = [' % f' % val[i] for val in arrays]
        buff.append('  '.join(w))

    try:
        fout = open(filename, 'w')
    except:
        _larch.writer.write("cannot open file %s'" % filename)
        return

    try:
        fout.write('\n'.join(buff))
        fout.write('\n')
    except:
        _larch.writer.write("cannot write to file %s'" % filename)
        return

    _larch.writer.write("wrote to file '%s'\n" % filename)

@ValidateLarchPlugin
def write_group(filename, group, scalars=None,
                arrays=None, arrays_like=None,
                commentchar='#',  _larch=None):
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


@ValidateLarchPlugin
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

def registerLarchPlugin():
    return (MODNAME, {'read_ascii': read_ascii,
                      'guess_filereader': guess_filereader,
                      'write_ascii': write_ascii,
                      'write_group': write_group,
                     })
