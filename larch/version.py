#!/usr/bin/env python
"""Version information"""
__date__    = '2022-Dec-20'
__release_version__ = '0.9.66'
__authors__ = "M. Newville, M. Koker, M. Rovezzi, B. Ravel, and others"
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

def version_data():
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

    vdat = {}
    vdat['larch'] = f'{__release_version__}, released {__date__}'
    vdat['python'] = f'{pyvers}, {builder:s}'

    return vdat

def make_banner(mods=None):
    "return startup banner"
    vdat = version_data()
    lines = [f"Larch {vdat['larch']}"]
    if __version__ != __release_version__:
        lines.append(f'Devel Version: {__version__:s}')
    lines.append(f"Python {vdat['python']}")
    lines.append('use `print(show_version())` for version details')
    linelen = max([len(line) for line in lines])
    border = '='*min(75, max(linelen, 25))
    lines.insert(0, border)
    lines.append(border)
    return '\n'.join(lines)


def show_version():
    vinf  = sys.version_info
    pyvers = f'{vinf.major:d}.{vinf.minor:d}.{vinf.micro:d}'
    out = [f'Larch release version {__release_version__}',
           f'Larch develop version {__version__}',
           f'Larch release date    {__date__}',
           f'Larch authors         {__authors__}',
           f'Python version        {pyvers}',
           f'Python full version   {sys.version}']

    for modname in ('numpy', 'scipy', 'matplotlib', 'h5py', 'sklearn',
                    'skimage', 'fabio', 'pyFAI', 'PIL', 'imageio',
                    'silx', 'tomopy', 'pymatgen.core', 'numdifftools',
                    'xraydb', 'lmfit', 'asteval', 'wx', 'wxmplot'):

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
        out.append(f'{modname:20s}  {vers}')
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
