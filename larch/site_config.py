#!/usr/bin/env python
"""
site configuration for larch:

   init_files:  list of larch files run (in order) on startup
   history_file:
"""
from __future__ import print_function

import sys
import os
import logging
import pkg_resources
from subprocess import check_call, CalledProcessError, TimeoutExpired

from .utils import (uname, get_homedir, nativepath, unixpath,
                    log_warning, log_error, version_ge)
from .version import __version__, __release_version__

larch_version = __version__
larch_release_version = __release_version__
# lists of recommended packages that are not installed by default
# but may be installed if several of the larch apps are run.
extras_wxgraph = {'wxutils': '0.3.0', 'wxmplot': '0.9.53'}
extras_epics =  {'pyepics': '3.5.0', 'epicsapps': None, 'psycopg2-binary':None}
extras_doc   = {'pytest': None, 'sphinx': None, 'numpydoc': None,
                'sphinxcontrib-bibtex': None, 'sphinxcontrib-argdoc': None}
extras_qtgraph = {'pyqt5': None, 'pyqtwebengine': None, 'pyqtgraph': None}
extras_plotly = {'plotly': None, 'jupyter': '5.0', 'ipywidgets': None}

def pjoin(*args):
    "simple join"
    return nativepath(os.path.join(*args))

def download_larch():
    check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'xraylarch'])

def update_larch():
    check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'xraylarch'])

def install_extras(package_dict, timeout=30):
    current = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    for pkg, vers in package_dict.items():
        install_needed = pkg not in current
        if pkg in current and vers is not None:
            install_needed = install_needed or version_ge(vers, current[pkg])

    if install_needed:
        command = [sys.executable, '-m', 'pip', 'install', f"{pkg}>={vers}"]
        try:
            check_call(command, timeout=timeout)
        except (CalledProcessError, TimeoutExpired):
            log_warning(f"could not pip install packages: {missing}")

##
# set system-wide and local larch folders
#   user_larchdir = get_homedir() + '.larch' (#unix)
#                 = get_homedir() + 'larch'  (#win)
##
home_dir = get_homedir()

here, i_am = os.path.split(__file__)
icondir = os.path.join(here, 'icons')

user_larchdir = pjoin(home_dir, '.larch')
if uname == 'win':
    user_larchdir = unixpath(pjoin(home_dir, 'larch'))

if 'LARCHDIR' in os.environ:
    user_larchdir = nativepath(os.environ['LARCHDIR'])

# on Linux, check for HOME/.local/share,
# make with mode=711 if needed
if uname in ('linux', 'darwin') and os.getuid() > 0:
    lshare = os.path.join(home_dir, '.local', 'share')
    if not os.path.exists(lshare):
        os.makedirs(lshare, mode=457) # for octal 711


# frozen executables, as from cx_freeze, will have
# these paths to be altered...
if hasattr(sys, 'frozen'):
    if uname.startswith('win'):
        try:
            tdir, exe = os.path.split(sys.executable)
            toplevel, bindir = os.path.split(tdir)
            larchdir = os.path.abspath(toplevel)
        except:
            pass
    elif uname.startswith('darwin'):
        tdir, exe = os.path.split(sys.executable)
        toplevel, bindir = os.path.split(tdir)
        larchdir = pjoin(toplevel, 'Resources', 'larch')


# initialization larch files to be run on startup
init_files = [pjoin(user_larchdir, 'init.lar')]

if 'LARCHSTARTUP' in os.environ:
    startup = os.environ['LARCHSTARTUP']
    if os.path.exists(startup):
        init_files = [nativepath(startup)]

# history file:
history_file = pjoin(user_larchdir, 'history.lar')

def make_user_larchdirs():
    """create user's larch directories"""
    files = {'init.lar':             'put custom startup larch commands:',
             'history.lar':          'history of larch commands:',
             'history_larchgui.lar': 'history of larch_gui commands:',
             }
    subdirs = {'matplotlib': 'matplotlib may put files here',
               'dlls':       'put dlls here',
               'feff':       'Feff files and folders here'}

    def make_dir(dname):
        "create directory"
        if not os.path.exists(dname):
            try:
                os.mkdir(dname)
            except PermissionError:
                log_warning(f'no permission to create directory {dname}')
            except (OSError, TypeError):
                log_error(sys.exc_info()[1])

    def write_file(fname, text):
        "write wrapper"
        if not os.path.exists(fname):
            try:
                with open(fname, 'w', encoding=sys.getdefaultencoding()) as fh:
                    fh.write(f'# {text}\n')
            except:
                log_error(sys.exc_info()[1])

    make_dir(user_larchdir)
    for fname, text in files.items():
        write_file(pjoin(user_larchdir, fname), text)

    for sdir, text in subdirs.items():
        sdir = pjoin(user_larchdir, sdir)
        make_dir(sdir)
        write_file(pjoin(sdir, 'README'), text)


def site_config():
    "retutn string of site config"
    isfrozen = getattr(sys, 'frozen', False)
    return f"""#== Larch Configuration:
  Release version:     {__release_version__}
  Development version: {__version__}
  Python executable:   {sys.executable}
  User larch dir:      {user_larchdir}
  User history_file:   {history_file}
#========================
"""

def show_site_config():
    print(site_config())

def system_settings():
    """set system-specific Environmental Variables, and make sure
    that the user larchdirs exist.
    This is run by the interpreter on startup."""
    # ubuntu / unity hack
    if uname.startswith('linux'):
        if 'ubuntu' in os.uname()[3].lower():
            os.environ['UBUNTU_MENUPROXY'] = '0'
    make_user_larchdirs()


if __name__ == '__main__':
    show_site_config()
