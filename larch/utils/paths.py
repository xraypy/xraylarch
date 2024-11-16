import sys
import os
import platform
from pathlib import Path
from charset_normalizer import from_bytes

from pyshortcuts import uname, get_homedir, get_cwd

def unixpath(d):
    if isinstance(d, bytes):
        d = str(from_bytes(d).best())
    if isinstance(d, str):
        d = Path(d).absolute()
    if isinstance(d, Path):
        return d.as_posix()
    raise ValueError(f"cannot get Path name from {d}")

def path_split(path):
    "emulate os.path.split, returning posix path and filename"
    p = Path(path).absolute()
    return p.parent.as_posix(), p.name

# bindir = location of local binaries
nbits = platform.architecture()[0].replace('bit', '')

_here = Path(__file__).absolute()
topdir = _here.parents[1].as_posix()
bindir = Path(topdir, 'bin', f"{uname}{nbits}").as_posix()
