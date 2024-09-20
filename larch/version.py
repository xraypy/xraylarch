#!/usr/bin/env python
"""Version information"""

__release_version__ = '0.9.81'
__date__    = '2024-September-20'
__authors__ = "M. Newville, M. Rovezzi, M. Koker, B. Ravel, and others"

from ._version import __version__, __version_tuple__

import sys
from collections import namedtuple
from packaging.version import parse as ver_parse
import importlib
import urllib3
import requests
import numpy
import scipy
import matplotlib
import lmfit

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# libraries whose versions might be interesting to know
LIBS_VERSIONS = ('numpy', 'scipy', 'matplotlib', 'h5py', 'sklearn', 'skimage',
                 'sqlalchemy', 'fabio', 'pyFAI', 'PIL', 'imageio', 'silx',
                 'tomopy', 'pymatgen.core', 'numdifftools', 'xraydb', 'lmfit',
                 'asteval', 'wx', 'wxmplot')

def version_data(with_libraries=False):
    "get version data"
    vinf  = sys.version_info
    pyvers = f'{vinf.major:d}.{vinf.minor:d}.{vinf.micro:d}'

    buildinfo = sys.version
    if '\n' in buildinfo:
        buildinfo = buildinfo.split('\n', maxsplit=1)[0].strip()
    if buildinfo.startswith(pyvers):
        buildinfo = buildinfo.replace(pyvers, '').strip()

    builder = buildinfo[:40]
    if '|' in buildinfo:
        sects = buildinfo.split('|')
        if len(sects) > 1:
            builder = sects[1].strip()

    vdat = {'release version': __release_version__,
            'release date':  __date__,
            'development version':  __version__,
            'authors': __authors__,
            'python version': pyvers,
            'python builder': builder,
            'python sysversion': sys.version,
            }

    if with_libraries:
        for modname in LIBS_VERSIONS:
            vers = "not installed"
            if modname not in sys.modules:
                try:
                    importlib.import_module(modname)
                except:
                    pass
            if modname in sys.modules:
                mod = sys.modules[modname]
                vers = getattr(mod, '__version__', None)
                if vers is None:
                    vers = getattr(mod, 'version',
                                   'unknown version')
            vdat[modname] = vers
    return vdat

def make_banner(with_libraries=False, show_libraries=None):
    "return startup banner"
    if show_libraries is None:
        show_libraries = LIBS_VERSIONS if with_libraries else []

    vdat = version_data(with_libraries=True)
    lines = [f"Larch {vdat['release version']}, released {vdat['release date']}"]
    if vdat['development version'] != vdat['release version']:
        lines.append(f"development version: {vdat['development version']}")
    lines.append(f"Python {vdat['python version']}, {vdat['python builder']}")
    libline = []
    for key, val in vdat.items():
        if key in show_libraries:
            libline.append(f"{key:s}: {val}")
            if len(libline) > 3:
                lines.append(', '.join(libline))
                libline = []
    if len(libline) > 0:
        lines.append(', '.join(libline))

    if len(show_libraries) < 10:
        lines.append('use `print(show_version())` for detailed versions')

    linelen = max([len(line) for line in lines])
    border = '='*min(99, max(linelen, 25))
    lines.insert(0, border)
    lines.append(border)
    return '\n'.join(lines)

def show_version():
    vdat = version_data(with_libraries=True)
    out = []
    for key, val in vdat.items():
        out.append(f"{key:20s}:  {val}")
    return '\n'.join(out)


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
