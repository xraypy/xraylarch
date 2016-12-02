#!/usr/bin/env python
"""
site configuration for larch:

   init_files:  list of larch files run (in order) on startup
   module_path: list of directories to search for larch code
   history_file:
"""
from __future__ import print_function

import sys
import os
from os.path import exists, abspath, join
from .utils import get_homedir, nativepath
from .version import __version__ as larch_version

def pjoin(*args):
    return nativepath(join(*args))

##
# set system-wide and local larch folders
#   larchdir     = sys.exec_prefix + 'share' + 'larch'
#   usr_larchdir = get_homedir() + '.larch' (#unix)
#                = get_homedir() + 'larch'  (#win)
##

larchdir = pjoin(sys.exec_prefix, 'share', 'larch')
home_dir = get_homedir()

usr_larchdir = pjoin(home_dir, '.larch')
if os.name == 'nt':
    usr_larchdir = pjoin(home_dir, 'larch')

if 'LARCHDIR' in os.environ:
    usr_larchdir = nativepath(os.environ['LARCHDIR'])

##
## names (and loading order) for core plugin modules
core_plugins = ('std', 'math', 'io', 'wx', 'xray', 'xrf', 'xafs')

# frozen executables, as from cx_freeze, will have
# these paths to be altered...
if hasattr(sys, 'frozen'):
    if os.name == 'nt':
        try:
            tdir, exe = os.path.split(sys.executable)
            toplevel, bindir = os.path.split(tdir)
            larchdir = os.path.abspath(toplevel)
        except:
            pass

    elif sys.platform.lower().startswith('darwin'):
        tdir, exe = os.path.split(sys.executable)
        toplevel, bindir = os.path.split(tdir)
        larchdir = pjoin(toplevel, 'Resources', 'larch')

modules_path = []
plugins_path = []
_path = [usr_larchdir, larchdir]

if 'LARCHPATH' in os.environ:
    _path.extend([nativepath(s) for s in os.environ['LARCHPATH'].split(':')])

for pth in _path:
    mdir = pjoin(pth, 'modules')
    if exists(mdir) and mdir not in modules_path:
        modules_path.append(mdir)

    pdir = pjoin(pth, 'plugins')
    if exists(pdir) and pdir not in plugins_path:
        plugins_path.append(pdir)

# initialization larch files to be run on startup
init_files = [pjoin(usr_larchdir, 'init.lar')]

if 'LARCHSTARTUP' in os.environ:
    startup = os.environ['LARCHSTARTUP']
    if exists(startup):
        init_files = [nativepath(startup)]

# history file:
history_file = pjoin(usr_larchdir, 'history.lar')

def make_user_larchdirs():
    """create user's larch directories"""
    files = {'init.lar':             'put custom startup larch commands:',
             'history.lar':          'history of larch commands:',
             'history_larchgui.lar': 'history of larch_gui commands:',
             }
    subdirs = {'matplotlib': 'matplotlib may put files here',
               'dlls':       'put dlls here',
               'modules':    'put custom larch or python modules here',
               'plugins':    'put custom larch plugins here'}

    def make_dir(dname):
        if not exists(dname):
            try:
                os.mkdir(dname)
            except (OSError, TypeError):
                print(sys.exc_info()[1])

    def write_file(fname, text):
        if not exists(fname):
            try:
                f = open(fname, 'w')
                f.write('# %s\n' % text)
                f.close()
            except:
                print(sys.exc_info()[1])

    make_dir(usr_larchdir)
    for fname, text in files.items():
        write_file(pjoin(usr_larchdir, fname), text)

    for sdir, text in subdirs.items():
        sdir = pjoin(usr_larchdir, sdir)
        make_dir(sdir)
        write_file(pjoin(sdir, 'README'), text)

def show_site_config():
    print( """===  Larch Configuration
  larch version:        %s
  sys executable:       %s
  sys is frozen:        %s
  system larch dir:     %s
  users larch dir:      %s
  users history_file:   %s
  users startup files:  %s
  modules search path:  %s
  plugins search path:  %s
========================
""" % (larch_version, sys.executable,
       repr(getattr(sys, 'frozen', False)),
       larchdir, usr_larchdir,
       history_file, init_files,
       modules_path, plugins_path))

def system_settings():
    """set system-specific Environmental Variables, and make sure
    that the user larchdirs exist.
    This is run by the interpreter on startup."""
    # ubuntu / unity hack
    if sys.platform.lower().startswith('linux'):
        if 'ubuntu' in os.uname()[3].lower():
            os.environ['UBUNTU_MENUPROXY'] = '0'
    make_user_larchdirs()


if __name__ == '__main__':
    show_site_config()
