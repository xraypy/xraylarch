import os
from datetime import datetime
from collections import namedtuple

FeffPathInfo = namedtuple('FeffPathInfo',
                          ('filename', 'reff', 'degeneracy',
                           'nleg', 'zabinsky', 'geom'))

class FeffResults:
    def __init__(self, folder, header=None, ipots=None, paths=None,
                 date=None):
        self.folder = folder
        self.header = header
        self.ipots = ipots
        self.paths = paths
        self.date = date

                          
def get_feffpathinfo(folder):
    """get list of Feff path info for a Feff folder
    """
    
    fdat = os.path.join(folder, 'files.dat')
    if not os.path.exists(fdat):
        raise ValueError(f'{folder:s} is not a complete Feff folder - run feff?')


    dtime = datetime.fromtimestamp(os.stat('files.dat').st_mtime).isoformat()
    with open(os.path.join(folder, 'files.dat'), 'r') as fh:
        fdatlines = fh.readlines()

    with open(os.path.join(folder, 'paths.dat'), 'r') as fh:
        pathslines = fh.readlines()
    
    paths = {}
    header = []
    waiting_for_dashes = True
    for xline in fdatlines:
        xline = xline.strip()
        if xline.startswith('----'):
            waiting_for_dashes = False
        if waiting_for_dashes:
            header.append(xline)
            continue
        if xline.startswith('feff0'):
            words = xline.split()
            index = int(words[0].replace('feff', '').replace('.dat', ''))
            paths[index] = [words[0], words[5], words[4], words[3], words[2]]

    ipots = ['']*12
    waiting_for_dashes = True
    for i, xline in enumerate(pathslines):
        xline = xline.strip()
        if xline.startswith('----'):
            waiting_for_dashes = False
        if waiting_for_dashes:
            continue
        if 'index, nleg' in xline:
            words = xline.split()
            index = int(words[0])
            nleg  = int(words[1])
            elems = []
            for j in range(nleg+1):
                xline = pathslines[j+i+1].strip().replace("'", '')
                if xline.startswith('x   '):
                    continue
                words = xline.split()[:-3]
                ipot = int(words[3])

                if ipot not in ipots:
                    ipots[ipot] = ' '.join(words[4:])
                elems.append(ipot)
            if index in paths:
                paths[index].append(elems)

   
    ipots = [i for i in ipots if len(i) > 0]
    ipots[0] = '[%s]' % ipots[0]
    opaths = []
    for pindex, pinfo in paths.items():
        pots = [0] + pinfo[5]
        geom =  ' -> '.join([ipots[i] for i in pots])
        opaths.append(FeffPathInfo(filename=pinfo[0],
                                   reff=float(pinfo[1]),
                                   nleg=int(float(pinfo[2])),
                                   degeneracy=float(pinfo[3]),
                                   zabinsky=float(pinfo[4]),
                                   geom=geom))

    return FeffResults(folder, ipots=ipots,
                       header='\n'.join(header),
                       paths=opaths, date=dtime)

if __name__ == '__main__':
    ret = get_feffpathinfo('/Users/Newville/.larch/feff/Cu1_K_Cuprite_cif9326')
    print(ret.folder)
    print(ret.ipots)
    print(ret.date)
    print(ret.header)
    for  p in ret.paths:
        print(p)
    
