#!/usr/bin/env python
__date__    = '2022-Jan-15'
__release_version__ = '0.9.58'
__authors__ = "M. Newville, M. Koker, B. Ravel, and others"

import sys
import numpy
import scipy
import matplotlib
import lmfit
from collections import OrderedDict, namedtuple
from packaging.version import parse as ver_parse
try:
    from importlib.metadata import version, PackageNotFoundError
except:
    from importlib_metadata import version, PackageNotFoundError
try:
    __version__ = version("xraylarch")
except PackageNotFoundError:
    # package is not installed
    __version__ = __release_version__

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

def version_data(mods=None):
    sysvers = sys.version
    if '\n' in sysvers:
        sysvers = sysvers.split('\n')[0]

    vdat = OrderedDict()
    vdat['larch'] = f'{__release_version__} ({__date__}) {__authors__}'
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
    if __version__ != __release_version__:
        lines.append(f'Devel Version: {__version__:s}')

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
    local_version = __release_version__

    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    try:
        req = requests.get(VERSION_URL, verify=False, timeout=3)
    except:
        return VersionStatus(False, local_version, 'unknown', 'offline')
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
    update_available = ver_parse(remote_version) > ver_parse(local_version)
    message = UPDATE_MESSAGE if update_available else LATEST_MESSAGE
    message = message.format(remote_version=remote_version,
                             local_version=local_version)
    return VersionStatus(update_available,local_version, remote_version, message)
