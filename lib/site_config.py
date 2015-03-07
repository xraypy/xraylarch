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

def windir(d):
    "ensure path uses windows delimiters"
    if d.startswith('//'): d = d[1:]
    d = d.replace('/','\\')
    return d

def nativedir(d):
    "ensure path uses delimiters for current OS"
    if os.name == 'nt':
        return windir(d)
    return unixdir(d)

def join(*args):
    return nativedir(os.path.join(*args))

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
    return nativedir(home_dir)

# set larch install directories
# on unix, these would be
#   larchdir =  $USER/.larch
#
# on windows, these would be
#   larchdir = $USER/larch

larchdir = site_configdata.larchdir
if os.name == 'nt' and larchdir.startswith('.'):
    larchdir = larchdir[1:]

home_dir = get_homedir()
larchdir = join(home_dir, larchdir)

if 'LARCHDIR' in os.environ:
    larchdir = nativedir(os.environ['LARCHDIR'])
else:
    larchdir = nativedir(abspath(join(home_dir, larchdir)))

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
        larchdir = join(toplevel, 'Resources', 'larch')


def make_larchdirs():
    "create users .larch directories"
    files = {'init.lar': '# put startup larch commands here\n',
             'history.lar': '# history of larch commands will be placed here\n'}
    subdirs = {'matplotlib': '# matplotlib may put files here...\n',
               'dlls':       '# put dlls here \n',
               'modules':    '# put custom larch or python modules here \n'}

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

    if not make_dir(larchdir):
        return
    for fname, text in files.items():
        fname = join(larchdir, fname)
        write_file(fname, text)

    for sdir, text in subdirs.items():
        sdir = join(larchdir, sdir)
        if not make_dir(sdir):
            break
        fname = join(sdir, 'README')
        write_file(fname, text)

modules_path = []
plugins_path = []
_path = [larchdir]

if 'LARCHPATH' in os.environ:
    _path.extend([nativedir(s) for s in os.environ['LARCHPATH'].split(':')])

for pth in _path:
    mdir = join(pth, 'modules')
    if exists(mdir) and mdir not in modules_path:
        modules_path.append(mdir)

    pdir = join(pth, 'plugins')
    if exists(pdir) and pdir not in plugins_path:
        plugins_path.append(pdir)

# initialization larch files to be run on startup
init_files = [join(larchdir, 'init.lar')]

if 'LARCHSTARTUP' in os.environ:
    startup = os.environ['LARCHSTARTUP']
    if exists(startup):
        init_files = [nativedir(startup)]

# history file:
history_file = join(larchdir, 'history.lar')

def show_site_config():
    is_frozen = repr(getattr(sys, 'frozen', None))
    print( """===  Larch Configuration
  sys executable:       %s
  sys frozen:           %s
  users home directory: %s
  users larch dir:      %s
  users history_file:   %s
  users startup files:  %s
  modules search path:  %s
  plugins search path:  %s
========================
""" % (sys.executable, is_frozen, home_dir, larchdir,
       history_file, init_files,
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
