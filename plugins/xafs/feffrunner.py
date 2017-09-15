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

    Feff8l_modules = ('rdinp', 'pot', 'xsph', 'pathfinder', 'genfmt', 'ff2x')

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

    def run(self, feffinp=None, folder=None, exe='feff8l'):
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

        savefile = '.save_.inp'
        here = os.path.abspath(os.getcwd())
        os.chdir(os.path.abspath(self.folder))

        feffinp_dir, feffinp_file = os.path.split(self.feffinp)
        feffinp_dir = dirname(self.feffinp)
        if len(feffinp_dir) > 0:
            os.chdir(feffinp_dir)

        if not isfile(feffinp_file):
            raise Exception("feff.inp file '%s' could not be found" % feffinp_file)

        if exe is None:
            for module in self.Feff8l_modules:
                os.chdir(here)
                self.run(exe=module)
            return

        #
        # exe is set, find the corresponding executable file

        ## find program to run:
        program = None
        if exe in self.Feff8l_modules:
            exe = "feff8l_%s" % exe

        resolved_exe = find_exe(exe)
        if resolved_exe is not None:
            program = resolved_exe

        else:
            try:
                program = self._larch.symtable.get_symbol('_xafs._feff_executable')
            except (NameError, AttributeError) as exc:
                program = None

        if program is not None:
            if not os.access(program, os.X_OK):
                program = None

        if program is None:  # Give up!
            os.chdir(here)
            raise Exception("'%s' executable cannot be found" % exe)

        ## preserve an existing feff.inp file if this is not called feff.inp
        if feffinp_file != 'feff.inp':
            if isfile('feff.inp'):
                copy('feff.inp', savefile)
            copy(feffinp_file, 'feff.inp')

        log = 'feffrun_%s.log' % exe
        if isfile(log):
            os.unlink(log)

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

def _feff6l(feffinp='feff.inp', folder='.', verbose=True, _larch=None, **kws):
    """
    run a Feff6l calculation for a feff.inp file in a folder

    Arguments:
    ----------
      feffinp (str): name of feff.inp file to use ['feff.inp']
      folder (str): folder for calculation, containing 'feff.inp' file ['.']
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

def _feff8l(feffinp='feff.inp', folder='.', module=None, verbose=True, _larch=None, **kws):
    """
    run a Feff8l calculation for a feff.inp file in a folder

    Arguments:
    ----------
      feffinp (str): name of feff.inp file to use ['feff.inp']
      folder (str): folder for calculation, containing 'feff.inp' file ['.']
      module (None or str): module of Feff8l to run [None -- run all]
      verbose (bool): whether to print out extra messages [False]

    Returns:
    --------
      instance of FeffRunner

    Notes:
    ------
      many results data files are generated in the Feff working folder
    """
    feffrunner = FeffRunner(folder=folder, feffinp=feffinp, verbose=verbose, _larch=_larch)
    feffrunner.run(exe=None)
    return feffrunner

def registerLarchGroups():
    return (FeffRunner,)

def registerLarchPlugin(): # must have a function with this name!
    return ('_xafs', { 'feffrunner': feffrunner,
                       'feff6l': _feff6l,
                       'feff8l': _feff8l})
