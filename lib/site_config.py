##
## site configuration for larch:
##
##   init_files:  list of larch files run (in order) on startup
##   module_path: list of directories to search for larch code
##   history_file:
import os
import sys
import site_configdata

join = os.path.join
exists = os.path.exists
abspath = os.path.abspath
curdir = abspath('.')

# general-use system path
home_dir = os.environ.get('HOME', None)
sys_larchdir = site_configdata.unix_installdir
usr_larchdir = site_configdata.unix_userdir

# windows
if os.name == 'nt':
    sys_larchdir = site_configdata.win_installdir
    usr_larchdir = site_configdata.win_userdir

    if home_dir is None:
        for profile in ('ALLUSERSPROFILE', 'USERPROFILE'):
            home_dir = os.environ.get(profile, None)

if home_dir is None:
    home_dir = curdir

if 'LARCHDIR' in os.environ:
    usr_larchdir = os.environ['LARCHDIR']
else:
    usr_larchdir = abspath(join(home_dir, usr_larchdir))

# modules_path, plugins_path
#  determine the search path for modules

modules_path, plugins_path = [], []
modpath = []

if 'LARCHPATH' in os.environ:
    modpath.append(os.environ['LARCHPATH'].split(':'))
else:
    modpath.append(usr_larchdir)

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
    if exists(os.environ['LARCHSTARTUP']):
        init_files.append(os.environ['LARCHSTARTUP'])

# history file:
history_file = join(home_dir, '.larch_history')
if exists(usr_larchdir) and os.path.isdir(usr_larchdir):
    history_file = join(usr_larchdir, 'history.lar')

def show_site_config():
    print """===  Larch Configuration 
  users home directory: %s
  users larch dir:      %s
  users history_file:   %s
  users startup files:  %s
  modules search path:  %s
  plugins search path:  %s
========================
""" % (home_dir, usr_larchdir, history_file, init_files,
       modules_path, plugins_path)

if __name__ == '__main__':
    show_site_config()
