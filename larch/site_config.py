#!/usr/bin/env python
"""
site configuration for larch:

   init_files:  list of larch files run (in order) on startup
   history_file:
"""
import sys
import os
import importlib.metadata
from subprocess import check_call, CalledProcessError, TimeoutExpired

from packaging.version import parse as version_parse

from .utils import (uname, get_homedir, nativepath, unixpath,
                    log_warning, log_error)
from .version import __version__, __release_version__

larch_version = __version__
larch_release_version = __release_version__

# lists of recommended packages that are not installed by default
# but may be installed if several of the larch apps are run.

extras_wxgraph = {'wxutils': '0.3.0', 'wxmplot': '0.9.56'}
extras_epics =  {'pyepics': '3.5.1', 'epicsapps': None, 'psycopg2-binary':None}
extras_doc   = {'pytest': None, 'sphinx': None, 'numpydoc': None,
                'sphinxcontrib-bibtex': None, 'sphinxcontrib-argdoc': None}
extras_qtgraph = {'pyqt5': None, 'pyqtwebengine': None, 'pyqtgraph': None}
extras_plotly = {'plotly': None, 'jupyter': '5.0', 'ipywidgets': None}
extras_pymatgen = {'mp_api': None, 'pandas': None, 'py3Dmol': None}


def pjoin(*args):
    "simple join"
    return nativepath(os.path.join(*args))

def update_larch():
    "pip upgrade larch"
    check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'xraylarch'])

def install_extras(package_dict, timeout=30):
    "install extra packages"
    for pkg, vers_required in package_dict.items():
        try:
            vers_installed = importlib.metadata.distribution(pkg).version
        except:
            vers_installed = None
        do_install = vers_installed is None
        if vers_installed is not None and vers_required is not None:
            do_install = (version_parse(vers_installed) <
                          version_parse(vers_required))
        if do_install:
            command = [sys.executable, '-m', 'pip', 'install', f"{pkg}>={vers_required}"]
            try:
                check_call(command, timeout=timeout)
            except (CalledProcessError, TimeoutExpired):
                log_warning(f"could not pip install packages: {pkg}")
#
# set system-wide and local larch folders
#   user_larchdir = get_homedir() + '.larch' (#unix)
#                 = get_homedir() + 'larch'  (#win)
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
             'history.lar':          'history of commands for larch CLI',
             'history_larchgui.lar': 'history of commands for larch GUI',
             }
    subdirs = {'matplotlib': 'matplotlib may put cache files here',
               'feff':       'Feff files and subfolders here',
               'fdmnes':     'FDMNES files and subfolders here',
               }

    def make_dir(dname):
        "create directory"
        if not os.path.exists(dname):
            try:
                os.mkdir(dname, mode=493)
            except PermissionError:
                log_warning(f'no permission to create directory {dname}')
            except (OSError, TypeError):
                log_error(sys.exc_info()[1])

    def write_file(fname, text):
        "write wrapper"
        if not os.path.exists(fname):
            try:
                with open(fname, 'w', encoding=sys.getdefaultencoding()) as fileh:
                    fileh.write(f'# {text}\n')
            except IOError:
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
    return f"""#== Larch Configuration:
  Release version:     {__release_version__}
  Development version: {__version__}
  Python executable:   {sys.executable}
  User larch dir:      {user_larchdir}
  User history_file:   {history_file}
#========================
"""

def show_site_config():
    "print stie_config"
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
