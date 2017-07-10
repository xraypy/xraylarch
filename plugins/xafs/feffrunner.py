import os
from   os.path   import realpath, isdir, isfile, join, basename, dirname
import sys
from   distutils.spawn import find_executable

from shutil import copy, move
import subprocess
import time
import re

from larch import (Group, Parameter, isParameter, param_value,
                   isNamedClass, Interpreter)

def find_exe(exename):
    bindir = 'bin'
    if os.name == 'nt':
        bindir = 'Scripts'
        if not exename.endswith('.exe'):
            exename = "%s.exe" % exename

    exefile = os.path.join(sys.exec_prefix, bindir, exename)

    if os.path.exists(exefile) and os.access(exefile, os.X_OK):
        return exefile
    return find_executable(exename)


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

    def __init__(self, feffinp='feff.inp', folder=None, verbose=True, repo=None, _larch=None, **kws):
        kwargs = dict(name='Feff runner')
        kwargs.update(kws)
        Group.__init__(self,  **kwargs)
        if _larch is None:
            self._larch   = Interpreter()
        else:
            self._larch = _larch

        self.folder   = folder or '.'
        self.feffinp  = feffinp
        self.verbose  = verbose
        self.mpse     = False
        self.repo     = repo
        self.resolved = None
        self.threshold = []
        self.chargetransfer = []


    def __repr__(self):
        fullfile = os.path.join(self.folder, self.feffinp)
        return '<External Feff Group: %s>' % fullfile

    def run(self, feffinp=None, folder=None, exe='monolithic'):
        """
        Make system call to run one or more of the stand-alone executables,
        writing a log file to the folder containing the input file.

        """
        if folder is not None:
            self.folder = folder

        if feffinp is not None:
            self.feffinp = feffinp

        if self.feffinp is None:
            raise Exception("no feff.inp file was specified")

        savefile = '.save_save_save.inp'
        here = os.path.abspath(os.getcwd())
        os.chdir(os.path.abspath(self.folder))


        feffinp_dir, feffinp_file = os.path.split(self.feffinp)
        feffinp_dir = dirname(self.feffinp)
        if len(feffinp_dir) > 0:
            os.chdir(feffinp_dir)

        if not isfile(feffinp_file):
            raise Exception("feff.inp file '%s' could not be found" % feffinp_file)

        log = 'f85e.log'

        if exe is None:
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
        program = None
        if exe.startswith('feff'): # step 1, exe seems to be numbered feff (e.g. feff6, feff7, ...)
            self.resolved = find_exe(exe)
            if self.resolved:
                program = self.resolved

        if exe in ('rdinp', 'pot', 'opconsat', 'xsph', 'pathfinder', 'genfmt', 'ff2x'):
            if self.repo == None: # step 2, try to find the installed feff85exafs module
                self.resolved = find_exe(exe)
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

        if program is None:  # step 4, try _xafs._feff_executable
            program = self._larch.symtable.get_symbol('_xafs._feff_executable')
            try:
                program = self._larch.symtable.get_symbol('_xafs._feff_executable')
            except NameError:
                os.chdir(here)
                raise Exception("_xafs._feff_executable is not set (1)")
            except AttributeError:
                os.chdir(here)
                raise Exception("_xafs._feff_executable is not set (2)")

        if program is not None:
            if not os.access(program, os.X_OK):
                program = None

        if program is None:  # step 5, give up
            os.chdir(here)
            raise Exception("'%s' executable cannot be found" % exe)

        ## preserve an existing feff.inp file if this is not called feff.inp
        if feffinp_file != 'feff.inp':
            if isfile('feff.inp'):
                copy('feff.inp', savefile)
            copy(feffinp_file, 'feff.inp')

        f = open(log, 'a')
        header = "\n======== running Feff module %s ========\n" % exe
        def write(msg):
            msg = " : {:s}\n".format(msg.strip().rstrip())
            self._larch.writer.write(msg)

        if self.verbose:
            write(header)
        f.write(header)
        process=subprocess.Popen(program, shell=False,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        flag = False
        thislist = []
        while True:
            if  process.returncode is None:
                process.poll()
            time.sleep(0.01)
            line = process.stdout.readline()
            if not line:
                break
            if self.verbose:
                write(line)
            ## snarf threshold energy
            pattern = re.compile('mu_(new|old)=\s+(-?\d\.\d+)')
            match = pattern.search(line)
            if match is not None:
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
    feff6_exe = find_exe('feff6l')
    if feff6_exe is None:
        feff6_exe = find_exe('feff6')
    _larch.symtable.set_symbol('_xafs._feff_executable', feff6_exe)


def feffrunner(feffinp=None, verbose=True, repo=None, _larch=None, **kws):
    """
    Make a FeffRunner group given a folder containing a baseline calculation
    """
    return FeffRunner(feffinp=feffinp, verbose=verbose, repo=repo, _larch=_larch)

def _feff6l(folder='.', feffinp='feff.inp', verbose=True, _larch=None, **kws):
    """
    run a feff6 calculation for a feff.inp file in a folder

    Arguments:
    ----------
      folder (str): folder for calculation, containing 'feff.inp' file ['.']
      feffinp (str): name of feff.inp file to use ['feff.inp']
      verbose (bool): whether to print out extra messages [False]

    Returns:
    --------
      instance of FeffRunner

    Notes:
    ------
      many results data files are generated in the Feff working folder
    """
    feffrunner = FeffRunner(folder=folder, feffinp=feffinp, verbose=verbose, _larch=_larch)
    feff_exe = _larch.symtable.get_symbol('_xafs._feff_executable')

    if 'feff6l' in feff_exe:
        exe = 'feff6l'
    else:
        exe = 'feff6'
    feffrunner.run(exe=exe)
    return feffrunner

def registerLarchGroups():
    return (FeffRunner,)

def registerLarchPlugin(): # must have a function with this name!
    return ('_xafs', { 'feffrunner': feffrunner,
                       'feff6l': _feff6l})
