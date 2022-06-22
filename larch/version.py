#!/usr/bin/env python
"""Version information"""
__date__    = '2022-Jun-21'
__release_version__ = '0.9.64'
__authors__ = "M. Newville, M. Koker, M. Rovezzi, B. Ravel, and others"

import sys
from collections import OrderedDict, namedtuple
from packaging.version import parse as ver_parse

import urllib3
import requests
import numpy
import scipy
import matplotlib
import lmfit

try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError
try:
    __version__ = version("xraylarch")
except PackageNotFoundError:
    # package is not installed
    __version__ = __release_version__

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def version_data(mods=None):
    "get version data"
    sysvers = sys.version
    if '\n' in sysvers:
        sysvers = sysvers.split('\n', maxsplit=1)[0]

    vdat = OrderedDict()
    vdat['larch'] = f'{__release_version__} ({__date__}) {__authors__}'
    vdat['python'] = sysvers

    allmods = [numpy, scipy, matplotlib, lmfit]
    if mods is not None:
        for mod in mods:
            if mod not in allmods:
                allmods.append(mod)

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
    "return startup banner"
    vdat = version_data(mods=mods)
    _lvers = vdat.pop('larch')
    _pvers = vdat.pop('python')
    lines = [f'Larch {_lvers}', f'Python {_pvers}']

    reqs = []
    for name, vstr in vdat.items():
        reqs.append(f'{name} {vstr}')
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
    "check version, return VersionStatus tuple"
    local_version = __release_version__

    try:
        req = requests.get(VERSION_URL, verify=False, timeout=3.10)
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
