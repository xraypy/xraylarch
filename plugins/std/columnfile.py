import numpy
from larch.util import fixName

MODNAME = '_io'

def _read_ascii(fname, larch=None):
    """
    """
    kws = {}
    finp = open(fname, 'r')
    kws['filename'] = fname
    print(" READ ASCII " , fname)
    text = finp.readlines()
    finp.close()
    data = []
    header = []
    mode = 'Header'
    for line in text:
        line = line[:-1].strip()
        if mode == 'Label':
            words = line[1:].split()
            kws['labels'] = words
            mode = 'Data'
        elif mode == 'Data':
            words = line.split()
            data.append([float(w) for w in words])

        if line.startswith('#-----'):
            mode = 'Label'

        elif line.startswith('#'):
            words = line[1:].split(':', 1)
            print' === ', words
            key = fixName(words[0].strip())
            print words[0], key
            if len(words) == 1:
                header.append(words[0].strip())
            else:
                kws[key] = words[1].strip()

    data = numpy.array(data).transpose()
    kws['data'] = data
    kws['header'] = '\n'.join(header)
    group = larch.symtable.new_group(name='ascii_file %s' % fname)
    for key, val in kws.items():
        setattr(group, key, val)
    return group

def registerLarchPlugin():
    return (MODNAME, {'read_ascii': _read_ascii})


