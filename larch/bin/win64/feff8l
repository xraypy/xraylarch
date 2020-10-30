#!/usr/bin/env python
"""
Feff85L monolithic main program.

This runs all (or selected) modules of Feff85L in order:
     feff8l_rdinp
     feff8l_pot
     feff8l_xsph
     feff8l_pathfinder
     feff8l_genfmt
     feff8l_ff2x
"""

from __future__ import print_function
import os
import sys
import glob
import tempfile
from datetime import datetime
from subprocess import Popen, PIPE
from optparse import OptionParser
import pkg_resources

def bytes2str(s):
    if isinstance(s, str):
        return s
    elif isinstance(s, bytes):
        return s.decode(sys.stdout.encoding)
    return str(s, sys.stdout.encoding)

usage = """usage: %prog [options] folder(s)

run feff8l (or selected modules) on one
or more folders containing feff.inp files.

Example:
   feff8l --no-ff2chi Structure1 Structure2
"""

parser = OptionParser(usage=usage, prog="feff8l",
                      version="Feff85L for EXAFS version 8.5L, build 001")
parser.add_option("-q", "--quiet", dest="quiet", action="store_true",
                  default=False, help="set quiet mode, default=False")
parser.add_option("--no-pot", dest="no_pot", action="store_true",
                  default=False, help="do not run POT module")
parser.add_option("--no-phases", dest="no_phases", action="store_true",
                  default=False, help="do not run XSPH module")
parser.add_option("--no-paths", dest="no_paths", action="store_true",
                  default=False, help="do not run PATHFINDER module")
parser.add_option("--no-genfmt", dest="no_genfmt", action="store_true",
                  default=False, help="do not run GENFMT module")
parser.add_option("--no-ff2chi", dest="no_ff2chi", action="store_true",
                  default=False, help="do not run FF2CHI module")

ERR_FEFFDIR = "Could not find folder '{:s}'"
ERR_FEFFINP = "Could not find feff.inp file in folder '{:s}'"
TOP_DIR, _ = os.path.split(os.path.abspath(__file__))
FEFFINP = 'feff.inp'

def isotime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class Feff8LRunner(object):
    modules = ('rdinp', 'pot', 'xsph', 'pathfinder', 'genfmt', 'ff2x')
    def __init__(self, run=True):
        try:
            self.logfile = open('feff8l.log', 'w+')
        except:
            self.logfile = tempfile.NamedTemporaryFile(prefix='feff8l')
        self.verbose = True
        if run:
            self.run()

    def write(self, msg, verbose=True):
        msg = bytes2str(msg)
        if verbose:
            sys.stdout.write(msg)
        self.logfile.write(msg)

    def run(self, rdinp=True, pot=True, xsph=True, pathfinder=True,
            genfmt=True, ff2x=True, verbose=True):
        """
        run all or selected modules of Feff85L

        Arguments
        ---------
        rdinp      (bool) : run read-input module  [True]
        pot        (bool) : run potentials module[True]
        xsph       (bool) : run xsph / phases module [True]
        pathfinder (bool) : run path finder module [True]
        genfmt     (bool) : run genfmt / feff module [True]
        ff2x       (bool) : run ff2chi module [True]
        verbose    (bool) : write normal output to screen as well as log file [True]
        """
        dorun =  dict(rdinp=rdinp, pot=pot, xsph=xsph, pathfinder=pathfinder,
                      genfmt=genfmt, ff2x=ff2x)

        self.write("#= Feff85l {:s}\n".format(isotime()), verbose=True)

        for module in self.modules:
            if not dorun[module]:
                continue
            self.write(("#= Feff85l {:s} module\n".format(module)), verbose=True)
            cmd = [os.path.join(TOP_DIR, "feff8l_{:s}".format(module))]
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
            while True:
                msg = bytes2str(proc.stdout.read())
                if msg == '':
                    break
                self.write(msg, verbose=verbose)
            while True:
                msg = bytes2str(proc.stdout.read())
                if msg == '':
                    break
                self.write("#ERROR %s" % msg, verbose=True)
            self.logfile.flush()
        for fname in glob.glob('log*.dat'):
            try:
                os.unlink(fname)
            except IOError:
                pass
        self.write("#= Feff85l done {:s}\n".format(isotime()), verbose=True)

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    runopts = dict(rdinp=True,
                   pot=not options.no_pot,
                   xsph=not options.no_phases,
                   pathfinder=not options.no_paths,
                   genfmt=not options.no_genfmt,
                   ff2x=not options.no_ff2chi,
                   verbose=not options.quiet)

    if len(args) == 0:
        args = ['.']

    for dirname in args:
        if os.path.exists(dirname) and os.path.isdir(dirname):
            thisdir = os.path.abspath(os.curdir)
            os.chdir(dirname)
            if os.path.exists(FEFFINP) and os.path.isfile(FEFFINP):
                f8 = Feff8LRunner(run=False)
                f8.run(**runopts)
            else:
                print(ERR_FEFFINP.format(os.path.abspath(os.curdir)))
            os.chdir(thisdir)
        else:
            print(ERR_FEFFDIR.format(dirname))
