#!/usr/bin/env python
"""
site configuration for larch:

   init_files:  list of larch files run (in order) on startup
   module_path: list of directories to search for larch code
   history_file:
"""
from __future__ import print_function

import os
import sys
from . import site_configdata

def unixdir(f):
    return f.replace('\\', '/')

def join(*args):
    return unixdir(os.path.join(*args))

exists = os.path.exists
abspath = os.path.abspath
curdir = abspath('.')

def get_homedir():
    "determine home directory"
    def check(method, s):
        try:
            if method(s) not in (None, s):
                return method(s)
        except KeyError:
            print('error looking up %s' % s)
            print(sys.exc_info[1])
        return None

    home_dir = check(os.path.expanduser, '~')
    if home_dir is not None:
        for var in ('$HOME', '$USERPROFILE', '$ALLUSERSPROFILE', '$HOMEPATH'):
            home_dir = check(os.path.expandvars, var)
            if home_dir is not None: break

    if home_dir is None:
        home_dir = os.path.abspath('.')
    return unixdir(home_dir)


# general-use system path
sys_larchdir = site_configdata.unix_installdir
usr_larchdir = site_configdata.unix_userdir

# windows
if os.name == 'nt':
    sys_larchdir = unixdir(site_configdata.win_installdir)
    usr_larchdir = unixdir(site_configdata.win_userdir)


home_dir = get_homedir()

def make_larch_userdirs():
    "create users .larch directories"
    files = {'init.lar': '# put startup larch commands here\n',
             'history.lar': '# history of larch commands will be placed here\n'}
    subdirs = {'matplotlib': '# matplotlib may put files here...\n',
               'modules':    '# put custom larch or python modules here \n',
               'plugins':    '# put larch plugins here \n'}

    def make_dir(dname):
        if exists(dname): return True
        try:
            os.mkdir(dname)
            return True
        except OSError:
            print('Error trying to create %s' % dname)
            print(sys.exc_info()[1])
        except TypeError:
            print('Error trying to create %s' % dname)
            print(sys.exc_info()[1])
        return False

    def write_file(fname, text):
        if os.path.exists(fname):
            return True
        try:
            f = open(fname, 'w')
            f.write(text)
            f.close()
            return True
        except:
            print('Error trying to open %s' % fname)
            print(sys.exc_info()[1])
        return False

    user_dir = abspath(join(home_dir, usr_larchdir))
    if not make_dir(user_dir):

        return
    for fname, text in files.items():
        fname = join(user_dir, fname)
        write_file(fname, text)
    for sdir, text in subdirs.items():
        sdir = join(user_dir, sdir)
        if not make_dir(sdir):
            break
        fname = join(sdir, 'README')
        write_file(fname, text)


if 'LARCHDIR' in os.environ:
    usr_larchdir = unixdir(os.environ['LARCHDIR'])
else:
    usr_larchdir = unixdir(abspath(join(home_dir, usr_larchdir)))

# modules_path, plugins_path
#  determine the search path for modules

modules_path, plugins_path = [], []
modpath = []

if 'LARCHPATH' in os.environ:
    modpath.extend([unixdir(s) for s in os.environ['LARCHPATH'].split(':')])
else:
    modpath.append(unixdir(usr_larchdir))

modpath.append(sys_larchdir)

for mp in modpath:
    mdir = join(mp, 'modules')
    if exists(mdir) and mdir not in modules_path:
        modules_path.append(mdir)

for mp in (usr_larchdir, sys_larchdir):
    mdir = join(mp, 'plugins')
    if exists(mdir) and mdir not in plugins_path:
        plugins_path.append(mdir)

# initialization larch files to be run on startup
init_files = []
for folder in (sys_larchdir, usr_larchdir):
    ifile = join(folder, 'init.lar')
    if exists(ifile):
        init_files.append(ifile)

if 'LARCHSTARTUP' in os.environ:
    startup = os.environ['LARCHSTARTUP']
    if exists(startup):
        init_files.append(unixdir(startup))

# history file:
history_file = join(home_dir, '.larch_history')
if exists(usr_larchdir) and os.path.isdir(usr_larchdir):
    history_file = join(usr_larchdir, 'history.lar')

def show_site_config():
    print( """===  Larch Configuration
  users home directory: %s
  users larch dir:      %s
  users history_file:   %s
  users startup files:  %s
  modules search path:  %s
  plugins search path:  %s
========================
""" % (home_dir, usr_larchdir, history_file, init_files,
       modules_path, plugins_path))

def system_settings():
    """set system-specific settings, such as
    Environmental Variables.

    This is run by the interpreter on startup."""
    # ubuntu / unity hack
    if sys.platform.lower().startswith('linux'):
        if 'ubuntu' in os.uname()[3].lower():
            os.environ['UBUNTU_MENUPROXY'] = '0'

if __name__ == '__main__':
    show_site_config()
