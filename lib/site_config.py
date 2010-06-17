##
## site configuration for larch:
##  
##   init_files:  list of larch files run (in order) on startup
##   module_path: list of directories to search for larch code

import os
import sys
_base_unix = os.path.join(sys.prefix,'share','larch')

_base_win  = 'C:\\Program Files\\larch'

# yes, user home *should* be overwritten   
base_path = _base_unix
user_home = _base_unix

if os.name == 'nt':
    base_path = _base_win
    user_home = _base_win

try:
    user_home = os.environ.get('HOME',user_home)
except:
    pass

module_path = ['.']
if 'LARCHPATH' in os.environ:
    module_path.extend(os.environ['LARCHPATH'].split(':'))

module_path.append(os.path.join(base_path,'modules'))

# initial larch files run at startup
init_files = []

sys_init = os.path.join(base_path,'init.lar')
if os.path.exists(sys_init):
    init_files.append(sys_init)

if 'LARCHSTARTUP' in os.environ:
    user_init = os.environ['LARCHSTARTUP']
else:
    user_init = os.path.join(user_home,'.larch_init')
if os.path.exists(user_init):
    init_files.append(user_init)    


