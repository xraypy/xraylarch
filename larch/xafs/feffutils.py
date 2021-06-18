import os
from datetime import datetime
from collections import namedtuple

FPathInfo = namedtuple('FeffPathInfo',
                       ('filename', 'reff', 'nleg',
                        'degeneracy', 'cwratio', 'geom'))
class FeffCalcResults:
    def __init__(self, folder, header=None, ipots=None,
                 paths=None, datetime=None, absorber=None,
                 edge=None):
        self.folder = folder
        self.header = header
        self.ipots = ipots
        self.paths = paths
        self.datetime = datetime
        self.absorber = absorber
        self.edge = edge
                          
def get_feff_pathinfo(folder):
    """get list of Feff path info for a Feff folder
    """
    
    fdat = os.path.join(folder, 'files.dat')
    pdat = os.path.join(folder, 'paths.dat')
    if not os.path.exists(fdat) or not os.path.exists(pdat):
        raise ValueError(f'{folder:s} is not a complete Feff folder - run feff?')

    dtime = datetime.fromtimestamp(os.stat(fdat).st_mtime).isoformat()
    with open(fdat, 'r') as fh:
        fdatlines = fh.readlines()

    with open(pdat, 'r') as fh:
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
            w = xline.split()
            index = int(w[0].replace('feff', '').replace('.dat', ''))
            paths[index] = [w[0], w[5], w[4], w[3], w[2]]

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
    absorber = ipots[0]
    ipots[0] = '[%s]' % ipots[0]
    opaths = []
    for pindex, pinfo in paths.items():
        pots = [0] + pinfo[5]
        geom =  ' > '.join([ipots[i] for i in pots])
        opaths.append(FPathInfo(filename=pinfo[0],
                                reff=float(pinfo[1]),
                                nleg=int(float(pinfo[2])),
                                degeneracy=float(pinfo[3]),
                                cwratio=float(pinfo[4]),
                                geom=geom))

    # read absorbing shell
    for line in header:
        line = line.strip()
        if (line.startswith('Abs ') and 'Rmt=' in line
            and 'Rnm=' in line and 'shell' in line):
            words= line.replace('shell', '').strip().split()
            edge = words[-1]
        
    return FeffCalcResults(os.path.abspath(folder),
                           absorber=absorber,
                           edge=edge,
                           ipots=ipots,
                           header='\n'.join(header),
                           paths=opaths,
                           datetime=dtime)
