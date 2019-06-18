#!/usr/bin/python
#  this script returns the directory into which dlls
#  should be placed for the present architecture.
#  current options are:
#     win32/     Windows, 32-bit
#     win64/     Windows, 64-bit
#     linux32/   Linux, 32-bit
#     linux64/   Linux, 64-bit
#     darwin64/  Mac OS X, 64-bit

from __future__ import print_function
import  os, sys
from platform import uname, architecture

system, node, release, version, mach, processor = uname()
arch = architecture()[0]

dlldir = None
makefile = None
if os.name == 'nt':
    dlldir = 'win32'
    makefile = 'Mk.win32'
    if arch.startswith('64'):
        dlldir = 'win64'
else:
    if system.lower().startswith('linu'):
        dlldir = 'linux32'
        makefile = 'Mk.linux'
        if arch.startswith('64'):
            dlldir = 'linux64'
    elif system.lower().startswith('darw'):
        dlldir = 'darwin64'
        makefile = 'Mk.darwin64'

print('Writing Makefiles for %s' % (system))

if dlldir is not None:
    os.system('cp ../conf/%s Mk.config' % (makefile))
    fout = open('Mk.install', 'w')
    fout.write("INSTALLDIR=../../larch/bin/%s/" % dlldir)
    fout.write("")
    fout.close()
