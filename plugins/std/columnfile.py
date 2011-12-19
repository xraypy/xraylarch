#!/usr/bin/env python
"""
  Larch column file reader: read_ascii)_
"""

import numpy
from larch.util import fixName

MODNAME = '_io'

def _read_ascii(fname, delim='#;*%', labels=None, larch=None):
    """read a column ascii column file.
    The delim argument (#;* by default) sets the first character
    to mark the header lines.

    Header lines continue until a line with
       '#----' (any delimiter followed by 4 '-'
    The line immediately following that is read as column labels
    (space delimited)

    If the header is of the form
       # KEY : VAL   (ie delimiter, key ':' value)
    these will be parsed into a 'attributes' dictionary
    in the returned group.

    If labels is left the default value of None, column labels will be used
    as the variable names. Variables from extra, unnamed columns will be
    called 'col1', 'col2'.

    If labels=False, the 'data' variable will contain the 2-dimensional data.
    """
    finp = open(fname, 'r')
    kws = {'filename': fname}
    _labels = None
    text = finp.readlines()
    finp.close()
    data = []
    header_txt = []
    header_kws = {}
    islabel = False
    for iline, line in enumerate(text):
        line = line[:-1].strip()
        if line[0] in delim:
            if islabel:
                _labels = line[1:].strip()
                islabel = False
            elif line[2:].strip().startswith('---'):
                islabel = True
            else:
                words = line[1:].split(':', 1)
                key = fixName(words[0].strip())
                if key.startswith('_'):
                    key = key[1:]
                if len(words) == 1:
                    header_txt.append(words[0].strip())
                else:
                    header_kws[key] = words[1].strip()
        else:
            words = line.split()
            data.append([float(w) for w in words])


    kws['header'] = '\n'.join(header_txt)
    kws['attributes'] = header_kws
    if labels is None:
        labels = _labels
    if labels is None:
        labels = header_txt.pop()

    data = numpy.array(data).transpose()
    if not labels:
        kws['data'] = data
    else:
        try:
            labels = labels.replace(',', ' ').split()
        except:
            labels = []
        for icol, col in enumerate(labels):
            kws[fixName(col.strip().lower())] = data[icol]
            if data.shape[0] >  len(labels):
                for icol in range(data.shape[0] - len(labels)):
                    colname = 'col%i' % (1+len(labels)+icol)
                    kws[colname] = data[icol]
                    kws['column_labels'].append(colname)

    group = larch.symtable.new_group(name='ascii_file %s' % fname)
    for key, val in kws.items():
        setattr(group, key, val)
    return group

def registerLarchPlugin():
    return (MODNAME, {'read_ascii': _read_ascii})


