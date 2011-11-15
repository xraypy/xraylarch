import numpy
from larch.util import fixName

MODNAME = '_io'

def _read_ascii(fname, delim='#;*%', use_labels=True, larch=None):
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

    If use_labels=True and the column labels can be used as the
    variable names, they will be.  Variables from extra columns
    will be called 'col1', 'col2'.

    If use_labels=False, the 'data' variable will contain the
    2-dimensional data.   
        """
    kws = {}
    finp = open(fname, 'r')
    kws['filename'] = fname
    text = finp.readlines()
    finp.close()
    data = []
    header_txt = []
    header_kws = {}
    mode = 'Header'
    for line in text:
        line = line[:-1].strip()
        isheader = line[0] in delim
        if mode == 'Label':
            kws['column_labels'] = [u.lower() for u in line[1:].split()]
            mode = 'Data'
        elif mode == 'Data':
            words = line.split()
            data.append([float(w) for w in words])

        if isheader and line[1:].startswith('-----'):
            mode = 'Label'

        elif isheader:
            words = line[1:].split(':', 1)
            key = fixName(words[0].strip())
            if key.startswith('_'):
                key = key[1:]
            if len(words) == 1:
                header_txt.append(words[0].strip())
            else:
                header_kws[key] = words[1].strip()

    data = numpy.array(data).transpose()
    kws['header'] = '\n'.join(header_txt)
    kws['attributes'] = header_kws

    if use_labels:
        labels = kws['column_labels']
        for icol, col in enumerate(labels):
            kws[fixName(col.strip().lower())] = data[icol]
            if data.shape[0] >  len(labels):
                for icol in range(data.shape[0] - len(labels)):
                    colname = 'col%i' % (1+len(labels)+icol)
                    kws[colname] = data[icol]
                    kws['column_labels'].append(colname)
    else:
        kws['data'] = data
    group = larch.symtable.new_group(name='ascii_file %s' % fname)
    for key, val in kws.items():
        setattr(group, key, val)
    return group

def registerLarchPlugin():
    return (MODNAME, {'read_ascii': _read_ascii})


