#!/usr/bin/env python
"""
  Larch column file reader: read_ascii
"""
import os
import time
import numpy as np
class Group:
    def __init__(self, **kws):
        for key, val in kws.items():
            setattr(self, key, val)

TINY = 1.e-7
MAX_FILESIZE = 100*1024*1024  # 100 Mb limit
COMMENTCHARS = '#;%*!$'

def getfloats(txt):
    words = [w.strip() for w in txt.replace(',', ' ').split()]
    try:
        return [float(w) for w in words]
    except:
        return None

def colname(txt):
    return txt.strip().lower().replace('.', '_')


def iso8601_time(ts):
    tzone = '-%2.2i:00' % (time.timezone/3600)
    s = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))
    return "%s%s" % (s, tzone)

def read_ascii(fname, labels=None, sort=False, sort_column=0, _larch=None):
    """read a column ascii column file, returning a group containing the data from the file.

    read_ascii(filename, labels=None, sort=False, sort_column=0)

    If the header is one of the forms of
        KEY : VAL
        KEY = VAL
    these will be parsed into a 'attrs' dictionary in the returned group.

    If labels is left the default value of None, column labels will be tried to
    be created from the line immediately preceeding the data, or using 'col1', 'col2',
    etc if column labels cannot be figured out.   The labels will be used to create
    1-d arrays for each column

    The group will have a 'data' component containing the 2-dimensional data, it will also
    have a 'header' component containing the text of the header -- an array of lines.
    If a footer (text after the block of numerical data) is in the file, the array of
    lines for this text will be put in the 'footer' component.

    """
    if not os.path.isfile(fname):
        raise OSError("File not found: '%s'" % fname)
    if os.stat(fname).st_size > MAX_FILESIZE:
        raise OSError("File '%s' too big for read_ascii()" % fname)

    finp = open(fname, 'r')
    text = finp.readlines()
    # text.append('')
    finp.close()

    _labelline, ncol = None, None
    data, footers, headers = [], [], []

    text.reverse()
    section = 'FOOTER'

    for line in text:
        line = line.strip()
        if len(line) < 1:
            continue
        # look for section transitions (going from bottom to top)
        if section == 'FOOTER' and getfloats(line) is not None:
            section = 'DATA'
        elif section == 'DATA' and getfloats(line) is None:
            section = 'HEADER'
            _labelline = line
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
    # set column labels
    _labels = ['col%i' % (i+1) for i in range(ncols)]
    if labels is None:
        if _labelline is None:
            _labelline = ' '.join(_labels)
        if _labelline[0] in COMMENTCHARS:
            _labelline = _labelline[1:].strip()
        _labelline = _labelline.lower()
        try:
            labels = [colname(l) for l in _labelline.split()]
        except:
            labels = []
    elif isinstance(labels, str):
        labels = labels.replace(',', ' ')
        labels = [colname(l) for l in labels.split()]

    for i, lab in enumerate(labels):
        try:
            _labels[i] = lab
        except:
            pass

    attrs = {'filename': fname}
    attrs['column_labels'] = _labels
    attrs['array_labels'] = _labels
    if sort and sort_column >= 0 and sort_column < nrow:
         data = data[:,np.argsort(data[sort_column])]

    group = Group(name='ascii_file %s' % fname,
                  filename=fname, header=headers,
                  column_labels=_labels,
                  array_labels=_labels,
                  data=data)
    if len(footers) > 0:
        group.footer = footers
    for i, nam in enumerate(_labels):
        setattr(group, nam.lower(), data[i])
    group.attrs = Group(name='header attributes from %s' % fname)
    for key, val in header_attrs.items():
        setattr(group.attrs, key, val)
    return group


def _read_ascii0(fname, commentchar='#;%', labels=None, sort=False, sort_column=0, _larch=None):
    """read a column ascii column file, returning a group containing the data from the file.

    read_ascii(filename, commentchar='$;%', labels=None, sort=False, sort_column=0)

    The commentchar argument (#;% by default) sets the valid comment characters:
    if the the first character in a line matches one of these, the line is marked
    as a  header lines.

    Header lines continue until a line with
       '#----' (any commentchar followed by 4 '-'
    The line immediately following that is read as column labels
    (space delimited)

    If the header is of the form
       # KEY : VAL   (ie commentchar key ':' value)
    these will be parsed into a 'attributes' dictionary
    in the returned group.

    If labels is left the default value of None, column labels will be used
    as the variable names. Variables from extra, unnamed columns will be
    called 'col1', 'col2'.

    If labels=False, the 'data' variable will contain the 2-dimensional data.

    """
    finp = open(fname, 'r')
    text = finp.readlines()
    finp.close()
    kws = {'filename': fname}
    _labels = None
    data = []
    header_txt = []
    header_kws = {}
    islabel = False
    for iline, line in enumerate(text):
        line = line[:-1].strip()
        if line[0] in commentchar:
            if islabel:
                _labels = line[1:].strip()
                islabel = False
            elif line[2:].strip().startswith('---'):
                islabel = True
            elif '=' in line[1:]: # perhaps '# x = 22' format?
                words = line[1:].split('=', 1)
                key = colname(words[0])
                if key.startswith('_'):
                    key = key[1:]
                if len(words) == 1:
                    header_txt.append(words[0].strip())
                else:
                    header_kws[key] = words[1].strip()
            elif ':' in line[1:]: # perhaps '# attribute: value' format?
                words = line[1:].split(':', 1)
                key = colname(words[0])
                if key.startswith('_'):
                    key = key[1:]
                if len(words) == 1:
                    header_txt.append(words[0].strip())
                else:
                    header_kws[key] = words[1].strip()
        else:
            words = line.replace(',', ' ').split()
            data.append([float(w) for w in words])


    if len(header_txt) > 0:
        header_kws['header'] = '\n'.join(header_txt)
    kws['attributes'] = header_kws
    kws['column_labels'] = []
    if labels is None:
        labels = _labels
    if labels is None:
        labels = header_txt.pop()
    data = np.array(data).transpose()
    ncol, nrow = data.shape
    if sort and sort_column >= 0 and sort_column < nrow:
        data = data[:,np.argsort(data[sort_column])]

    if not labels:
        kws['data'] = data
    else:
        try:
            labels = labels.replace(',', ' ').split()
        except:
            labels = []
        for icol in range(ncol):
            cname = 'col%i' % (1+icol)
            if icol < len(labels):
                cname = colname(labels[icol])
            kws[cname] = data[icol]
            kws['column_labels'].append(cname)

    group = kws
    if _larch is not None:
        group = _larch.symtable.create_group(name='ascii_file %s' % fname)
        atgrp = _larch.symtable.create_group(
            name='header attributes from %s' % fname)
        for key, val in kws['attributes'].items():
            setattr(atgrp, key, val)

        kws['attributes'] = atgrp
        for key, val in kws.items():
            setattr(group, key, val)
    return group
