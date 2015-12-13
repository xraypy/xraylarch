
import os
from   os.path   import realpath, isdir, isfile, join, basename, dirname
from   distutils.spawn import find_executable
from shutil import copy, move
import subprocess
import re

from larch import (Group, Parameter, isParameter, param_value,
                   isNamedClass, Interpreter)

class FeffRunner(Group):
    """
    A Larch plugin for managing calls to the feff85exafs stand-alone executables.
    This plugin does not manage the output of Feff.  See feffpath() and other tools.

    Methods:
        run -- run one or more parts of feff

            feff = feffrunner(feffinp='path/to/feff.inp')
            feff.run() to run feff monolithically
            feff.run('rdinp')
            feff.run('xsph')
               and so on to run individual parts of feff
               ('rdinp', 'pot', 'opconsat', 'xsph', 'pathfinder', 'genfmt', 'ff2x')

          By default, installed versions of the feff executables are
          run.  To run newly compiled versions from the feff85exafs
          git repository, set the repo attribute to the top of the
          respository:

            feff = feffrunner(feffinp='path/to/feff.inp')
            feff.repo = '/home/bruce/git/feff85exafs'
            feff.run()

          If the symbol _xafs._feff_executable is set to a Feff executable,
          it can be run by doing

            feff = feffrunner(feffinp='path/to/feff6.inp')
            feff.run(None)

          run returns None if feff ran successfully, otherwise it
          returns an Exception with a useful message

          Other versions of feff in the execution path can also be
          handled, with the caveat that the executable begins with
          'feff', i.e. 'feff6', 'feff7', etc.

            feff = feffrunner(feffinp='path/to/feff6.inp')
            feff.run('feff6')

          If the value of the feffinp attribute is a file with a
          basename other than 'feff.inp', that file will be renamed to
          'feff.inp' and care will be taken to preserve an existing
          file by that name.

    Attributes:
        feffinp  -- the feff.inp file, absolute or relative to CWD
        repo     -- when set to the top of the feff85exfas repository, the newly compiled executables will be used
        resolved -- the fully resolved path to the most recently run executable
        verbose  -- write screen messages if True
        mpse     -- run opconsat after pot if True

    """

    def __init__(self, feffinp=None, verbose=True, repo=None, _larch=None, **kws):
        kwargs = dict(name='Feff runner')
        kwargs.update(kws)
        Group.__init__(self,  **kwargs)
        if _larch == None:
            self._larch   = Interpreter()
        else:
            self._larch = _larch
        self.feffinp  = feffinp
        self.verbose  = verbose
        self.mpse     = False
        self.repo     = repo
        self.resolved = None
        self.threshold = []
        self.chargetransfer = []


    def __repr__(self):
        if self.feffinp is not None:
            if not isfile(self.feffinp):
                return '<External Feff Group (empty)>'
            return '<External Feff Group: %s>' % self.feffinp
        return '<External Feff Group (empty)>'


    def run(self, exe='monolithic'):
        """
        Make system call to run one or more of the stand-alone executables,
        writing a log file to the folder containing the input file.

        """

        if self.feffinp == None:
            raise Exception("no feff.inp file was specified")
        if not isfile(self.feffinp):
            raise Exception("feff.inp file '%s' could not be found" % self.feffinp)

        savefile = '.save_save_save.inp'
        here=os.getcwd()
        os.chdir(dirname(self.feffinp))
        log = 'f85e.log'

        if exe == None:
            exe = ''
        else:
            if not ((exe in ('monolithic', 'rdinp', 'pot', 'opconsat', 'xsph', 'pathfinder', 'genfmt', 'ff2x')) or exe.startswith('feff')):
                os.chdir(here)
                raise Exception("'%s' is not a valid executable name" % exe)

        ## default behavior is to step through the feff85exafs modules (but not opconsat, monolithic presumes that opconsat will not be used)
        if exe.startswith('mono'): # run modules recursively
            if isfile(log): os.unlink(log)
            for m in ('rdinp', 'pot', 'xsph', 'pathfinder', 'genfmt', 'ff2x'):
                os.chdir(here)
                self.run(m)
                if m == 'pot' and self.mpse:
                    self.run('opconsat')
            return
        elif exe.startswith('feff'):
            if isfile(log): os.unlink(log)

        ## if exe is unset or not set to something already recognized,
        ## try to figure out what executable to run
        ##
        ## the logic is:
        ##  1. if exe seems to be a feff version, try to find that Feff executable
        ##  2. if repo is None, try to find the installed feff85exafs executable
        ##  3. if repo is set, try to find the newly compiled feff85exafs executable
        ##  4. if nothing has yet been found, try to use _xafs._feff_executable
        ##  5. if nothing is found, raise an Exception
        program=None
        if exe.startswith('feff'): # step 1, exe seems to be numbered feff (e.g. feff6, feff7, ...)
            self.resolved = find_executable(exe)
            if self.resolved:
                program=self.resolved

        if exe in ('rdinp', 'pot', 'opconsat', 'xsph', 'pathfinder', 'genfmt', 'ff2x'):
            if self.repo == None: # step 2, try to find the installed feff85exafs module
                self.resolved = find_executable(exe)
                if not os.access(self.resolved, os.X_OK):
                    os.chdir(here)
                    raise Exception("'%s' is not an executable" % self.resolved)
                if self.resolved:
                    program=self.resolved
            else:                   # step 3, try to find the newly compiled feff85exafs module
                folder=exe.upper()
                if exe=='pathfinder':
                    folder='PATH'
                program=join(self.repo, 'src', folder, exe)
                self.resolved=program
                if not isfile(program):
                    os.chdir(here)
                    raise Exception("'%s' cannot be found (has it been compiled?)" % program)
                if not os.access(program, os.X_OK):
                    os.chdir(here)
                    raise Exception("'%s' is not an executable" % program)

        if program == None:  # step 4, try _xafs.feff_executable
            program = self._larch.symtable.get_symbol('_xafs._feff_executable')
            try:
                program = self._larch.symtable.get_symbol('_xafs._feff_executable')
            except NameError:
                os.chdir(here)
                raise Exception("_xafs._feff_executable is not set (1)")
            except AttributeError:
                os.chdir(here)
                raise Exception("_xafs._feff_executable is not set (2)")

        if program != None:
            if not os.access(program, os.X_OK):
                program = None

        if program == None:  # step 5, give up
            os.chdir(here)
            raise Exception("'%s' executable cannot be found" % exe)

        ## preserve an existing feff.inp file if this is not called feff.inp
        if basename(self.feffinp) != 'feff.inp':
            if isfile('feff.inp'):
                copy('feff.inp', savefile)
                copy(basename(self.feffinp), 'feff.inp')

        f = open(log, 'a')
        header = "\n======= running module %s ====================================================\n" % exe
        if self.verbose: print(header)
        f.write(header)
        process=subprocess.Popen(program, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        flag = False
        thislist = []
        while True:
            line = process.stdout.readline()
            if not line:
                break
            if self.verbose: print( ':'+line.rstrip())
            ## snarf threshold energy
            pattern = re.compile('mu_(new|old)=\s+(-?\d\.\d+)')
            match = pattern.search(line)
            if match != None:
                self.threshold.append(match.group(2))
            ## snarf charge transfer
            if line.strip().startswith('Charge transfer'):
                thislist = []
                flag = True
            elif line.strip().startswith('SCF ITERATION'):
                self.chargetransfer.append(list(thislist))
                flag = False
            elif line.strip().startswith('Done with module 1'):
                self.chargetransfer.append(list(thislist))
                flag = False
            elif flag:
                this = line.split()
                thislist.append(this[1])
            f.write(line)
        f.close

        if isfile(savefile):
            move(savefile, 'feff.inp')
        os.chdir(here)
        return None

######################################################################

def initializeLarchPlugin(_larch=None):
    """initialize _xafs._feff_executable"""
    _larch.symtable.set_symbol('_xafs._feff_executable', find_executable('feff6'))


def feffrunner(feffinp=None, verbose=True, repo=None, _larch=None, **kws):
    """
    Make a FeffRunner group given a folder containing a baseline calculation
    """
    return FeffRunner(feffinp=feffinp, verbose=verbose, repo=repo, _larch=_larch)


def registerLarchPlugin(): # must have a function with this name!
    return ('_xafs', { 'feffrunner': feffrunner })
