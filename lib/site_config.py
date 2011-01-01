##
## site configuration for larch:
##  
##   init_files:  list of larch files run (in order) on startup
##   module_path: list of directories to search for larch code

import os
import sys

join = os.path.join
exists = os.path.exists


# general-use system path
base_path = ['/usr/local/share/']
user_homedirs = [os.environ.get('HOME', '.')]

if os.name == 'nt':
    base_path = ['C:\\Program Files']
    for profile in ('USERPROFILE', 'ALLUSERSPROFILE'):
        hdir = os.environ.get(profile, '.')
        if hdir not in user_homedirs:
            user_homedirs.append(hdir)

base_path.insert(0, join(sys.prefix, 'share'))

module_path = ['.']
for lardir in  base_path:
    sdir = join(lardir, 'larch', 'modules')
    if exists(sdir) and sdir not in module_path:
        module_path.append(sdir)

for lardir  in ('larch', '.larch'):
    for uhome in user_homedirs:
        sdir = join(uhome, lardir)
    if exists(sdir) and sdir not in module_path:
        module_path.append(sdir)

if 'LARCHPATH' in os.environ:
    module_path.extend(os.environ['LARCHPATH'].split(':'))

# initial larch files run at startup
init_files = []

for lardir in module_path:
    ifile = join(lardir, 'init.lar')
    if exists(ifile):
        init_files.append(ifile)

if 'LARCHSTARTUP' in os.environ:
    if exists(os.environ['LARCHSTARTUP']):
        init_files.insert(0, os.environ['LARCHSTARTUP'])

