import os
from datetime import datetime
from collections import namedtuple

FPathInfo = namedtuple('FeffPathInfo',
                       ('filename', 'absorber', 'shell', 'reff', 'nleg',
                        'degen', 'cwratio', 'geom'))
class FeffCalcResults:
    def __init__(self, folder=None, header=None, ipots=None,
                 paths=None, datetime=None, absorber=None,
                 shell=None, input_text=None):
        self.folder = folder
        self.header = header
        self.ipots = ipots
        self.paths = paths
        self.datetime = datetime
        self.absorber = absorber
        self.shell = shell
        self.input_text = input_text

    def __getstate__(self):
        """Get state for pickle."""
        return (self.folder, self.absorber, self.shell, self.header,
                self.ipots, self.paths, self.datetime, self.input_text)

    def __setstate__(self, state):
        """Set state from pickle."""
        (self.folder, self.absorber, self.shell, self.header,
         self.ipots, self.paths, self.datetime, self.input_text) = state


def get_feff_pathinfo(folder):
    """get list of Feff path info for a Feff folder
    """
    fdat = os.path.join(folder, 'files.dat')
    pdat = os.path.join(folder, 'paths.dat')
    f001 = os.path.join(folder, 'feff0001.dat')
    finp = os.path.join(folder, 'feff.inp')

    # check for valid, complete calculation
    if (not os.path.exists(fdat) or not os.path.exists(pdat) or
        not os.path.exists(f001) or not os.path.exists(finp)):
        return FeffCalcResults(os.path.abspath(folder), absorber=None,
                               shell=None, ipots=[], header='',
                               paths=[], datetime=None)


    dtime = datetime.fromtimestamp(os.stat(fdat).st_mtime).isoformat()
    with open(fdat, 'r') as fh:
        fdatlines = fh.readlines()

    with open(pdat, 'r') as fh:
        pathslines = fh.readlines()

    paths = {}
    header = []
    shell = 'K'
    waiting_for_dashes = True
    for xline in fdatlines:
        xline = xline.strip()
        if xline.startswith('----'):
            waiting_for_dashes = False
        if waiting_for_dashes:
            header.append(xline)

            if (xline.startswith('Abs ') and 'Rmt=' in xline and
                'Rnm=' in xline and 'shell' in xline):
                words = xline.replace('shell', '').strip().split()
                shell = words[-1]
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
                                absorber=absorber,
                                shell=shell,
                                reff=float(pinfo[1]),
                                nleg=int(float(pinfo[2])),
                                degen=float(pinfo[3]),
                                cwratio=float(pinfo[4]),
                                geom=geom))

    # read absorbing shell
    for line in header:
        line = line.strip()

    # read input
    try:
        input_text = open(finp, 'rb').read().decode('utf-8')
    except:
        input_text = '<not available>'

    return FeffCalcResults(os.path.abspath(folder),
                           absorber=absorber,
                           shell=shell,
                           ipots=ipots,
                           header='\n'.join(header),
                           paths=opaths,
                           input_text=input_text,
                           datetime=dtime)
