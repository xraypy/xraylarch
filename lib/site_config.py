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

#
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
    home_dir = '.'

if 'LARCHDIR' in os.environ:
    usr_larchdir = os.environ['LARCHDIR']
else:
    usr_larchdir = abspath(join(home_dir, usr_larchdir))

# module_path / larch_dir
#  1. determine the search path for modules
#  2. determin the "larch directory"
module_path = ['.']

for folder in (sys_larchdir, usr_larchdir):
    mod_dir = join(folder, 'modules')
    if exists(mod_dir):
        module_path.append(mod_dir)

if 'LARCHPATH' in os.environ:
    for mod_dir in os.environ['LARCHPATH'].split(':'):
        if exists(mod_dir) and mod_dir not in module_path:
            module_path.append(mod_dir)

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

# print 'history_file: ', history_file
# print 'module_path: ', module_path
# print 'init_files: ', init_files

