MODNAME = '_io'

def read_ascii(fname, larch=None):
    finp = open(fname, 'r')
    kw['filename'] = fname
    text = finp.readlines()
    finp.close()
    data = []
    header = []
    mode = 'Header'
    for line in text:
        line = line[:-1].strip()
        if mode == 'Data':
            words = line.split(' ')
            data.append(words)
        if line.startswith('#-----'):
            mode = 'Data'
        elif line.startswith('#'):
            words = line[1:].split(':', 1)
            if len(words) == 1:
                header.append(words[0].strip())
            else:
                kw[words[0].strip()] = words[1].strip()
    kw['data'] = numpy.array(data)

    group = larch.symtable.create_group()
    for key, val in kws.items():
        setattr(group, key, val)
    return group

def registerLarchPlugin():
    return (MODNAME, {'read_ascii': _read_ascii})


