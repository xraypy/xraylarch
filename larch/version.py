#!/usr/bin/env python
__date__    = '2021-Jun-12'
__version__ = '0.9.52'
__authors__ = "M. Newville, M. Koker, B. Ravel, and others"

import sys
import numpy
import scipy
import matplotlib
import lmfit
from collections import OrderedDict, namedtuple
from packaging.version import parse as ver_parse
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

def version_data(mods=None):
    sysvers = sys.version
    if '\n' in sysvers:
        sysvers = sysvers.split('\n')[0]

    vdat = OrderedDict()
    vdat['larch'] = "%s (%s) %s" % (__version__, __date__, __authors__)
    vdat['python'] = "%s" % (sysvers)

    allmods = [numpy, scipy, matplotlib, lmfit]
    if mods is not None:
        for m in mods:
            if m not in allmods:
                allmods.append(m)

    for mod in allmods:
        if mod is not None:
            mname = mod.__name__
            try:
                vers = mod.__version__
            except:
                vers = "unavailable"
            vdat[mname] = vers
    return vdat

def make_banner(mods=None):
    vdat = version_data(mods=mods)

    lines = ['Larch %s' % vdat.pop('larch'),
             'Python %s' % vdat.pop('python')]

    reqs = []
    for name, vstr in vdat.items():
        reqs.append('%s %s' % (name, vstr))
    lines.append(', '.join(reqs))

    linelen = max([len(line) for line in lines])
    border = '='*max(linelen, 75)
    lines.insert(0, border)
    lines.append(border)

    return '\n'.join(lines)


########
## for comparing current with remote version
########
VERSION_URL='https://raw.githubusercontent.com/xraypy/xraylarch/gh-pages/version.txt'

VersionStatus = namedtuple('VersionStatus', ('update_available',
                                             'local_version',
                                             'remote_version',
                                             'message'))

UPDATE_MESSAGE = """#=== Update Available ===
Larch version {remote_version:s} is available. Your version is currently {local_version:s}.
To update the latest version run
   larch -u
from a Command Window or Terminal.
#========================"""

LATEST_MESSAGE = """Larch version {local_version:s} is up to date."""

def check_larchversion():
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    req = requests.get(VERSION_URL, verify=False, timeout=5)
    remote_version = '0.9.001'
    if req.status_code == 200:
        try:
            for line in req.text.split('\n'):
                line = line.strip()
                if not line.startswith('#'):
                    remote_version = line
                    break
        except:
            pass
    local_version = __version__
    update_available = ver_parse(remote_version) > ver_parse(local_version)
    message = UPDATE_MESSAGE if update_available else LATEST_MESSAGE
    message = message.format(remote_version=remote_version,
                             local_version=local_version)
    return VersionStatus(update_available,local_version, remote_version, message)
