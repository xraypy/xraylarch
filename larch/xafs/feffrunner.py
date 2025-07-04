import sys
import os

import glob
from shutil import copy, move
import subprocess
import time
import re
from pathlib import Path
from optparse import OptionParser
from subprocess import Popen, PIPE

from pyshortcuts import bytes2str, uname, get_cwd

from larch import Group
from larch.larchlib import isNamedClass
from larch.utils import isotime, bindir

def find_exe(exename):
    if isinstance(exename, Path):
        exename = str(exename)
    if uname == 'win' and not exename.endswith('.exe'):
        exename = f"{exename}.exe"
    exefile = Path(bindir, exename)
    if exefile.exists() and os.access(exefile, os.X_OK):
        return exefile

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
        folder   -- the folder to run in, containing feff.inp file
        feffinp  -- the feff.inp file, absolute or relative to `folder`
        resolved -- the fully resolved path to the most recently run executable
        verbose  -- write screen messages if True
        mpse     -- run opconsat after pot if True

    """

    Feff8l_modules = ('rdinp', 'pot', 'xsph', 'pathfinder', 'genfmt', 'ff2x')

    def __init__(self, feffinp='feff.inp', folder='.', verbose=True, _larch=None,
                 message_writer=None, **kws):
        kwargs = dict(name='Feff runner')
        kwargs.update(kws)
        Group.__init__(self,  **kwargs)
        self._larch = _larch

        if folder is None:
            folder = '.'
        self.folder   = folder
        self.feffinp  = feffinp
        self.verbose  = verbose
        self.message_writer   = message_writer
        self.mpse     = False
        self.resolved = None
        self.threshold = []
        self.chargetransfer = []

    def __repr__(self):
        ffile = Path(self.folder, self.feffinp)
        return f'<External Feff Group: {ffile}>'

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
        here = Path.cwd().absolute()
        os.chdir(Path(self.folder).absolute())

        pfeff = Path(self.feffinp)
        feffinp_dir, feffinp_file = pfeff.parent, pfeff.name
        if feffinp_dir.exists():
            os.chdir(feffinp_dir)

        if not Path(feffinp_file).is_file():
            raise Exception(f"feff.inp file '{feffinp_file}' could not be found")

        if exe in (None, 'feff8l'):
            for module in self.Feff8l_modules:
                os.chdir(here)
                self.run(exe=module)
            return

        #
        # exe is set, find the corresponding executable file
        ## find program to run:
        program = None
        if exe in self.Feff8l_modules:
            exe = f"feff8l_{exe}"

        resolved_exe = find_exe(exe)
        if resolved_exe is not None:
            program = resolved_exe

        else:
            getsym = self._larch.symtable.get_symbol
            try:
                program = getsym('_xafs._feff8_executable')
            except (NameError, AttributeError) as exc:
                try:
                    program = getsym('_xafs._feff_executable')
                except (NameError, AttributeError) as exc:
                    program = None

        if program is not None:
            if not os.access(program, os.X_OK):
                program = None

        if program is None:  # Give up!
            os.chdir(here)
            raise Exception(f"'{exe}' executable cannot be found")

        ## preserve an existing feff.inp file if this is not called feff.inp
        if feffinp_file != 'feff.inp':
            if Path('feff.inp').is_file():
                copy('feff.inp', savefile)
            copy(feffinp_file, 'feff.inp')

        logname = Path(program).name
        if logname.endswith('.exe'):
            logname = logname[:4]

        log = f'feffrun_{logname}.log'

        if Path(log).is_file():
            os.unlink(log)

        f = open(log, 'a')
        header = f"\n======== running Feff module {exe} ========\n"

        def write(msg):
            msg = bytes2str(msg)
            msg = " : {:s}\n".format(msg.strip().rstrip())
            if self._larch is not None:
                self._larch.writer.write(msg)
            else:
                sys.stdout.write(msg)

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
            line = bytes2str(process.stdout.readline())
            if not line:
                break
            if self.verbose:
                write(line)
            if callable(self.message_writer):
                self.message_writer(line)

            ## snarf threshold energy
            pattern = re.compile(r'mu_(new|old)=\s+(-?\d\.\d+)')
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

        if Path(savefile).is_file():
            move(savefile, 'feff.inp')
        os.chdir(here)
        return None

######################################################################
def feffrunner(folder=None, feffinp=None, verbose=True, _larch=None, **kws):
    """
    Make a FeffRunner group given a folder containing a baseline calculation
    """
    return FeffRunner(folder=folder, feffinp=feffinp, verbose=verbose,
                      _larch=_larch, **kws)

def feff6l(feffinp='feff.inp', folder='.', verbose=True, _larch=None, **kws):
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
    feffrunner = FeffRunner(folder=folder, feffinp=feffinp, verbose=verbose,
                            _larch=_larch, **kws)
    exe = find_exe('feff6l')
    feffrunner.run(exe=exe)
    return feffrunner

def feff6l_cli():
    """run feff6l as command line program
    """

    usage = """usage: %prog [options] folder(s)

run feff6l on one or more folders containing feff.inp files
or on an input file in the current folder

Examples:
   feff6l Structure1 Structure2

   feff6l feff_Cu2O.inp

"""

    parser = OptionParser(usage=usage, prog="feff6l",
                          version="Feff6L version 6L.02")

    FEFFINP = 'feff.inp'
    (options, args) = parser.parse_args()
    if len(args) == 0:
        args = ['.']

    curdir = Path(get_cwd()).absolute()
    for arg in args:
        parg = Path(arg).absolute()
        if parg.is_file():
            feff6l(feffinp=parg.as_posix())
        elif parg.is_dir():
            feffinp = Path(parg, 'feff.inp').absolute()
            if feffinp.exists():
                os.chdir(parg)
                feff6l(folder=parg.as_posix())
            else:
                cdir = Path.cwd().absolute()
                msg = "Could not find feff.inp file in folder '{cdir}'"
                sys.stdout.write(msg)
            os.chdir(curdir)


def feff8l(feffinp='feff.inp', folder='.', module=None, verbose=True, _larch=None, **kws):
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
    feffrunner = FeffRunner(folder=folder, feffinp=feffinp, verbose=verbose,
                            _larch=_larch, **kws)
    feffrunner.run(exe='feff8l')
    return feffrunner


def feff8l_cli():
    """run feff8l as  a command line program to run all or some of
     feff8l_rdinp
     feff8l_pot
     feff8l_xsph
     feff8l_pathfinder
     feff8l_genfmt
     feff8l_ff2x
    """

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


    FEFFINP = 'feff.inp'
    (options, args) = parser.parse_args()

    verbose = not options.quiet
    modules = ['rdinp', 'pot', 'xsph', 'pathfinder', 'genfmt', 'ff2x']
    if options.no_pot:
        modules.remove('pot')
    if options.no_phases:
        modules.remove('xsph')
    if options.no_paths:
        modules.remove('pathfinder')
    if options.no_genfmt:
        modules.remove('genfmt')
    if options.no_ff2chi:
        modules.remove('ff2x')

    if len(args) == 0:
        args = ['.']


    def run_feff8l(modules):
        """ run selected modules of Feff85L   """
        try:
            logfile = open('feff8l.log', 'w+')
        except:
            logfile = tempfile.NamedTemporaryFile(prefix='feff8l')

        def write(msg):
            msg = bytes2str(msg)
            sys.stdout.write(msg)
            logfile.write(msg)

        write(f"#= Feff85l {isotime()}\n")
        for mod in modules:
            write(f"#= Feff85l {mod} module\n")
            exe = find_exe(f'feff8l_{mod}')
            proc = Popen(exe, stdout=PIPE, stderr=PIPE)
            while True:
                msg = bytes2str(proc.stdout.read())
                if msg == '':
                    break
                write(msg)
            while True:
                msg = bytes2str(proc.stderr.read())
                if msg == '':
                    break
                write(f"#ERROR {msg}")
            logfile.flush()
        for fname in glob.glob('log*.dat'):
            try:
                os.unlink(fname)
            except IOError:
                pass
        write(f"#= Feff85l done {isotime()}\n")

    for dname in args:
        pdir = Path(dname).absolute()
        if pdir.exists() and pdir.is_dir():
            thisdir = Path.cwd().absolute()
            os.chdir(pdir)
            pfeff = Path(FEFFINP)
            if pfeff.exists() and pfeff.is_file():
                run_feff8l(modules)
            else:
                msg = f"Could not find feff.inp file in folder '{pdir}'"
                sys.stdout.write(msg)
            os.chdir(thisdir)
        else:
            print(f"Could not find folder '{pdir}'")
