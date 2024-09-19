import sys
import os
import platform
from pathlib import Path
from charset_normalizer import from_bytes

HAS_PWD = True
try:
    import pwd
except ImportError:
    HAS_PWD = False

def unixpath(d):
    if isinstance(d, bytes):
        d = str(from_bytes(d).best())
    if isinstance(d, str):
        d = Path(d).absolute()
    if isinstance(d, Path):
        return d.as_posix()
    raise ValueError(f"cannot get Path name from {d}")

# uname = 'win', 'linux', or 'darwin'
uname = sys.platform.lower()

if os.name == 'nt':
    uname = 'win'
if uname.startswith('linux'):
    uname = 'linux'

def path_split(path):
    "emulate os.path.split, returning posix path and filename"
    p = Path(path).absolute()
    return p.parent.as_posix(), p.name

# bindir = location of local binaries
nbits = platform.architecture()[0].replace('bit', '')

_here = Path(__file__).absolute()
topdir = _here.parents[1].as_posix()
bindir = Path(topdir, 'bin', f"{uname}{nbits}").as_posix()


def get_homedir():
    "determine home directory"
    homedir = None
    def check(method, s):
        "check that os.path.expanduser / expandvars gives a useful result"
        try:
            if method(s) not in (None, s):
                return method(s)
        except:
            pass
        return None

    # for Unixes, allow for sudo case
    susername = os.environ.get("SUDO_USER", None)
    if HAS_PWD and susername is not None and homedir is None:
        homedir = pwd.getpwnam(susername).pw_dir

    # try expanding '~' -- should work on most Unixes
    if homedir is None:
        homedir = check(os.path.expanduser, '~')

    # try the common environmental variables
    if homedir is  None:
        for var in ('$HOME', '$HOMEPATH', '$USERPROFILE', '$ALLUSERSPROFILE'):
            homedir = check(os.path.expandvars, var)
            if homedir is not None:
                break

    # For Windows, ask for parent of Roaming 'Application Data' directory
    if homedir is None and os.name == 'nt':
        try:
            from win32com.shell import shellcon, shell
            homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        except ImportError:
            pass

    # finally, use current folder
    if homedir is None:
        homedir = os.path.abspath('.')
    return unixpath(homedir)

def get_cwd():
    """get current working directory
    Note: os.getcwd() can fail with permission error.

    when that happens, this changes to the users `HOME` directory
    and returns that directory so that it always returns an existing
    and readable directory.
    """
    try:
        return Path('.').absolute().as_posix()
    except:
        home = get_homedir()
        os.chdir(home)
        return home
