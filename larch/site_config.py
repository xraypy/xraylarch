#!/usr/bin/env python
"""
site configuration for larch:

   init_files:  list of larch files run (in order) on startup
   history_file:
"""
import sys
import os
from pathlib import Path

from subprocess import check_call, CalledProcessError, TimeoutExpired

from packaging.version import parse as version_parse

from .utils import (uname, get_homedir, log_warning, log_error)
from .version import __version__, __release_version__

larch_version = __version__
larch_release_version = __release_version__

# lists of recommended packages that are not installed by default
# but may be installed if several of the larch apps are run.

def pjoin(*args):
    "simple join"
    return Path(*args).absolute().as_posix()

def update_larch(with_larix=True):
    "pip upgrade larch"
    target = 'xraylarch'
    if with_larix:
        target = 'xraylarch[larix]'
    check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', target])

#                 = get_homedir() + 'larch'  (#win)
home_dir = get_homedir()

icondir = Path(Path(__file__).parent, 'icons').absolute()

user_larchdir = pjoin(home_dir, '.larch')

if 'LARCHDIR' in os.environ:
    user_larchdir = Path(os.environ['LARCHDIR']).absolute().as_posix()

# on Linux, check for HOME/.local/share,
# make with mode=711 if needed
if uname in ('linux', 'darwin') and os.getuid() > 0:
    lshare = Path(home_dir, '.local', 'share').absolute()
    lshare.mkdir(mode=457, parents=True, exist_ok=True) # for octal 711


# initialization larch files to be run on startup
init_files = [pjoin(user_larchdir, 'init.lar')]

if 'LARCHSTARTUP' in os.environ:
    startup = Path(os.environ['LARCHSTARTUP'])
    if startup.exists():
        init_files = [startup.as_posix()]

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
        dname = Path(dname).absolute()
        if not dname.exists():
            try:
                dname.mkdir(mode=493, parents=True)
            except PermissionError:
                log_warning(f'no permission to create directory {dname.as_posix()}')
            except (OSError, TypeError):
                log_error(sys.exc_info()[1])

    def write_file(fname, text):
        "write wrapper"
        if not Path(fname).exists():
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
